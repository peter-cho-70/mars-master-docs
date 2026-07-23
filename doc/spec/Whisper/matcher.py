# -*- coding: utf-8 -*-
"""
matcher.py
----------
STT로 인식된 텍스트 조각을 기사 원문과 비교해서
현재 낭독 중인 대략적인 위치(문장 인덱스)를 추정하는 모듈.

- 기사 원문은 문장 단위로 미리 분절해둔다.
- 인식된 텍스트가 들어올 때마다, "현재 위치 근처"의 몇 개 문장과만
  유사도를 비교한다 (전체 기사와 매번 비교하면 느리고, 역행도 방지됨).
- 유사도 계산은 rapidfuzz(설치돼 있으면) 또는 difflib(표준 라이브러리)를 사용.
"""

import re

try:
    from rapidfuzz import fuzz
    _USE_RAPIDFUZZ = True
except ImportError:
    import difflib
    _USE_RAPIDFUZZ = False


def split_sentences(article_text: str):
    """기사 원문을 문장 단위로 분리한다.
    한국어 뉴스 원고는 보통 '다.', '요.', '까?', '!' 등으로 끝나므로
    이를 기준으로 간단히 분리한다. 필요시 더 정교한 규칙으로 교체 가능.
    """
    text = article_text.strip()
    # 문장 종결부호 뒤에서 분리 (부호는 유지)
    raw = re.split(r'(?<=[.!?」』])\s+', text)
    sentences = [s.strip() for s in raw if s.strip()]
    return sentences


def _normalize(text: str) -> str:
    """비교를 위해 공백/문장부호 등을 정리한다."""
    text = re.sub(r'[^\w가-힣]', '', text)
    return text.lower()


def _similarity(a: str, b: str) -> float:
    """0~100 범위의 유사도 점수."""
    a, b = _normalize(a), _normalize(b)
    if not a or not b:
        return 0.0
    if _USE_RAPIDFUZZ:
        return fuzz.partial_ratio(a, b)
    else:
        return difflib.SequenceMatcher(None, a, b).ratio() * 100


class ArticleMatcher:
    """
    기사 문장 리스트를 받아, STT 조각이 들어올 때마다
    '현재 낭독 위치로 추정되는 문장 인덱스'를 반환한다.

    - current_idx: 마지막으로 확정된 위치 (역행 방지의 기준점)
    - forward_window: 현재 위치로부터 몇 문장 앞까지 탐색할지
    - min_score: 이 점수 미만이면 "매칭 실패"로 간주하고 위치를 유지
    """

    def __init__(self, sentences, forward_window: int = 4, min_score: float = 45.0):
        self.sentences = sentences
        self.forward_window = forward_window
        self.min_score = min_score
        self.current_idx = 0  # 0-based, 아직 시작 전이면 0

    def update(self, stt_chunk_text: str):
        """
        새로 인식된 텍스트 조각(stt_chunk_text)을 받아
        (추정 문장 인덱스, 매칭 점수, 매칭 성공 여부)를 반환한다.
        """
        if not stt_chunk_text.strip():
            return self.current_idx, 0.0, False

        best_idx = self.current_idx
        best_score = -1.0

        lo = self.current_idx
        hi = min(len(self.sentences), self.current_idx + self.forward_window + 1)

        for idx in range(lo, hi):
            score = _similarity(stt_chunk_text, self.sentences[idx])
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_score >= self.min_score:
            # 역행 방지: 현재 위치보다 앞으로만 이동
            self.current_idx = max(self.current_idx, best_idx)
            return self.current_idx, best_score, True
        else:
            # 매칭 실패 -> 이전 위치 유지 (fallback)
            return self.current_idx, best_score, False

    def current_sentence(self):
        if 0 <= self.current_idx < len(self.sentences):
            return self.sentences[self.current_idx]
        return ""
