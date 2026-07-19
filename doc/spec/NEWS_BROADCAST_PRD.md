# 뉴스 방송 제작 시스템 (NBS) — Product Requirements Document

**문서 버전**: 1.0  
**작성일**: 2026-06-23  
**상태**: 작성 중  
**프로젝트 코드명**: NBS (News Broadcast System)

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 구성 원칙](#2-시스템-구성-원칙)
3. [사용자 및 권한 체계](#3-사용자-및-권한-체계)
4. [소프트웨어 구성](#4-소프트웨어-구성)
5. [Phase 1 — MVP: PDF 파싱 + 큐시트 + OBS 기본 진행](#5-phase-1--mvp)
6. [Phase 2 — 통합 제작 시스템](#6-phase-2--통합-제작-시스템)
7. [Phase 3 — 멀티유저 + 분리 서버](#7-phase-3--멀티유저--분리-서버)
8. [장비 및 인프라 구성](#8-장비-및-인프라-구성)
9. [OBS 연동 규칙](#9-obs-연동-규칙)
10. [데이터 모델](#10-데이터-모델)
11. [개발 로드맵](#11-개발-로드맵)

---

## 1. 프로젝트 개요

### 1-1. 배경과 목적

방송 뉴스 진행은 현재 큐시트(PDF), OBS, 기사 작성 시스템이 각각 분리되어 운용되고 있어 PD와 제작진의 수동 작업이 많다. NBS는 이 세 가지를 하나로 통합하여:

- PDF 큐시트를 자동 파싱해 디지털 큐시트로 변환
- 큐시트 아이템별로 OBS 씬·서버·자막을 자동 제어
- 다수의 제작진이 동시에 기사·영상·자막을 준비하고 PD는 방송 진행에만 집중

### 1-2. 핵심 가치

| 가치 | 설명 |
|------|------|
| 자동화 | "다음▶" 버튼 하나로 씬전환·클립로드·자막이 자동 실행 |
| 협업 | 5대 클라이언트가 동시에 큐시트·기사·영상 준비 |
| 유연성 | Phase 1 단일 Mac → Phase 2·3 서버 분리로 무중단 전환 |
| 안전성 | SRV3 예비 서버·자동 재연결·폴백 규칙으로 방송 사고 방지 |

### 1-3. 적용 대상

- 뉴스 프로그램 (뉴스투데이, 뉴스데스크, 뉴스25 등)
- 앵커 2인 공동진행 구조
- OBS Studio 기반 방송 시스템

---

## 2. 시스템 구성 원칙

### 2-1. 배포 모드 (단일 설정값으로 전환)

```
DEPLOY_MODE=LOCAL   ← Phase 1: 서버+OBS 동일 Mac
DEPLOY_MODE=REMOTE  ← Phase 2·3: 서버 분리
```

**LOCAL 모드 (Phase 1)**
```
[단일 Mac]
├── 백엔드 서버 (localhost:3000)
├── OBS Studio  (localhost:4455)
├── NBS 방송진행 앱 (브라우저)
├── NPS 큐시트 제작 (브라우저)
└── MARS 기사 작성 (브라우저)
```

**REMOTE 모드 (Phase 2·3)**
```
[백엔드 서버 PC]          [방송 Mac]            [제작 PC 1~5]
 API + DB + WS Sync  ←→  OBS + NBS 진행앱  ←→  MARS + NPS
 192.0.2.4:3000       localhost:4455          브라우저
```

### 2-2. 전환 방법

`.env` 파일의 `DEPLOY_MODE`와 `OBS_HOST` 값만 변경하면 코드 수정 없이 전환 완료:

```bash
# Phase 1 → Phase 2 전환 시 변경 사항
DEPLOY_MODE=REMOTE
OBS_HOST=192.0.2.5        # 방송 Mac IP
SERVER_PUBLIC_URL=http://192.0.2.4:3000
OBS_AUTO_CONNECT=true
```

---

## 3. 사용자 및 권한 체계

### 3-1. 역할 정의

| 역할 | 코드 | 레벨 | 직책 | 주요 SW |
|------|------|------|------|---------|
| 편성장·PD | ADMIN | 5 | 총괄 책임자 | MARS + NPS + NBS |
| 기자·편집자 | EDITOR | 4 | 기사 작성 | MARS |
| 영상 담당 | MEDIA | 3 | 영상 매칭 | NPS (영상탭) |
| 자막 담당 | CG | 2 | CG 관리 | NPS (자막탭) |
| 기술·보조 | MONITOR | 1 | 모니터링 | 읽기 전용 |

### 3-2. 기능별 권한 매트릭스

| 기능 | ADMIN | EDITOR | MEDIA | CG | MONITOR |
|------|:-----:|:------:|:-----:|:--:|:-------:|
| 큐시트 생성·편집 | ✓ | — | — | — | — |
| 큐시트 확정 | ✓ | — | — | — | — |
| 큐시트 조회 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 기사 작성·출고 | ✓ | ✓ | — | — | — |
| 기사 조회 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 영상 업로드·매칭 | ✓ | — | ✓ | — | — |
| CG 자막 전송 | ✓ | ✓ | — | ✓ | — |
| OBS 씬 전환 | ✓ | — | — | — | — |
| OBS 설정 변경 | ✓ | — | — | — | — |
| 사용자 관리 | ✓ | — | — | — | — |
| 시스템 로그 조회 | ✓ | — | — | — | ✓ |

---

## 4. 소프트웨어 구성

### 4-1. MARS — 기사 제작 시스템

**목적**: 기자·편집자가 기사를 작성·검색·출고하는 시스템  
**파일**: `mars-news-editor.html`

| 화면 | 기능 |
|------|------|
| 기사 목록 | 전체/내기사/즐겨찾기 탭, 부서·날짜·출고여부 필터 |
| 기사 에디터 | 2컬럼 — 좌: 자막 박스 목록, 우: 앵커멘트·리포트 본문 |
| 자막 박스 | 타입별(하단/이름/위치/코너/긴급) CG 항목 편집 |
| 태그 시스템 | `◀ SYN ▶`, `cg)`, `타가)`, `◀ INT ▶` 태그 삽입·하이라이팅 |

### 4-2. NPS — 큐시트 제작 시스템

**목적**: 편성장·영상·자막 담당자가 큐시트를 편성하고 소재를 연결하는 시스템  
**파일**: `nps-news-system.html`

| 화면 | 기능 |
|------|------|
| 큐시트 테이블 | NO·형식·아이템·기사·자막·A·C·영상·담당·시간·합계·제목 |
| 아이템매칭 탭 | 기사 검색·선택·매칭, 앵커멘트 미리보기 |
| 영상조회 탭 | 영상 검색, 드래그앤드롭 매칭, 듀얼 플레이어 |
| 자막조회 탭 | CG 항목 편집, OBS 전송 |
| 앵커멘트조회 탭 | 매칭된 기사의 앵커/리포트 본문 확인 |

### 4-3. NBS — 방송 진행 시스템

**목적**: PD 1인이 방송 중 OBS를 제어하고 큐시트를 진행하는 시스템  
**파일**: `news-broadcast-system.html`

| 화면 | 기능 |
|------|------|
| 큐시트 진행뷰 | 현재 아이템 강조, 이전·시작·다음 버튼 |
| 비디오 스위처 | PGM·PVW 버스, CUT·AUTO·전환효과 |
| 탈리 모니터 | 소스별 ON AIR·PREVIEW 표시 |
| 오디오 | 앵커 MIC 레벨 페이더·뮤트·VU미터 |
| CG 자막 | 아이템별 자막 큐 목록, 타입별 전송·해제 |
| 서버 상태 | SRV1·2·3 ON AIR·STANDBY·SPARE 표시 |

---

## 5. Phase 1 — MVP

**목표**: 단일 Mac에서 PDF 큐시트 파싱 → 디지털 큐시트 → OBS 기본 진행까지 완성  
**기간**: 4~6주  
**담당**: 1인 개발 가능

### 5-1. PDF 큐시트 파싱

#### 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| P1-01 | PDF 파일 드래그앤드롭 또는 파일 선택으로 업로드 | 필수 |
| P1-02 | pdfplumber(Python) 또는 pdf.js(JS)로 텍스트 추출 | 필수 |
| P1-03 | 추출된 텍스트에서 컬럼 구조 자동 인식 | 필수 |
| P1-04 | NO, 형식, 아이템명, 담당, 시간, 합계, 제목, 부가자막 파싱 | 필수 |
| P1-05 | 파싱 결과를 JSON 구조로 변환 | 필수 |
| P1-06 | 파싱 오류 항목 표시 및 수동 수정 UI | 필수 |
| P1-07 | 프로그램명·앵커·PD·방송일시 헤더 파싱 | 필수 |
| P1-08 | 뉴스데스크·뉴스투데이·뉴스25 등 다양한 형식 지원 | 권장 |

#### 파싱 규칙

```python
# 형식 컬럼 → 아이템 타입 매핑
TYPE_MAP = {
    '완': 'REPORT',    # 완성 VCR 리포트 → SRV 자동 배정
    '단': 'ANCHOR',    # 단신 → CAM1
    '타': 'TITLE',     # 타이틀 → TITLE 씬
    '출': 'CORNER',    # 출연 코너 (투데이 전용)
    'NT': 'NT',        # 뉴스탑 → CAM+SRV PIP
}

# 아이템명 패턴 → 추가 정보 추출
PATTERNS = {
    r'\[(\d+:\d+)\]': 'anc_duration',      # [1:47] → 앵커멘트 길이
    r'\[:\]':         'has_anc',            # [:] → 앵커멘트 있음
    r'\*+앵멘':       'anc_confirm_needed', # ***앵멘 → 앵멘 확인 필요
    r'##':            'graphic_needed',     # ## → 그래픽 처리
    r'동영상D':        'video_dan',         # 동영상D → 동영상 단신
}

# 앵커 교대 행 감지
ANCHOR_CHANGE_PATTERNS = ['남앵커', '여앵커', '남녀앵커', '조현용 앵커', '김수지 앵커']
```

#### 파싱 결과 JSON 구조

```json
{
  "meta": {
    "title":       "뉴스투데이-1,2부",
    "anc":         "손령 정슬기",
    "pd":          "박철현 류도현",
    "date":        "2026-06-23",
    "broadcastAt": "06:00:00",
    "duration":    "00:58:00",
    "sourceFile":  "뉴스투데이_큐시트_샘플.pdf",
    "parsedAt":    "2026-06-23T05:30:00"
  },
  "items": [
    {
      "id":         "uuid",
      "no":         "1",
      "type":       "REPORT",
      "item":       "[:이란, IAEA 사찰 재개 수용...",
      "reporter":   "허유신",
      "dur":        "01:50",
      "cumDur":     "03:26",
      "subtitle":   "이란, IAEA 사찰 수용..",
      "addlSubtitle":"",
      "ancIcon":    "single",
      "cueNum":     "X",
      "hasAnc":     true,
      "ancDuration": "01:47",
      "warnFlag":   false,
      "obsScene":   "",
      "transIn":    "Cut",
      "sources":    [],
      "clips":      [],
      "cg":         []
    }
  ]
}
```

### 5-2. OBS 연동 필수 설정

#### 큐시트 아이템에서 설정 가능한 OBS 항목

| 항목 | 설명 | 입력 방식 |
|------|------|---------|
| OBS 씬명 | 전환할 OBS 씬 이름 | 드롭다운 (OBS 씬 목록 자동 로드) |
| 카메라 배정 | CAM1~4 중 사용할 카메라 | 체크박스 다중 선택 |
| 서버 배정 | SRV1/SRV2/SRV3 (자동교대 or 수동) | 드롭다운 또는 자동 |
| 전환 효과 IN | CUT / DISSOLVE / FADE / WIPE | 드롭다운 |
| 전환 효과 OUT | CUT / DISSOLVE / FADE | 드롭다운 |
| CG 자막 소스 | CG_LOWER_THIRD / CG_NAME / CG_BREAKING | 드롭다운 |
| 탈리 설정 | 해당 아이템 ON AIR 시 탈리 표시 여부 | 토글 |
| 프리셋 | 카메라 프리셋 번호 (PTZ 카메라) | 숫자 입력 |
| 앵커 MIC | MIC1 / MIC2 / 모두 / 음소거 | 드롭다운 |
| 클립 경로 | 서버 재생 영상 파일 경로 | 파일 브라우저 |

#### OBS 씬 자동 추천 규칙

```
아이템 타입 → 추천 씬:
TITLE   → TITLE
CM      → CM_PRE
OPEN    → CAM1_ANCHOR (앵커 투샷이면 CAM1_CAM2_2SHOT)
ANCHOR  → CAM1_ANCHOR
BRIDGE  → CAM1_ANCHOR (단, 직전과 다른 카메라)
REPORT  → SRV1_VCR or SRV2_VCR (교대)
NT      → CAM1_SRV1_PIP or CAM1_SRV2_PIP
LIVE    → LIVE_EXT
WEATHER → WEATHER
STOCK   → LIVE_STOCK
CLOSING → CLOSING
```

#### PTZ 카메라 프리셋 규칙

```
CAM1 프리셋:
  1 = 앵커 단독 (기본 포지션)
  2 = 앵커 클로즈업
  3 = 앵커+자막 (하단자막 보이는 구도)

CAM2 프리셋:
  1 = 앵커 서브 각도
  2 = 투샷 구도

CAM3 프리셋:
  1 = 와이드 스튜디오
  2 = 앵커 측면

CAM4 프리셋:
  1 = 날씨 전용 구도
  2 = 클로즈업 인서트
```

### 5-3. 서버 교대 규칙

```
글로벌 카운터 N (프로그램 시작 시 0 초기화)
  N % 2 == 0 → SRV1 온에어, SRV2 다음 클립 사전 로드
  N % 2 == 1 → SRV2 온에어, SRV1 다음 클립 사전 로드
  SRV3 = 항상 예비 (자동 배정 금지, 수동 긴급 투입만)

아이템 시작 시:
  1. 현재 SRV에 클립 로드 → 재생
  2. 다음 SRV에 다음 아이템 클립 사전 로드
  3. 카운터 N++

SRV3 긴급 투입 조건:
  - SRV1/SRV2 기술 오류
  - 클립 로드 실패
  - PD 수동 판단

SRV3 투입 절차:
  1. PD "SRV3 긴급" 버튼 클릭
  2. 확인 팝업 → 승인
  3. SRV3_VCR 씬으로 즉시 CUT
  4. 카운터 N 리셋 (다음 아이템부터 SRV1→SRV2 재시작)
```

### 5-4. Phase 1 전환 안전 규칙

```
전환 전 체크:
  ① 다음 OBS 씬이 존재하는가?  → 없으면 전환 차단 + 경고
  ② PVW ≠ PGM 인가?           → 동일하면 전환 차단
  ③ SRV 클립 로드 완료 여부    → 미완료 시 경고 (차단 아님)
  ④ 타이머 10초 미만 시        → 앰버 경고, 5초 미만 레드 경고

폴백:
  씬 없음 → BLACK 씬으로 전환 + 오류 로그
  OBS 연결 끊김 → 재연결 시도 (3초 간격, 최대 10회)
  전환 무응답(2초) → 재시도 1회 후 수동 전환 요청
```

### 5-5. Phase 1 구현 범위

| 번호 | 기능 | 상태 |
|------|------|------|
| 1 | PDF 큐시트 업로드 및 파싱 | 개발 필요 |
| 2 | 파싱 결과 큐시트 뷰 + 수동 편집 | 개발 필요 |
| 3 | 큐시트 아이템별 OBS 설정 (씬·카메라·서버·자막·PTZ·MIC) | 개발 필요 |
| 4 | OBS WebSocket 연결 (localhost:4455) | 완료 (NBS) |
| 5 | 방송 진행 — 다음 버튼 → 씬전환·클립로드·자막 자동 | 완료 (NBS) |
| 6 | 서버 교대 자동화 (SRV1↔SRV2, SRV3 예비) | 완료 (NBS) |
| 7 | 탈리 표시 (PGM/PVW 소스별) | 완료 (NBS) |
| 8 | 앵커 MIC 레벨 자동 제어 | 완료 (NBS) |
| 9 | PTZ 카메라 프리셋 자동 호출 | 개발 필요 |
| 10 | JSON 큐시트 저장·불러오기 | 완료 |

---

## 6. Phase 2 — 통합 제작 시스템

**목표**: 기사 작성(MARS)·큐시트(NPS)·방송(NBS) 통합 + 백엔드 서버 연동  
**기간**: 8~12주  
**사용자**: 최대 5명 동시 접속

### 6-1. 백엔드 서버 구축

#### 기술 스택

| 레이어 | 기술 | 선택 이유 |
|--------|------|---------|
| 런타임 | Node.js 20 LTS | obs-websocket-js 네이티브 지원 |
| 프레임워크 | Express 4 | 경량, 빠른 개발 |
| 실시간 | Socket.io 4 | WebSocket + 폴링 폴백 |
| DB (Phase 2 초기) | SQLite (better-sqlite3) | 설치 불필요, 단일 파일 |
| DB (Phase 2 후기) | PostgreSQL 15 | 다중 동시 접속, 백업 |
| 인증 | JWT (access 8h + refresh 7d) | stateless |
| 파일 | multer + 로컬 스토리지 | Phase 2 기본 |

#### API 엔드포인트 전체 목록

```
인증
  POST   /api/auth/login         로그인 → JWT 발급
  POST   /api/auth/refresh       토큰 갱신
  GET    /api/auth/me            내 정보

기사 (EDITOR 이상)
  GET    /api/articles           목록 (검색·필터·페이지네이션)
  POST   /api/articles           생성
  GET    /api/articles/:id       상세
  PUT    /api/articles/:id       수정
  DELETE /api/articles/:id       삭제 (ADMIN)
  POST   /api/articles/:id/publish  출고
  GET    /api/articles/:id/cg    자막 목록

큐시트 (ADMIN 편집, 나머지 조회)
  GET    /api/cuesheets          목록
  POST   /api/cuesheets          생성
  GET    /api/cuesheets/:id      상세 + 아이템 전체
  PUT    /api/cuesheets/:id      수정
  POST   /api/cuesheets/:id/confirm  확정 (ADMIN)
  POST   /api/cuesheets/parse-pdf    PDF 파싱 → JSON 반환

큐시트 아이템
  POST   /api/cuesheets/:id/items        아이템 추가
  PUT    /api/cue-items/:id              아이템 수정 (OBS 설정 포함)
  DELETE /api/cue-items/:id             아이템 삭제
  POST   /api/cue-items/:id/articles    기사 매칭
  DELETE /api/cue-items/:id/articles/:aid 기사 해제
  POST   /api/cue-items/:id/media       영상 매칭
  DELETE /api/cue-items/:id/media/:mid  영상 해제
  PUT    /api/cue-items/:id/subtitles   자막 업데이트

미디어 (MEDIA 이상)
  GET    /api/media              목록 (검색)
  POST   /api/media/upload       업로드
  DELETE /api/media/:id          삭제

CG 자막
  GET    /api/cg/templates       템플릿 목록
  POST   /api/cg/templates       템플릿 생성
  POST   /api/cg/send            OBS 자막 전송 (CG 이상)

OBS (ADMIN)
  GET    /api/obs/status         OBS 상태
  GET    /api/obs/scenes         씬 목록
  POST   /api/obs/scene          씬 전환
  POST   /api/obs/cg             자막 전송
  POST   /api/obs/media/load     클립 로드
  POST   /api/obs/media/control  클립 재생 제어

사용자 (ADMIN)
  GET    /api/users              목록
  POST   /api/users              생성
  PUT    /api/users/:id          수정
  DELETE /api/users/:id          비활성화

시스템
  GET    /health                 헬스체크
  GET    /api/config             클라이언트용 서버 설정
```

### 6-2. PDF 파싱 서버 구현

#### 파싱 엔진 (Node.js + pdf-parse)

```javascript
// POST /api/cuesheets/parse-pdf
// multipart/form-data { file: PDF }

async function parsePDF(buffer) {
  const text = await extractText(buffer);
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  
  const meta  = parseHeader(lines);
  const items = parseItems(lines);
  
  return { meta, items };
}

function parseHeader(lines) {
  // 패턴: "ANC: 손령 정슬기  PD: 박철현 수정일시: ..."
  const ancMatch  = lines.join(' ').match(/ANC[:\s]+([^\s]+(?:\s+[^\s]+)?)\s+PD/);
  const pdMatch   = lines.join(' ').match(/PD[:\s]+([^\s]+)/);
  const titleLine = lines.find(l => l.includes('뉴스') && l.includes('(20'));
  // ...
}

function parseItems(lines) {
  const items = [];
  let cumSec = 0;
  
  for (const line of lines) {
    // NO 형식 아이템 A C 담당 시간 합계 제목 부가자막
    const match = line.match(
      /^(\S+)\s+(완|단|타|출|NT|특)\s+(.+?)\s+(\S+)?\s+(\d+:\d+)\s+(\d+:\d+)\s*(.*)$/
    );
    if (match) {
      items.push(mapToItem(match, cumSec));
      cumSec += parseDur(match[5]);
    }
    
    // 앵커 교대 행 감지
    if (isAnchorChange(line)) {
      items.push({ type: 'ANCHOR_CHANGE', reporter: extractAnchorName(line) });
    }
  }
  return items;
}
```

### 6-3. 실시간 동기화

#### WebSocket 이벤트 설계

```
서버 → 클라이언트 (브로드캐스트):
  cuesheet:item:update   큐시트 아이템 변경
  cuesheet:confirmed     큐시트 확정
  broadcast:cue:advance  진행 큐 이동 (모든 화면 동기화)
  obs:scene:pgm          OBS PGM 씬 변경
  obs:scene:pvw          OBS PVW 씬 변경
  obs:media:ended        서버 클립 재생 완료
  obs:connected          OBS 연결됨
  obs:disconnected       OBS 연결 끊김
  cg:sent                자막 전송됨 (모든 화면 표시)

클라이언트 → 서버 (REMOTE 모드):
  obs:scene:set          씬 전환 요청
  obs:cg:send            자막 전송 요청
  obs:media:load         클립 로드 요청
  obs:media:control      클립 재생 제어
  obs:volume:set         볼륨 설정
  cuesheet:join          큐시트 룸 참가
```

### 6-4. Phase 2 구현 범위

| 번호 | 기능 | 우선순위 |
|------|------|---------|
| 1 | 백엔드 서버 (Node.js + SQLite) | 필수 |
| 2 | JWT 로그인 + 5종 권한 체계 | 필수 |
| 3 | 기사 CRUD API (MARS 연동) | 필수 |
| 4 | 큐시트 CRUD API (NPS 연동) | 필수 |
| 5 | PDF 파싱 API + 서버 처리 | 필수 |
| 6 | Socket.io 실시간 동기화 | 필수 |
| 7 | 영상 업로드 API | 필수 |
| 8 | CG 템플릿 관리 | 권장 |
| 9 | 방송 로그 기록 | 권장 |
| 10 | 클라이언트 앱 서버 서빙 | 권장 |

---

## 7. Phase 3 — 멀티유저 + 분리 서버

**목표**: 서버 분리 + 외부 접속 + 운영 안정화 + 고급 자동화  
**기간**: 12~16주  
**사용자**: 최대 10명 동시, 외부 원격 접속

### 7-1. 서버 분리 구성

```
[백엔드 서버 — 상시 가동]       [방송 Mac — 방송 시간만]
 Linux / NAS / Mini PC         Mac M2 Pro 이상
 192.0.2.4                 192.0.2.5
 ├── API 서버 :3000             ├── OBS Studio :4455
 ├── DB (PostgreSQL) :5432     └── NBS 방송진행 앱
 ├── 미디어 서버 :9000
 └── WS Sync :3001

[제작 클라이언트 — 사무실 어디서나]
 PC 1~5: http://192.0.2.4:3000
 MARS + NPS 브라우저 접속
```

### 7-2. 추가 요구사항

#### 7-2-1. 고급 PDF 파싱

| ID | 요구사항 |
|----|---------|
| P3-01 | 다중 PDF 동시 처리 (뉴스투데이 1·2부, 뉴스데스크 등) |
| P3-02 | AI 보조 파싱 — 불규칙 형식 처리 (Claude API 연동) |
| P3-03 | 파싱 템플릿 저장 (프로그램별 컬럼 위치 기억) |
| P3-04 | 이전 큐시트와 차이점 하이라이팅 |

#### 7-2-2. 고급 OBS 자동화

| ID | 요구사항 |
|----|---------|
| P3-05 | PTZ 카메라 프리셋 자동 호출 (아이템 타입별) |
| P3-06 | 자막 자동 타이밍 (아이템 시작 +2초 ON, 종료 -3초 OFF) |
| P3-07 | 다음 클립 사전 로드 자동화 (2아이템 앞에서) |
| P3-08 | 미디어 재생 종료 이벤트 → 자동 다음 큐 신호 |
| P3-09 | UNDO 기능 (직전 PGM 복구) |
| P3-10 | 전환 로그 전체 저장 (씬·자막·클립 타임스탬프) |

#### 7-2-3. 멀티유저 충돌 방지

| ID | 요구사항 |
|----|---------|
| P3-11 | 낙관적 잠금 (Optimistic Lock) — 동시 편집 충돌 감지 |
| P3-12 | 아이템 편집 중 표시 ("OOO 편집 중") |
| P3-13 | 확정된 큐시트는 ADMIN만 잠금 해제 가능 |
| P3-14 | 변경 이력 (Revision History) 저장 및 롤백 |

#### 7-2-4. 미디어 관리

| ID | 요구사항 |
|----|---------|
| P3-15 | 파일명 규칙 자동 검증 (`프로그램코드-기자명-순서-타입`) |
| P3-16 | 클립-큐시트 자동 매칭 (파일명 패턴 기반) |
| P3-17 | 영상 메타데이터 자동 추출 (길이, 해상도, 코덱) |
| P3-18 | 미디어 만료 관리 (방송 후 N일 자동 정리) |

#### 7-2-5. 보안 및 운영

| ID | 요구사항 |
|----|---------|
| P3-19 | HTTPS + WSS (TLS 인증서) |
| P3-20 | VPN 또는 Tailscale 원격 접속 |
| P3-21 | 자동 DB 백업 (일 1회, 7일 보관) |
| P3-22 | 헬스체크 대시보드 (서버·OBS·클라이언트 상태) |
| P3-23 | 장애 알림 (OBS 연결 끊김, 서버 응답 없음 → 슬랙·카카오 알림) |

#### 7-2-6. 태블릿/모바일 지원

| ID | 요구사항 |
|----|---------|
| P3-24 | iPad 반응형 NBS 방송진행 앱 |
| P3-25 | 앵커 텔레프롬프터 뷰 (앵커용 태블릿) |
| P3-26 | 모바일 알림 (자막 전송, 클립 로드 완료) |

---

## 8. 장비 및 인프라 구성

### 8-1. 최소 구성 (Phase 1)

```
Mac M2 Pro (32GB RAM, 1TB SSD)
├── OBS Studio 28+
├── NBS 방송진행 앱 (Chrome)
├── NPS 큐시트 제작 (Chrome)
└── 연결 장비:
    ├── CAM 1~4: USB 캡처카드 or NDI 카메라
    ├── 앵커 MIC ×2: USB 오디오 인터페이스
    └── HDMI 케이블 (모니터 연결)

모니터 1: OBS 멀티뷰 (8분할)
모니터 2: NBS 방송진행 앱
```

### 8-2. 권장 구성 (Phase 2·3)

```
[백엔드 서버 (상시)]
  Intel NUC or Mac Mini M2
  - RAM: 16GB 이상
  - SSD: 2TB (영상 클립 저장)
  - OS: Ubuntu 22.04 or macOS

[방송 Mac (방송 전용)]
  Mac M2 Pro 이상
  - RAM: 32GB 이상
  - 네트워크: 유선 기가비트 필수

[제작 클라이언트 1~5]
  일반 PC or Mac (브라우저만 있으면 됨)

[스위치/공유기]
  기가비트 이더넷 스위치 (Wi-Fi 금지)
  VLAN 분리: 방송망 / 제작망 / 인터넷망
```

### 8-3. OBS 씬 컬렉션 표준 목록

```
NEWS_BROADCAST (씬 컬렉션명)
│
├── TITLE                  프로그램 타이틀
├── CM_PRE                 전 CM
├── CM_POST                후 CM
├── CAM1_ANCHOR            앵커1 단독
├── CAM2_ANCHOR            앵커2 단독
├── CAM1_CAM2_2SHOT        투샷
├── CAM3_WIDE              와이드
├── CAM4_CLOSEUP           클로즈업
├── SRV1_VCR               서버1 풀스크린
├── SRV2_VCR               서버2 풀스크린
├── SRV3_VCR               서버3 예비
├── SRV1_VCR_CG            서버1 + 하단자막
├── SRV2_VCR_CG            서버2 + 하단자막
├── CAM1_SRV1_PIP          앵커1 + 서버1 PIP (뉴스탑)
├── CAM1_SRV2_PIP          앵커1 + 서버2 PIP
├── LIVE_EXT               외부 중계
├── LIVE_STOCK             증권 LIVE
├── WEATHER                날씨
├── CLOSING                클로징
└── BLACK                  블랙 (비상)

OBS 소스 표준 이름 (필수 준수):
  CAM1, CAM2, CAM3, CAM4       카메라
  SERVER1, SERVER2, SERVER3    미디어 소스
  앵커1_마이크, 앵커2_마이크     오디오
  CG_LOWER_THIRD               하단자막
  CG_NAME                      이름자막
  CG_BREAKING                  긴급자막
  LOGO_OVERLAY                 로고
```

---

## 9. OBS 연동 규칙

### 9-1. 카메라 전환 규칙

```
C-1: 앵커 단독 → CAM1 기본 (CAM2는 PVW)
C-2: 투샷 → CAM1_CAM2_2SHOT
C-3: VCR 직전 → 현재 카메라 유지 → VCR 시작과 동시에 SRV 씬 전환
C-4: VCR → 앵커 복귀 → 클립 종료 -5초에 PVW에 CAM1 세팅
C-5: 동일 카메라 연속 금지 → 반드시 다른 씬 경유
```

### 9-2. 자막 자동 ON/OFF 규칙

```
아이템 타입별 자막 타이밍:
  REPORT:
    ① PGM 전환 +2초: CG_LOWER_THIRD ON (리포트 제목)
    ② +7초: OFF
    ③ 기자 등장: CG_NAME ON → +5초 OFF

  OPEN:
    ① +5초: CG_NAME ON (앵커 이름)
    ② +8초: CG_NAME OFF

  NT:
    ① PGM 전환 동시: CG_LOWER_THIRD ON (NT 제목)
    ② 앵커 멘트 중반: OFF

  LIVE:
    ① PGM 전환 동시: CG_LOCATION ON (현장 위치)

  WEATHER:
    ① PGM 전환 동시: CG_CORNER_TITLE ON ("날씨")
    ② +3초: OFF

  CLOSING:
    ① 마지막 멘트 종료: CG_CLOSING ON
```

### 9-3. 앵커 MIC 자동 제어 규칙

```
씬별 MIC 레벨:
  CAM* 씬 (앵커 직접):
    앵커1_마이크: 80% (−2dB)
    앵커2_마이크: 80%

  SRV* 씬 (VCR 재생):
    앵커1_마이크: 15% (−15dB, 배경음 수준)
    앵커2_마이크: 15%

  LIVE_* 씬:
    앵커*_마이크: 0% (뮤트)

  WEATHER 씬:
    앵커1_마이크: 80%
    앵커2_마이크: 0%

수동 오버라이드:
  PD가 MIC 레벨 수동 조정 시 → 해당 아이템 종료까지 유지
  다음 아이템으로 이동 시 → 자동 레벨로 복귀
```

---

## 10. 데이터 모델

### 10-1. 핵심 테이블 관계

```
users ──< articles
users ──< cuesheets
cuesheets ──< cue_items
cue_items ──< cue_item_articles >── articles
cue_items ──< cue_item_media    >── media_files
cue_items ──< cue_item_subtitles
users ──< cg_templates
cue_items.obsScene → OBS 씬명 (텍스트 참조)
```

### 10-2. 큐 아이템 OBS 설정 필드

```sql
-- cue_items 테이블의 OBS 관련 컬럼
obs_scene      TEXT,          -- 전환할 OBS 씬명
trans_in       TEXT DEFAULT 'Cut',  -- 전환 효과 IN
trans_out      TEXT DEFAULT 'Cut',  -- 전환 효과 OUT
cam_primary    TEXT,          -- 주 카메라 (cam1~cam4)
cam_secondary  TEXT,          -- 보조 카메라
srv_slot       TEXT,          -- 서버 슬롯 (srv1/srv2/srv3/auto)
cam_preset     INTEGER,       -- PTZ 카메라 프리셋 번호
mic_mode       TEXT DEFAULT 'auto', -- MIC 제어 모드 (auto/manual)
mic1_level     REAL DEFAULT 0.8,    -- 앵커1 MIC 레벨 (0~1)
mic2_level     REAL DEFAULT 0.8,    -- 앵커2 MIC 레벨 (0~1)
cg_auto        INTEGER DEFAULT 1,   -- 자막 자동 ON/OFF
cg_delay_on    INTEGER DEFAULT 2,   -- 자막 ON 딜레이 (초)
cg_delay_off   INTEGER DEFAULT 5,   -- 자막 OFF 딜레이 (초)
tally_enabled  INTEGER DEFAULT 1    -- 탈리 표시 여부
```

---

## 11. 개발 로드맵

### 단계별 일정

```
Phase 1 (MVP) — 4~6주
  Week 1~2: PDF 파싱 엔진 + 큐시트 뷰
  Week 3~4: OBS 설정 UI (씬·카메라·서버·자막·PTZ·MIC)
  Week 5~6: 방송 진행 테스트 + 버그 수정

Phase 2 (통합) — 8~12주
  Week 1~3: 백엔드 서버 (Node.js + SQLite)
  Week 4~5: JWT 인증 + 권한 체계
  Week 6~8: 기사·큐시트·미디어 API
  Week 9~10: Socket.io 실시간 동기화
  Week 11~12: 통합 테스트 + 리허설

Phase 3 (완성) — 12~16주
  Week 1~4: 서버 분리 + PostgreSQL 전환
  Week 5~8: 고급 자동화 (PTZ·자막타이밍·사전로드)
  Week 9~12: 멀티유저 충돌 방지 + 이력 관리
  Week 13~16: 보안 강화 + 운영 안정화
```

### 현재 완료 파일 목록

```
news-broadcast-system.html   NBS 방송진행 (OBS WebSocket 연동)
nps-news-system.html         NPS 큐시트 제작
mars-news-editor.html        MARS 기사 작성
news-server/
  server.js                  백엔드 메인 서버
  config/database.js         DB 초기화 (SQLite)
  middleware/auth.js         JWT 인증·권한
  services/obs-bridge.js     OBS Bridge (LOCAL/REMOTE)
  ws/socket-handler.js       Socket.io 핸들러
  routes/auth.js             인증 API
  .env.example               환경 설정 템플릿
obsnewscontrol.md            OBS 연동 규칙 문서
system-architecture.md       시스템 아키텍처 문서
```

---

*NBS PRD v1.0 — 2026-06-23*  
*다음 업데이트: Phase 1 개발 완료 후 v1.1*
