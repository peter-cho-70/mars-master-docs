#!/usr/bin/env python3
"""
뉴스 큐시트 PDF 파서 — cuesheet_parser.py
==========================================
지원 형식: 뉴스투데이, 뉴스데스크, 뉴스25 등 MBC 계열 큐시트 PDF

사용법:
  python3 cuesheet_parser.py 큐시트.pdf
  python3 cuesheet_parser.py 큐시트.pdf --out result.json
  python3 cuesheet_parser.py 큐시트.pdf --debug
"""

import pdfplumber
import re
import json
import sys
import os
from datetime import datetime
from uuid import uuid4

# ──────────────────────────────────────────────
#  컬럼 X 좌표 기준 (픽셀, pdfplumber 좌표계)
#  실제 PDF에서 측정한 값 — 약간의 허용 범위 적용
# ──────────────────────────────────────────────
COL = {
    'no':       (40,  68),   # NO 번호
    'type':     (60,  90),   # 형식 (완/단/타/출/NT 아이콘 영역)
    'item':     (82, 248),   # 아이템명
    'a':        (210,260),   # A 컬럼 (앵커 아이콘)
    'c':        (244,270),   # C 컬럼 (큐번호)
    'reporter': (262,306),   # 담당 기자
    'dur':      (298,344),   # 시간 MM:SS
    'cum':      (338,390),   # 합계 (누적 시간)
    'title':    (375,483),   # 제목
    'subtitle': (478,600),   # 부가자막
}

# 형식 아이콘 유니코드 → 타입 코드 매핑
# pdfplumber가 추출한 유니코드 심볼 처리
ICON_TYPE_MAP = {
    '\ue98a': '완',  # 완성 리포트 아이콘
    '\ue90c': '타',  # 타이틀 아이콘
    '\ue961': '특',  # 특수 아이콘 (CM, 오프닝 등)
    '\ue9b2': '단',  # 단신 아이콘
    '\ue9e8': '출',  # 출연 아이콘
}

# 형식 텍스트 → 아이템 타입 매핑
TYPE_MAP = {
    '완': 'REPORT',
    '단': 'ANCHOR',
    '타': 'TITLE',
    '출': 'CORNER',
    'NT': 'NT',
    '특': 'SPECIAL',
    'CM': 'CM',
    '날씨': 'WEATHER',
    '클로징': 'CLOSING',
    '단/': 'ANCHOR',
}

# 아이템명 패턴
RE_ANC_DUR    = re.compile(r'^\[(\d+:\d+)\]')           # [1:47] 앵커멘트 길이
RE_HAS_ANC    = re.compile(r'^\[:\]')                    # [:] 앵커멘트 있음
RE_ANC_WARN   = re.compile(r'\*+앵멘')                  # ***앵멘 확인 필요
RE_GRAPHIC    = re.compile(r'##')                        # ## 그래픽
RE_VIDEO_DAN  = re.compile(r'^동영상D')                  # 동영상D 단신
RE_DDR        = re.compile(r'\[DDR타이틀\]')             # DDR 타이틀
RE_SVR        = re.compile(r'\[SVR타이틀\]')             # SVR 타이틀
RE_TOKTOK     = re.compile(r'\[타이틀없음\]')            # 타이틀없음 코너
RE_SB         = re.compile(r'^\(SB\)')                   # (SB) 스탠바이
RE_TIME       = re.compile(r'^\d{1,2}:\d{2}(:\d{2})?$') # MM:SS or HH:MM:SS

# 앵커 교대 패턴
ANCHOR_CHANGE_PATTERNS = [
    '남앵커', '여앵커', '남녀앵커', '남녀…', '남녀',
    '앵커', '조현용 앵커', '김수지 앵커', '손령', '정슬기',
]

