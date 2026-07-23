# -*- coding: utf-8 -*-
"""
stt_stream.py
-------------
faster-whisper(경량 Whisper, CPU에서도 실시간 가능)로 오디오를
청크 단위로 잘라 순차적으로 인식하고, 인식된 텍스트 조각을
콜백으로 전달하는 모듈.

두 가지 입력 소스를 지원:
  1) 마이크 실시간 입력 (sounddevice 필요)
  2) 이미 녹음된 wav 파일 (테스트/검증용, 실시간처럼 재생 속도에 맞춰 흘려보냄)

모델은 최초 실행 시 인터넷에서 한 번 다운로드되며(HuggingFace Hub),
이후에는 로컬 캐시(~/.cache/huggingface)에서 로드된다.
"""

import time
import queue
import numpy as np

from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
CHUNK_SECONDS = 3.0          # 몇 초 단위로 잘라서 인식할지
CHUNK_OVERLAP_SECONDS = 0.5  # 문맥 유지를 위한 청크 간 겹침


class WhisperStreamer:
    def __init__(self, model_size: str = "small", device: str = "cpu",
                 compute_type: str = "int8", language: str = "ko"):
        """
        model_size: tiny / base / small / medium / large-v3
                    - 위치 추정 목적이면 base~small 권장 (속도-정확도 균형)
        device: "cpu" 또는 "cuda" (GPU 있으면 cuda 권장, 없어도 small까지는 CPU로 실시간 가능)
        compute_type: "int8"(CPU 권장, 가장 빠름) / "int8_float16" / "float16"(GPU)
        """
        print(f"[STT] 모델 로딩 중... (model={model_size}, device={device}, compute_type={compute_type})")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.language = language
        print("[STT] 모델 로딩 완료")

    def _transcribe_chunk(self, audio_chunk: np.ndarray) -> str:
        """오디오 청크(float32, 16kHz, mono)를 텍스트로 변환."""
        segments, _info = self.model.transcribe(
            audio_chunk,
            language=self.language,
            beam_size=1,          # 실시간성을 위해 beam search 최소화
            vad_filter=True,      # 무음 구간 제거
            condition_on_previous_text=False,
        )
        text = "".join(seg.text for seg in segments)
        return text.strip()

    # ---------- 1) 파일 기반 테스트 모드 ----------
    def stream_from_wav(self, wav_path: str, on_text, realtime: bool = True):
        """
        wav_path의 오디오를 CHUNK_SECONDS 단위로 잘라 순차적으로 인식하고,
        인식될 때마다 on_text(chunk_text, chunk_start_sec)를 호출한다.

        realtime=True면 실제 낭독 속도와 비슷하게 sleep을 넣어
        운영 환경의 스트리밍을 흉내낸다 (검증용).
        """
        import soundfile as sf

        audio, sr = sf.read(wav_path, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)  # 스테레오 -> 모노
        if sr != SAMPLE_RATE:
            raise ValueError(
                f"샘플레이트가 {sr}Hz입니다. 사전에 {SAMPLE_RATE}Hz로 변환한 파일을 사용하세요 "
                f"(예: ffmpeg -i input.wav -ar 16000 -ac 1 output.wav)"
            )

        chunk_len = int(CHUNK_SECONDS * SAMPLE_RATE)
        step_len = int((CHUNK_SECONDS - CHUNK_OVERLAP_SECONDS) * SAMPLE_RATE)

        pos = 0
        while pos < len(audio):
            chunk = audio[pos: pos + chunk_len]
            if len(chunk) < SAMPLE_RATE * 0.3:  # 너무 짧은 마지막 조각은 스킵
                break

            t0 = time.time()
            text = self._transcribe_chunk(chunk)
            elapsed = time.time() - t0

            if text:
                on_text(text, pos / SAMPLE_RATE)

            if realtime:
                # 실제 청크 길이만큼 시간이 흘렀다고 가정하고,
                # 처리 시간(elapsed)을 뺀 나머지만큼 대기 -> 실사용 지연 체감 확인용
                wait = max(0.0, step_len / SAMPLE_RATE - elapsed)
                time.sleep(wait)

            pos += step_len

    # ---------- 2) 실시간 마이크 모드 ----------
    def stream_from_mic(self, on_text, device=None):
        """
        마이크 입력을 실시간으로 받아 CHUNK_SECONDS 단위로 인식한다.
        Ctrl+C로 종료.
        """
        import sounddevice as sd

        q = queue.Queue()

        def _callback(indata, frames, time_info, status):
            if status:
                print(f"[STT][경고] {status}")
            q.put(indata.copy())

        chunk_len = int(CHUNK_SECONDS * SAMPLE_RATE)
        step_len = int((CHUNK_SECONDS - CHUNK_OVERLAP_SECONDS) * SAMPLE_RATE)
        buffer = np.zeros((0,), dtype=np.float32)

        print("[STT] 마이크 입력 시작 (Ctrl+C로 종료)")
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                             callback=_callback, device=device):
            try:
                while True:
                    data = q.get()
                    buffer = np.concatenate([buffer, data.flatten()])

                    while len(buffer) >= chunk_len:
                        chunk = buffer[:chunk_len]
                        text = self._transcribe_chunk(chunk)
                        if text:
                            on_text(text, None)
                        buffer = buffer[step_len:]
            except KeyboardInterrupt:
                print("\n[STT] 종료합니다.")
