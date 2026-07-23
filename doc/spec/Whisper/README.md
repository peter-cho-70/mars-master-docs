# 오디오 기사 하이라이트 프로토타입 (Whisper 기반)

큐시트 기사 원문 텍스트와, 진행자가 낭독하는 오디오를 Whisper(경량 모델)로
실시간 인식한 결과를 비교해서 "지금 어느 문장을 읽고 있는지" 대략적인
위치를 추정하는 프로토타입입니다.

## 구성 파일

| 파일 | 역할 |
|---|---|
| `matcher.py` | 기사 문장 분절 + STT 텍스트와 유사도 매칭(위치 추정) |
| `stt_stream.py` | faster-whisper로 오디오를 청크 단위로 인식 (wav 파일 / 마이크 모두 지원) |
| `main.py` | 전체 파이프라인 실행 (CLI) |
| `sample_article.txt` | 테스트용 예시 기사 |
| `requirements.txt` | 필요 패키지 |

## 설치

```bash
pip install -r requirements.txt
```

- CPU만으로 `small` 모델까지는 실시간 처리 가능합니다 (본문 PRD 7-3 참고).
- 최초 실행 시 Whisper 모델 가중치가 HuggingFace에서 자동 다운로드됩니다
  (`small` 모델 기준 약 500MB). 이후에는 로컬 캐시에서 바로 로드됩니다.
- **주의**: 이 환경(Claude 샌드박스)은 외부 네트워크가 제한되어 있어
  모델 다운로드/마이크 접근이 불가능합니다. 아래 실행은 Peter님의 실제
  PC(인터넷 + 마이크 사용 가능한 환경)에서 진행해 주세요.

## 사용법

### 1) 녹음 파일로 먼저 검증 (권장되는 첫 단계)

실제 방송에 투입하기 전에, 진행자가 기사를 읽는 샘플 오디오를 녹음해서
먼저 정확도/지연을 확인하는 것을 권장합니다.

```bash
# wav가 16kHz mono가 아니면 먼저 변환
ffmpeg -i input.mp3 -ar 16000 -ac 1 sample_audio.wav

python main.py --article sample_article.txt --wav sample_audio.wav
```

`sample_article.txt`를 실제로 사용할 기사 원문으로, `sample_audio.wav`를
그 기사를 낭독한 녹음 파일로 교체해서 테스트하면 됩니다.

### 2) 마이크로 실시간 테스트

```bash
python main.py --article sample_article.txt --mic
```

Ctrl+C로 종료합니다.

### 주요 옵션

| 옵션 | 설명 | 기본값 |
|---|---|---|
| `--model` | whisper 모델 크기 (tiny/base/small/medium) | small |
| `--device` | cpu 또는 cuda | cpu |
| `--compute-type` | int8(cpu 권장) / float16(gpu 권장) | int8 |
| `--forward-window` | 현재 위치 기준 몇 문장 앞까지 탐색할지 | 4 |
| `--min-score` | 이 유사도(0~100) 미만이면 "매칭 실패"로 간주하고 이전 위치 유지 | 45.0 |
| `--delay-comp` | 평균 지연 보정값(초). 실측 후 반영 | 0.0 |

## 다음 단계 (실제 시스템 연동 시)

1. **큐시트 연동**: `--article` 텍스트 파일 대신, 큐시트 시스템에서 현재
   진행 중인 아이템의 기사를 API/DB로 가져오도록 교체
2. **마이크 소스 교체**: `sounddevice` 대신 방송 믹서/오디오 인터페이스의
   출력을 받는 방식으로 교체 (예: 가상 오디오 케이블, ALSA/CoreAudio 라우팅)
3. **화면 표시 연동**: 현재 `print`로만 출력되는 하이라이트 결과를,
   문서 표시 화면(웹소켓/HTTP 등)으로 전송하도록 `on_text` 콜백 안에 추가
4. **지연 실측**: 실제 낭독 시작 시각과 하이라이트 표시 시각의 차이를
   여러 번 측정해 평균값을 구하고, 이를 `--delay-comp`에 반영
5. **정확도 튜닝**: `--min-score`, `--forward-window`를 실제 데이터로
   튜닝. 오탐(엉뚱한 문장으로 튐)이 잦으면 `min-score`를 높이고,
   반대로 위치가 잘 안 넘어가면 낮추는 방향으로 조정

## 모델 선택 참고 (PRD 7-3 요약)

- `tiny`/`base`: 매우 빠르지만 인식 오류 다소 많음. 저사양 PC에서도 충분히 실시간
- `small`: 속도-정확도 균형이 좋아 기본값으로 권장
- `medium` 이상: 정확도는 높지만 CPU만으로는 실시간이 빠듯할 수 있음 (GPU 권장)