# 특수 아이템 식별 (행에 NO 없이 나타나는 항목들)
SPECIAL_ITEMS = {
    'CM': 'CM',
    '전CM': 'CM',
    '후CM': 'CM',
    '중간광고': 'CM',
    '중CM': 'CM',
    '타이틀': 'TITLE',
    '메인타이틀': 'TITLE',
    '끝 타이틀': 'TITLE',
    '비상 타이틀': 'TITLE',
    '오프닝': 'OPEN',
    '클로징': 'CLOSING',
    '날씨': 'WEATHER',
    '스포츠 뉴스': 'SPORTS',
    '잠시후': 'BUMPER',
    '주요뉴스': 'HEADLINE',
    '미리보는 오늘': 'PREVIEW',
    '시보': 'TIMESIG',
}


# ══════════════════════════════════════════════
#  헬퍼 함수
# ══════════════════════════════════════════════

def words_in_col(words, col_key):
    """특정 컬럼 범위 내의 단어만 필터링"""
    x_min, x_max = COL[col_key]
    return [w for w in words if x_min <= w['x0'] < x_max]


def words_text(words):
    """단어 목록을 하나의 텍스트로 합침"""
    return ' '.join(w['text'] for w in words).strip()


def parse_duration(s):
    """'MM:SS' 또는 'HH:MM:SS' → 초 단위 정수"""
    if not s:
        return 0
    parts = s.replace(';', ':').split(':')
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass
    return 0


def fmt_duration(secs):
    """초 → 'HH:MM:SS' 문자열"""
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def guess_item_type(item_text, no_text, reporter, type_raw):
    """아이템명과 컨텍스트로 타입 추론"""
    if type_raw and type_raw in TYPE_MAP:
        return TYPE_MAP[type_raw]

    item_lower = item_text.lower()

    # 특수 아이템 식별
    for key, val in SPECIAL_ITEMS.items():
        if key in item_text:
            return val

    # 동영상D = 동영상 단신
    if RE_VIDEO_DAN.match(item_text):
        return 'ANCHOR'  # 동영상 단신은 단신으로 분류

    # 담당이 ANC이면 앵커 직접 낭독
    if reporter == 'ANC':
        return 'ANCHOR'

    # 담당이 exr이면 CM
    if reporter == 'exr':
        return 'CM'

    # NO가 있으면 리포트 (기본)
    if no_text and no_text.isdigit():
        return 'REPORT'

    return 'SPECIAL'


def extract_anc_metadata(item_text):
    """아이템명에서 앵커멘트 메타데이터 추출"""
    meta = {
        'ancDuration':     None,
        'hasAnc':          False,
        'ancWarnFlag':     False,
        'graphicNeeded':   False,
        'isVideoDan':      False,
        'isDDR':           False,
        'isSVR':           False,
        'isCorner':        False,
        'isSB':            False,
    }

    m = RE_ANC_DUR.match(item_text)
    if m:
        meta['ancDuration'] = m.group(1)
        meta['hasAnc'] = True

    if RE_HAS_ANC.match(item_text):
        meta['hasAnc'] = True

    if RE_ANC_WARN.search(item_text):
        meta['ancWarnFlag'] = True
        meta['hasAnc'] = True

    if RE_GRAPHIC.search(item_text):
        meta['graphicNeeded'] = True

    if RE_VIDEO_DAN.match(item_text):
        meta['isVideoDan'] = True

    if RE_DDR.search(item_text):
        meta['isDDR'] = True

    if RE_SVR.search(item_text):
        meta['isSVR'] = True

    if RE_TOKTOK.match(item_text):
        meta['isCorner'] = True

    if RE_SB.match(item_text):
        meta['isSB'] = True

    return meta


