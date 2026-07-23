# -*- coding: utf-8 -*-
"""
main.py
-------
사용법:

  1) 녹음된 wav 파일로 테스트 (실제 방송 전 검증용)
     python main.py --article sample_article.txt --wav sample_audio.wav

  2) 마이크로 실시간 테스트
     python main.py --article sample_article.txt --mic

  wav 파일은 16kHz mono여야 합니다. 다른 포맷이면 먼저 변환하세요:
     ffmpeg -i input.mp3 -ar 16000 -ac 1 sample_audio.wav

지연 보정(--delay-comp): 실측한 평균 지연(초)만큼 하이라이트 표시를
"미리" 당겨서 보여주고 싶을 때 사용. 예: 인식 파이프라인이 평균 1.2초
늦게 반응한다면 --delay-comp 1.2로 설정 (표시 로직에서 참고용으로만 출력,
실제 화면 표시 시스템과 연동 시 이 값만큼 타임스탬프를 보정해서 쏘면 됨).
"""

import argparse
import time

from matcher import split_sentences, ArticleMatcher
from stt_stream import WhisperStreamer


def main():
    parser = argparse.ArgumentParser(description="오디오 인식 기반 기사 하이라이트 프로토타입 (Whisper)")
    parser.add_argument("--article", required=True, help="기사 원문 텍스트 파일 경로")
    parser.add_argument("--wav", help="테스트용 wav 파일 경로 (16kHz mono)")
    parser.add_argument("--mic", action="store_true", help="마이크로 실시간 테스트")
    parser.add_argument("--model", default="small", help="whisper 모델 크기 (tiny/base/small/medium)")
    parser.add_argument("--device", default="cpu", help="cpu 또는 cuda")
    parser.add_argument("--compute-type", default="int8", help="int8(cpu 권장) / float16(gpu 권장)")
    parser.add_argument("--forward-window", type=int, default=4,
                         help="현재 위치 기준 몇 문장 앞까지 탐색할지")
    parser.add_argument("--min-score", type=float, default=45.0,
                         help="이 유사도(0~100) 미만이면 매칭 실패로 간주")
    parser.add_argument("--delay-comp", type=float, default=0.0,
                         help="평균 지연 보정값(초, 참고용 출력에 반영)")
    args = parser.parse_args()

    with open(args.article, encoding="utf-8") as f:
        article_text = f.read()
    sentences = split_sentences(article_text)
    print(f"[기사] 총 {len(sentences)}개 문장으로 분절됨\n")

    matcher = ArticleMatcher(sentences, forward_window=args.forward_window,
                              min_score=args.min_score)
    streamer = WhisperStreamer(model_size=args.model, device=args.device,
                                compute_type=args.compute_type)

    def on_text(chunk_text, chunk_start_sec):
        recv_time = time.time()
        idx, score, matched = matcher.update(chunk_text)
        display_time = recv_time - args.delay_comp  # 보정 참고용

        status = "OK " if matched else "유지"
        ts = f"{chunk_start_sec:6.1f}s" if chunk_start_sec is not None else "  live "
        print(f"[{ts}] 인식: \"{chunk_text}\"")
        print(f"        -> [{status}] 문장 #{idx+1}/{len(sentences)} (유사도 {score:.0f}) "
              f"| 보정후 표시시각(epoch) {display_time:.2f}")
        print(f"        하이라이트: {matcher.current_sentence()}\n")

    if args.wav:
        streamer.stream_from_wav(args.wav, on_text, realtime=True)
    elif args.mic:
        streamer.stream_from_mic(on_text)
    else:
        parser.error("--wav 또는 --mic 중 하나를 지정하세요")


if __name__ == "__main__":
    main()