def suggest_obs_settings(item_type, has_anc, reporter, item_text):
    """아이템 타입에 따른 OBS 설정 자동 추천"""
    settings = {
        'obsScene':   '',
        'transIn':    'Cut',
        'transOut':   'Cut',
        'srvAuto':    False,
        'camPrimary': '',
        'micMode':    'auto',
        'cgAutoOn':   True,
        'cgDelayOn':  2,
        'cgDelayOff': 5,
        'camPreset':  1,
    }

    type_settings = {
        'TITLE':   {'obsScene': 'TITLE',       'transIn': 'Fade', 'camPrimary': ''},
        'CM':      {'obsScene': 'CM_PRE',       'transIn': 'Cut',  'camPrimary': ''},
        'OPEN':    {'obsScene': 'CAM1_ANCHOR',  'transIn': 'Cut',  'camPrimary': 'cam1'},
        'ANCHOR':  {'obsScene': 'CAM1_ANCHOR',  'transIn': 'Cut',  'camPrimary': 'cam1'},
        'REPORT':  {'obsScene': 'SRV{N}_VCR',  'transIn': 'Cut',  'srvAuto': True},
        'NT':      {'obsScene': 'CAM1_SRV{N}_PIP', 'transIn': 'Cut', 'srvAuto': True, 'camPrimary': 'cam1'},
        'CORNER':  {'obsScene': 'CAM1_ANCHOR',  'transIn': 'Mix',  'camPrimary': 'cam1'},
        'WEATHER': {'obsScene': 'WEATHER',      'transIn': 'Mix',  'transOut': 'Mix', 'camPrimary': 'cam4'},
        'SPORTS':  {'obsScene': 'LIVE_EXT',     'transIn': 'Cut',  'camPrimary': ''},
        'CLOSING': {'obsScene': 'CLOSING',      'transIn': 'Mix',  'transOut': 'Fade', 'camPrimary': 'cam1'},
        'LIVE':    {'obsScene': 'LIVE_EXT',     'transIn': 'Cut',  'camPrimary': ''},
        'HEADLINE':{'obsScene': 'CAM1_ANCHOR',  'transIn': 'Cut',  'camPrimary': 'cam1'},
        'BUMPER':  {'obsScene': 'TITLE',        'transIn': 'Cut'},
        'SPECIAL': {'obsScene': '',             'transIn': 'Cut'},
    }

    ts = type_settings.get(item_type, {})
    settings.update(ts)
    return settings


# ══════════════════════════════════════════════
#  PDF 헤더 파싱
# ══════════════════════════════════════════════

def parse_header(all_words_page1):
    """첫 페이지 단어에서 프로그램 메타 추출"""
    header = {
        'title':       '',
        'anc':         '',
        'pd':          '',
        'modifiedAt':  '',
        'date':        '',
        'broadcastAt': '',
        'duration':    '',
    }

    # 전체 텍스트로 패턴 매칭
    all_text = ' '.join(w['text'] for w in all_words_page1)

    # 프로그램명 — 날짜 포함 행에서 추출
    m = re.search(r'(뉴스[\w\-,·]+\([12]\d{3}-\d{2}-\d{2}\))', all_text)
    if m:
        header['title'] = m.group(1)
        # 날짜 추출
        dm = re.search(r'\((\d{4}-\d{2}-\d{2})\)', m.group(1))
        if dm:
            header['date'] = dm.group(1)

    # ANC 파싱
    m = re.search(r'ANC:\s*([\w\s]+?)\s+PD:', all_text)
    if m:
        header['anc'] = m.group(1).strip()

    # PD 파싱
    m = re.search(r'PD:\s*([\w\s]+?)\s+수정일시:', all_text)
    if m:
        header['pd'] = m.group(1).strip()

    # 수정일시
    m = re.search(r'수정일시:\s*([\d\-\s:]+)', all_text)
    if m:
        header['modifiedAt'] = m.group(1).strip()

    return header


# ══════════════════════════════════════════════
#  행 단위 파싱
# ══════════════════════════════════════════════

def group_words_by_row(words, y_tolerance=6):
    """단어들을 y좌표 기준으로 행으로 그룹화"""
    rows = {}
    for w in words:
        y_key = round(w['top'] / y_tolerance) * y_tolerance
        rows.setdefault(y_key, []).append(w)
    # y 좌표 순 정렬, 각 행 내부는 x 좌표 순
    sorted_rows = []
    for y in sorted(rows.keys()):
        row = sorted(rows[y], key=lambda w: w['x0'])
        sorted_rows.append((y, row))
    return sorted_rows


def is_header_row(row_words):
    """헤더 행 여부 (NO, 형식, 아이템 등이 포함된 행)"""
    texts = {w['text'] for w in row_words}
    return {'NO', '형식', '아이템'}.issubset(texts)


def is_page_header(row_words, first_rows_y):
    """페이지 상단 메타 행 여부"""
    if not row_words:
        return False
    top = row_words[0]['top']
    return top < first_rows_y + 80  # 상단 80px 이내


def is_anchor_change_row(row_words):
    """앵커 교대 행 여부"""
    texts = [w['text'] for w in row_words]
    full = ' '.join(texts)
    for pat in ANCHOR_CHANGE_PATTERNS:
        if pat in full and len(texts) <= 4:
            return True
    return False


def parse_row(row_words, srv_counter, debug=False):
    """
    한 행의 단어 목록 → 큐시트 아이템 dict
    반환: (item_dict or None, new_srv_counter)
    """
    if not row_words:
        return None, srv_counter

    full_text = ' '.join(w['text'] for w in row_words)

    # ── NO 컬럼 추출 ──
    no_words = words_in_col(row_words, 'no')
    no_text  = words_text(no_words).strip('※★')

    # ── 아이템 컬럼 추출 ──
    item_words   = words_in_col(row_words, 'item')
    item_text    = words_text(item_words)

    # ── 담당 컬럼 ──
    rep_words    = words_in_col(row_words, 'reporter')
    reporter     = words_text(rep_words)

    # ── 시간 컬럼 ──
    dur_words    = words_in_col(row_words, 'dur')
    dur_text     = words_text(dur_words)

    # ── 합계 컬럼 ──
    cum_words    = words_in_col(row_words, 'cum')
    cum_text     = words_text(cum_words)

    # ── 제목 컬럼 ──
    title_words  = words_in_col(row_words, 'title')
    title_text   = words_text(title_words)

    # ── 부가자막 ──
    sub_words    = words_in_col(row_words, 'subtitle')
    subtitle     = words_text(sub_words)

    # ── A/C 컬럼 ──
    a_words = words_in_col(row_words, 'a')
    c_words = words_in_col(row_words, 'c')
    a_text  = words_text(a_words)
    c_text  = words_text(c_words)

    # 시간이 없는 행은 스킵 (그러나 아이템명만 있는 속행은 허용)
    if not dur_text and not item_text:
        return None, srv_counter

    # 형식 감지 (아이콘 or 텍스트)
    type_raw = ''
    # 아이콘 매핑
    for w in row_words:
        if w['text'] in ICON_TYPE_MAP:
            type_raw = ICON_TYPE_MAP[w['text']]
            break
    # 텍스트로 형식 감지
    if not type_raw:
        for key in TYPE_MAP:
            if item_text.startswith(key) or full_text.startswith(key):
                type_raw = key
                break

    # 아이템 타입 결정
    item_type = guess_item_type(item_text, no_text, reporter, type_raw)

    # 아이템명 정리 — 형식 코드가 붙어있으면 제거
    clean_item = item_text
    for key in list(TYPE_MAP.keys()) + list(ICON_TYPE_MAP.values()):
        if clean_item.startswith(key + ' '):
            clean_item = clean_item[len(key):].strip()

    # 앵커멘트 메타데이터 추출
    anc_meta = extract_anc_metadata(clean_item)

    # OBS 자동 설정 추천
    obs = suggest_obs_settings(item_type, anc_meta['hasAnc'], reporter, clean_item)

    # 서버 교대 카운터 처리
    if obs['srvAuto']:
        srv_n = 1 if srv_counter % 2 == 0 else 2
        obs['obsScene'] = obs['obsScene'].replace('{N}', str(srv_n))
        srv_counter += 1

    # 앵커 A 컬럼 해석
    anc_icon = 'none'
    if a_text:
        # 아이콘 유니코드 분석 (단독/투샷)
        anc_icon = 'single' if len(a_text) < 3 else 'twoshot'

    # C 컬럼 (큐번호) 해석
    cue_num = None
    if c_text:
        c_clean = c_text.strip()
        if c_clean in ('×', 'X', '✕', '\u00d7'):
            cue_num = 'X'
        elif c_clean == '★':
            cue_num = '★'
        elif c_clean.isdigit():
            cue_num = c_clean

    # 시간 파싱
    dur_sec = parse_duration(dur_text)
    cum_sec = parse_duration(cum_text)

    item = {
        'id':          str(uuid4()),
        'no':          no_text or '',
        'type':        item_type,
        'typeRaw':     type_raw,
        'item':        clean_item,
        'reporter':    reporter,
        'dur':         dur_text or '',
        'durSec':      dur_sec,
        'cum':         cum_text or '',
        'cumSec':      cum_sec,
        'title':       title_text,
        'subtitle':    subtitle,
        'anchorIcon':  anc_icon,
        'cueNum':      cue_num,

        # 앵커멘트 메타
        'hasAnc':       anc_meta['hasAnc'],
        'ancDuration':  anc_meta['ancDuration'],
        'ancWarnFlag':  anc_meta['ancWarnFlag'],
        'graphicNeeded':anc_meta['graphicNeeded'],
        'isVideoDan':   anc_meta['isVideoDan'],
        'isCorner':     anc_meta['isCorner'],

        # OBS 설정 (자동 추천값 — 사용자 수정 가능)
        'obsScene':    obs['obsScene'],
        'transIn':     obs['transIn'],
        'transOut':    obs['transOut'],
        'srvAuto':     obs['srvAuto'],
        'camPrimary':  obs['camPrimary'],
        'micMode':     obs['micMode'],
        'cgAutoOn':    obs['cgAutoOn'],
        'cgDelayOn':   obs['cgDelayOn'],
        'cgDelayOff':  obs['cgDelayOff'],
        'camPreset':   obs['camPreset'],

        # 제작 필드 (나중에 채워짐)
        'status':      'empty',
        'articles':    [],
        'clips':       [],
        'cg':          [],
        'note':        '',
        'warnFlag':    anc_meta['ancWarnFlag'],

        # 파싱 메타
        '_parseConfidence': 'high' if (no_text and dur_text and item_text) else 'low',
    }

    if debug:
        print(f"  [{no_text:>3}] {item_type:<10} {clean_item[:30]:<30} {reporter:<10} {dur_text}")

    return item, srv_counter


# ══════════════════════════════════════════════
#  메인 파서
# ══════════════════════════════════════════════

def parse_cuesheet_pdf(pdf_path, debug=False):
    """
    PDF 파일 → 큐시트 JSON 딕셔너리
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"파일 없음: {pdf_path}")

    result = {
        'meta': {},
        'items': [],
        'parseInfo': {
            'sourceFile':  os.path.basename(pdf_path),
            'parsedAt':    datetime.now().isoformat(),
            'pages':       0,
            'itemCount':   0,
            'warnings':    [],
        }
    }

    all_items  = []
    srv_counter = 0
    header_parsed = False

    with pdfplumber.open(pdf_path) as pdf:
        result['parseInfo']['pages'] = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages):
            if debug:
                print(f"\n{'='*60}")
                print(f"PAGE {page_num + 1}")
                print('='*60)

            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            if not words:
                continue

            # 헤더 파싱 (첫 페이지만)
            if not header_parsed:
                result['meta'] = parse_header(words)
                header_parsed = True

            # 행 단위 그룹화
            rows = group_words_by_row(words, y_tolerance=6)
            first_y = rows[0][0] if rows else 0

            prev_was_anchor_change = False
            anchor_change_name     = ''

            for y, row_words in rows:
                # 헤더/메타 행 스킵
                if is_page_header(row_words, first_y):
                    continue
                if is_header_row(row_words):
                    continue

                # 앵커 교대 행 감지
                if is_anchor_change_row(row_words):
                    full = ' '.join(w['text'] for w in row_words)
                    prev_was_anchor_change = True
                    anchor_change_name     = full.strip()
                    if debug:
                        print(f"  [앵커교대] {anchor_change_name}")
                    # 구분 아이템으로 삽입
                    all_items.append({
                        'id':       str(uuid4()),
                        'type':     'ANCHOR_CHANGE',
                        'item':     anchor_change_name,
                        'reporter': anchor_change_name,
                        '_divider': True,
                    })
                    continue

                # 일반 아이템 행 파싱
                item, srv_counter = parse_row(row_words, srv_counter, debug=debug)
                if item:
                    if prev_was_anchor_change:
                        item['anchorBlock'] = anchor_change_name
                        prev_was_anchor_change = False
                    all_items.append(item)

    # 중복/빈 항목 정리
    items = clean_items(all_items)
    result['items'] = items
    result['parseInfo']['itemCount'] = len([i for i in items if not i.get('_divider')])

    # 총 시간 계산
    total_sec = max((i.get('cumSec', 0) for i in items if not i.get('_divider')), default=0)
    result['meta']['totalDuration'] = fmt_duration(total_sec)

    # 저품질 파싱 경고
    low_conf = [i for i in items if i.get('_parseConfidence') == 'low']
    if low_conf:
        result['parseInfo']['warnings'].append(
            f"{len(low_conf)}개 아이템 파싱 신뢰도 낮음 — 수동 확인 필요"
        )

    return result


def clean_items(items):
    """파싱 결과 정리: 중복 제거, 빈 아이템 제거"""
    cleaned = []
    seen_ids = set()

    for item in items:
        if item['id'] in seen_ids:
            continue
        seen_ids.add(item['id'])

        # 완전히 빈 항목 스킵
        if not item.get('_divider'):
            if not item.get('item') and not item.get('dur') and not item.get('no'):
                continue

        cleaned.append(item)

    return cleaned


# ══════════════════════════════════════════════
#  CLI 실행
# ══════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description='뉴스 큐시트 PDF 파서')
    parser.add_argument('pdf',          help='입력 PDF 파일 경로')
    parser.add_argument('--out', '-o',  help='출력 JSON 파일 경로 (없으면 stdout)')
    parser.add_argument('--debug', '-d',action='store_true', help='디버그 출력')
    parser.add_argument('--summary', '-s', action='store_true', help='요약만 출력')
    args = parser.parse_args()

    print(f"[파서] {args.pdf} 파싱 시작...", file=sys.stderr)

    result = parse_cuesheet_pdf(args.pdf, debug=args.debug)

    if args.summary:
        meta  = result['meta']
        info  = result['parseInfo']
        items = result['items']
        real  = [i for i in items if not i.get('_divider')]

        print(f"\n{'='*50}")
        print(f"프로그램: {meta.get('title','—')}")
        print(f"앵커:     {meta.get('anc','—')}")
        print(f"PD:       {meta.get('pd','—')}")
        print(f"방송일:   {meta.get('date','—')}")
        print(f"총 시간:  {meta.get('totalDuration','—')}")
        print(f"{'='*50}")
        print(f"파싱 페이지: {info['pages']}")
        print(f"아이템 수:   {info['itemCount']}")
        print(f"{'='*50}")

        type_counts = {}
        for item in real:
            t = item.get('type','?')
            type_counts[t] = type_counts.get(t, 0) + 1
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  {t:<12}: {c}개")

        print(f"{'='*50}")
        if info['warnings']:
            print("⚠ 경고:")
            for w in info['warnings']:
                print(f"  - {w}")

        print(f"\n아이템 목록:")
        for item in items:
            if item.get('_divider'):
                print(f"\n  ── {item.get('item','구분')} ──")
            else:
                warn = ' ⚠' if item.get('warnFlag') else ''
                print(f"  [{item.get('no','  '):>3}] {item['type']:<10} {item.get('dur',''):>5}  {item.get('item','')[:35]}{warn}")
        return

    # JSON 출력
    json_str = json.dumps(result, ensure_ascii=False, indent=2)

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"[파서] 저장 완료: {args.out}", file=sys.stderr)
        print(f"[파서] 아이템 {result['parseInfo']['itemCount']}개 파싱됨", file=sys.stderr)
    else:
        print(json_str)


if __name__ == '__main__':
    main()
