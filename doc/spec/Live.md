# Live Production Planner (LPP)
### vMix 연동 시사교양 라이브 방송 기획 · 소재 자동생성 플랫폼 기획서

| 항목 | 내용 |
|---|---|
| 문서명 | Live.md — LPP 제품 기획서 (PRD) |
| 버전 | v0.1 (Draft) |
| 대상 프로그램 | 시사교양 스튜디오 생방송 |
| 연동 대상 | vMix (HD / 4K / Pro / Max), API HTTP:8088 · TCP:8099 |
| 작성 목적 | 방송 구성(러다운)을 설계하면 vMix 진행 소재(프리셋·타이틀·데이터소스·큐시트·자동화 명령)를 자동 생성하는 제작 도구 |

---

## 1. 개요

### 1.1 한 줄 정의
**"방송 구성을 짜면, vMix에서 바로 진행할 수 있는 모든 소재가 자동으로 만들어지는 프로그램."**

제작진(PD·작가·CG)은 프로그램의 진행 흐름(타이틀 → 카메라 → 자막 → 서버영상 → PIP → 영상 → 끝타이틀)을 카드 단위로 설계한다. LPP는 이 구성을 해석하여, 오퍼레이터(TD)가 vMix에서 곧바로 방송을 진행할 수 있도록 **입력(Input) 프리셋, 자막·타이틀 템플릿, 데이터소스, 오디오 라우팅, 큐시트, 실시간 제어 명령**을 자동으로 생성한다.

### 1.2 왜 필요한가
현재 시사교양 생방송 제작에서 반복적으로 발생하는 비효율:

- 매 회차마다 vMix 프리셋을 손으로 재구성하고, 자막(상단·이름)을 GT Title에 일일이 입력한다.
- 출연자·소속·직함이 바뀔 때마다 이름자막을 수동으로 다시 만든다.
- PIP 소스(PPT·PC·영상·라이브)를 미리 세팅하지 않아 진행 중 전환이 매끄럽지 못하다.
- 전화·화상 인터뷰의 오디오(믹스마이너스, 버스 배정)를 매번 새로 설정하다 실수가 난다.
- 원고와 큐시트가 vMix 조작과 분리돼 있어, 오퍼레이터가 "지금 무엇을 눌러야 하는지"를 종이 큐시트로 판단한다.

LPP는 이 과정을 **구성 설계 → 소재 자동생성 → 원큐 진행**의 파이프라인으로 통합한다.

---

## 2. 표준 방송 구조 정의

### 2.1 시사교양 진행 문법 (기본 러다운)

사용자가 정의한 표준 진행 순서를 LPP의 기본 템플릿으로 채택한다.

```
[1] 오프닝 타이틀
[2] 카메라 (진행자 인사)
[3] 자막 표출  ── 상단자막(코너/주제 띠) + 이름자막(진행자·출연자)
[4] 서버영상 (VOD/리포트, 자체 오디오 사용)
[5] 카메라 (스튜디오 복귀)
[6] 카메라 + PIP (PPT / PC / 영상 / 라이브 소스, 진행 중 소스 전환)
[7] 영상 (기타 소재)
[8] 카메라 (마무리)
[9] 끝타이틀 (엔딩/크레딧)
```

- 이 순서는 **고정이 아니라 기본형(preset grammar)** 이며, 카드 단위로 자유롭게 추가·삭제·재배열한다.
- 전화 인터뷰·화상 인터뷰 세그먼트는 어느 위치에나 삽입 가능하다.

### 2.2 세그먼트 → vMix 매핑

각 진행 요소가 vMix에서 어떤 Input / Overlay / Bus 조작으로 실현되는지 정의한다. 이 매핑 규칙이 자동생성 엔진의 핵심 로직이다.

| 진행 요소 | vMix Input 유형 | 전환 방식 | Overlay | 오디오 처리 |
|---|---|---|---|---|
| 오프닝/끝타이틀 | Title(GT) 또는 Video(애니메이션) | Fade / Stinger | PGM 직접 | 배경음 M 버스 |
| 카메라 | Camera / NDI | Cut | — | 마이크 버스 유지 |
| 상단자막 | Title(GT), 데이터소스 바인딩 | — | **Overlay 1** (상시성) | 없음 |
| 이름자막 | Title(GT), 데이터소스 바인딩 | — | **Overlay 2** (화자별) | 없음 |
| 서버영상 | Video / List (미디어) | Cut / Fade | PGM 직접 | 영상 오디오 M 인가 |
| 카메라 PIP | MultiView Input(카메라 + PIP 레이어) | Cut | 레이어 소스 스왑 | 소스 오디오 선택 인가 |
| 기타 영상 소재 | Video / Image / Web | Cut / Fade | PGM 직접 | 필요 시 오디오 인가 |
| 전화 인터뷰 | vMix Call(영상 None) 또는 Audio 입력 | — (오디오만) | 카메라 위 이름자막 | Mix-Minus 버스 A |
| 화상 인터뷰 | vMix Call(영상+오디오) 또는 Zoom | Cut / PIP | 카메라 PIP 또는 전체화면 | Mix-Minus 버스 A/B |

---

## 3. 시스템 아키텍처

### 3.1 전체 구성도

```
┌─────────────────────────────────────────────────────────────────┐
│                        LPP (Live Production Planner)              │
│                                                                   │
│  ┌────────────┐   ┌──────────────┐   ┌─────────────────────────┐ │
│  │  Frontend  │   │   Backend    │   │   Generation Engine     │ │
│  │  (React)   │◄─►│ (Node/Express)│◄─►│  · Preset Builder       │ │
│  │            │   │  SQLite(WAL) │   │  · Title Template Maker │ │
│  │ 러다운 에디터│   │  JWT Auth    │   │  · Data Source Writer   │ │
│  │ 자막 관리   │   │  5-Role RBAC │   │  · Cue→Command Compiler │ │
│  │ 진행 콘솔   │   └──────┬───────┘   └───────────┬─────────────┘ │
│  └────────────┘          │                       │               │
└──────────────────────────┼───────────────────────┼───────────────┘
                           │                       │
              ┌────────────▼──────────┐  ┌──────────▼──────────────┐
              │  산출물 (Artifacts)    │  │   Live Control Layer     │
              │  · show.vmix (프리셋)  │  │   node-vmix              │
              │  · titles/*.gtzip      │  │   TCP:8099 (제어·TALLY)  │
              │  · datasources/*.csv   │  │   HTTP:8088 (SetText 등) │
              │  · rundown.json (큐시트)│ └──────────┬──────────────┘
              └────────────┬──────────┘             │
                           │                        ▼
                           ▼               ┌──────────────────┐
                  ┌──────────────┐         │   vMix (스튜디오)  │
                  │ vMix 로드/감시 │◄───────►│  Inputs/Overlays  │
                  │ (폴더 워치)   │          │  Audio Buses M,A-G │
                  └──────────────┘         └──────────────────┘
```

### 3.2 기술 스택

| 계층 | 기술 | 비고 |
|---|---|---|
| 프론트엔드 | React + TypeScript, 드래그앤드롭(dnd-kit) | 러다운 카드 UI, 진행 콘솔 |
| 백엔드 | Node.js + Express | 기존 NBS 스택과 정합 |
| DB | SQLite (better-sqlite3, WAL 모드) | 프로그램/회차/러다운/자막 저장 |
| 인증 | JWT, 5단계 역할(RBAC) | 관리자·PD·작가·CG·오퍼레이터 |
| vMix 연동 | node-vmix (TCP 8099 + HTTP 8088) | 실시간 제어·XML 상태·TALLY 수신 |
| 자막 콘텐츠 배포 | 파일 감시 폴더(CSV/XML/JSON) | vMix Data Sources가 자동 갱신 |
| 배포 모드 | LOCAL / REMOTE (환경변수 스위치) | 기존 NBS 이중 모드 규약 준용 |

> vMix TCP API는 HTTP와 동일 기능을 저오버헤드로 제공하며 TALLY 이벤트 구독이 가능하다. 실시간 상태(현재 PGM/PRV/Overlay)는 TCP `XML`·`TALLY` 구독으로 수신하고, 텍스트 변경 등 단발 명령은 HTTP `SetText`로 처리하는 하이브리드 방식을 채택한다.

### 3.3 사용자 역할 (RBAC 5단계)

| 레벨 | 역할 | 권한 |
|---|---|---|
| L5 | 관리자(Admin) | 시스템 설정, vMix 연결정보, 사용자 관리 |
| L4 | 연출(PD) | 프로그램·회차 생성, 러다운 확정, 큐시트 승인 |
| L3 | 작가(Writer) | 원고·자막 문안·출연자 정보 작성 |
| L2 | CG/그래픽 | 타이틀·자막 템플릿 디자인, 데이터소스 편집 |
| L1 | 오퍼레이터(TD) | 진행 콘솔 조작, 실시간 큐 진행 |

---

## 4. 핵심 기능 명세

### 4.1 러다운(큐시트) 에디터
- 진행 요소를 **카드**로 표현하고 드래그앤드롭으로 순서 편집.
- 카드 유형: `타이틀`, `카메라`, `상단자막`, `이름자막`, `서버영상`, `PIP`, `영상`, `전화인터뷰`, `화상인터뷰`, `끝타이틀`.
- 각 카드에 속성 지정: 소요시간, 사용 카메라 번호, 자막 문안, 사용 소스, 오디오 상태.
- 표준 시사교양 문법(2.1)을 **원클릭 템플릿**으로 삽입.
- 카드 총합으로 **예상 러닝타임** 자동 계산.

### 4.2 소재 자동생성 엔진 (핵심)

러다운을 입력받아 다음 산출물을 생성한다.

**(a) vMix 프리셋 생성 (`show.vmix`)**
- 러다운에 등장하는 모든 입력을 스캔하여 Input 카탈로그 구성(카메라 N대, 서버영상, 타이틀, PIP 컨테이너, vMix Call 슬롯 등).
- 두 가지 생성 전략을 지원:
  - **템플릿 채움**: 스튜디오 기본 프리셋(base.vmix)을 템플릿으로 두고 회차별 항목만 치환.
  - **API 빌드**: vMix에 `AddInput` 명령을 순차 전송해 실시간으로 프로덕션을 구성.

**(b) 타이틀/자막 템플릿 생성**
- GT Title 템플릿을 진행 요소별로 생성: `오프닝`, `끝타이틀`, `상단자막`, `이름자막`.
- 각 텍스트 레이어명을 데이터소스 키와 일치시켜(예: 레이어 `Name` ↔ 컬럼 `Name`) **자동 매핑(Column=Auto)** 되도록 설계.

**(c) 데이터소스 파일 생성**
- 자막 실제 문안을 담는 표를 CSV/XML/JSON으로 생성하여 감시 폴더에 배치.
- vMix Data Sources는 CSV·Excel·XML·JSON·Google Sheets·RSS·Text를 지원하며, 파일이 바뀌면 **연결된 타이틀이 자동 갱신**된다 → 자막 문안 수정이 실시간 반영.

**(d) 큐시트 → 명령 컴파일 (`rundown.json`)**
- 각 카드를 실행 가능한 vMix 명령 시퀀스로 변환(부록 C 참조).
- 오퍼레이터가 **"다음 큐"** 버튼 하나로 카드를 순차 실행하도록 구성.

**(e) AI 보조 초안 (선택)**
- 원고 텍스트로부터 상단자막 문구 후보 자동 추천.
- 출연자 정보(이름/소속/직함)로부터 이름자막 데이터 행 자동 생성.
- 대본을 러다운 카드 골격으로 초벌 변환.

### 4.3 자막 시스템 (상단자막 · 이름자막)
- **상단자막**: 코너·주제 띠. Overlay 1 상시 표출, 데이터소스 행 선택으로 문안 교체.
- **이름자막**: 화자별 lower-third. Overlay 2, 화자 전환 시 데이터 행 선택 + Overlay On/Off.
- 데이터소스 행 제어: `DataSourceNextRow` / `DataSourcePreviousRow` / `DataSourceSelectRow`, Auto-Next·Loop 지원.
- 문안 즉시 수정: HTTP `SetText`(Input·SelectedName·Value)로 특정 타이틀 필드를 실시간 갱신.

### 4.4 카메라 PIP 관리 (동적 소스 전환)
- **PIP 슬롯** 개념: 카메라 위에 얹히는 소형 화면 레이어. 후보 소스 리스트를 미리 등록(PPT / PC(NDI·캡처) / 영상 / 라이브(NDI)).
- 진행 중 **소스 스왑**: 진행 콘솔에서 후보를 선택하면 PIP 레이어 입력을 교체하는 명령을 전송.
- 구현: MultiView 입력의 오버레이 레이어 입력을 바꾸거나, Overlay 3/4 채널의 할당 입력을 교체.
- 레이아웃 프리셋: 전체화면 / 우하단 PIP / 사이드 분할 등 배치 저장.

### 4.5 서버·라이브 영상 및 오디오
- 서버영상(VOD)·라이브 소스는 각기 독립 오디오를 보유.
- 영상 전환 시 해당 입력 오디오를 M(Master)에 인가/차단하는 명령을 큐에 포함.
- 라이브 소스 오디오는 지연·레벨을 고려해 별도 버스 배정 옵션 제공.

### 4.6 마이크 · 오디오 라우팅
- 마이크 **1~3개**를 독립 오디오 입력으로 등록하며, **영상 전환과 무관하게 상시 유지**(독립 이동).
- 오디오 아키텍처: Master(M) + 7개 버스(A~G) + Headphones 활용.
- 자동 라우팅 규칙:
  - 마이크 1~3 → M(방송 송출)에 상시 인가.
  - 서버·라이브 영상 오디오 → 전환 시 M에 인가/차단.
  - 인터뷰 리턴 피드 → 버스 A/B로 믹스마이너스 구성.
- 각 입력의 `audiobusses` 상태를 XML로 읽어 콘솔에 시각화.

### 4.7 전화 인터뷰 · 화상 인터뷰
- **화상 인터뷰**: vMix Call 사용. 게스트 수용은 에디션에 따라 HD 1명 / 4K 4명 / Pro 8명. 게스트는 브라우저+웹캠만으로 접속.
- **전화 인터뷰**: vMix Call을 **영상 None + 오디오만**으로 구성하거나 별도 Audio 입력으로 처리, 화면은 카메라 + 이름자막.
- **믹스마이너스**: vMix Call은 Auto Mix Minus를 내장해 게스트가 자기 목소리를 되듣지 않는다. 리턴 오디오는 Master / Headphones / Bus A~G 중 선택.
- LPP는 인터뷰 카드 생성 시 **리턴 비디오 출력·리턴 오디오 버스·믹스마이너스**를 자동 프리셋으로 채운다.
- "가상 대기실(green room)" 옵션: 대기 게스트를 버스 A에서 대화시키고 온에어 직전 M 인가.

### 4.8 PowerPoint 실시간 연동
- vMix PowerPoint 입력으로 슬라이드를 로드하고 API로 슬라이드 전·후 이동.
- PPT 원본 파일을 감시하여 **진행 중 내용 수정이 반영**되도록 구성.
- PIP 슬롯의 후보 소스로 PPT를 등록해 카메라 위 소형 화면으로도 표출.

### 4.9 실시간 제어 (진행 콘솔)
- 큐시트를 실행 리스트로 렌더링하고 **다음 큐 / 이전 큐 / 특정 큐 점프** 제공.
- 현재 PGM·PRV·Overlay 상태를 TALLY 구독으로 실시간 표시.
- 원터치 액션: `자막 ON/OFF`, `PIP 소스 전환`, `인터뷰 온에어`, `서버영상 재생`.
- 비상 처리: 즉시 카메라 복귀(패닉 컷), 전 Overlay 오프.

---

## 5. vMix 기술 매핑 상세

### 5.1 Input 유형 매핑
| 진행 요소 | vMix Input 유형 |
|---|---|
| 카메라 | Camera / NDI / Capture |
| 서버영상·기타영상 | Video / List / Photos |
| 타이틀·자막 | Title (GT Designer, `.gtzip`) |
| PIP 컨테이너 | MultiView / Virtual Set |
| PC·발표자료 | NDI / Screen Capture / PowerPoint |
| 화상 인터뷰 | vMix Call / Zoom |
| 전화 인터뷰 | vMix Call(영상 None) / Audio |

### 5.2 Overlay 채널 배치(권장)
| 채널 | 용도 |
|---|---|
| Overlay 1 | 상단자막(주제 띠) — 상시성 |
| Overlay 2 | 이름자막(화자 lower-third) |
| Overlay 3 | PIP-A (PPT/PC 등 주 보조화면) |
| Overlay 4 | PIP-B (영상/라이브 등 보조) |

### 5.3 오디오 버스 설계
| 버스 | 역할 |
|---|---|
| M (Master) | 방송 송출 오디오 (마이크 1~3 상시 + 전환 영상 오디오) |
| A | 인터뷰 리턴/믹스마이너스, 가상 대기실 |
| B | 보조 인터뷰/통역 등 |
| C~G | 예비(다국어·모니터·레코딩 분리 등) |
| Headphones | 오퍼레이터 모니터 |

### 5.4 GT Title ↔ Data Source 매핑 규칙
- Title Editor에서 필드 선택 후 Data Source 지정(Table·Column).
- **레이어명 = 컬럼명** 규칙을 강제하여 Column=Auto 자동 매핑 성립.
- Format 옵션으로 접두·접미 결합 가능(예: `직함: {0}`).
- 행 선택 시 해당 데이터소스를 참조하는 모든 타이틀이 동시 갱신.

### 5.5 주요 API / Shortcut 함수
| 목적 | 함수 |
|---|---|
| PGM 전환 | `Cut`, `CutDirect`, `Fade`, `Transition1~4` |
| 오버레이 제어 | `OverlayInput1~4`, `OverlayInput1In/Out` |
| 자막 텍스트 변경 | `SetText`, `SetTextColour` |
| 데이터소스 행 | `DataSourceNextRow`, `DataSourcePreviousRow`, `DataSourceSelectRow` |
| 입력 추가 | `AddInput` |
| 오디오 | `AudioBus`, `SetVolume`, `AudioOn/Off`, `SoloOn/Off` |
| 상태 수신 | TCP `XML`, `TALLY`, `SUBSCRIBE ACTS` |

---

## 6. 데이터 모델 (요약 스키마)

```
Program(id, name, genre, created_by)
Episode(id, program_id, air_date, running_time, status)
Rundown(id, episode_id, order_index, card_type, title,
        duration_sec, camera_no, source_ref, audio_state, notes)
TitleTemplate(id, type, gt_file, layer_map_json)   -- 상단/이름/오프닝/끝
DataRow(id, datasource_id, columns_json)           -- 자막 문안 행
DataSource(id, episode_id, kind, file_path)        -- csv/xml/json
PipSource(id, episode_id, label, input_type, input_ref)
Interview(id, episode_id, mode, return_video, return_bus, mix_minus)
CueCommand(id, rundown_id, seq, function, params_json)
VmixTarget(id, host, http_port=8088, tcp_port=8099, edition)
User(id, name, role_level)                         -- L1~L5
```

---

## 7. 자동 생성 산출물 (Artifacts)

| 산출물 | 형식 | 용도 |
|---|---|---|
| `show.vmix` | XML 프리셋 | vMix에 로드하는 회차 프로덕션 |
| `titles/opening.gtzip` 외 | GT Title | 타이틀·자막 그래픽 템플릿 |
| `datasources/subtitle.csv` | CSV/XML/JSON | 상단·이름자막 문안 표(실시간 편집) |
| `rundown.json` | JSON | 큐시트 + 카드별 vMix 명령 시퀀스 |
| `audio_plan.md` | 문서 | 마이크·버스·믹스마이너스 라우팅 표 |
| `setup_checklist.md` | 문서 | 카메라 입력·NDI·인터뷰 세팅 체크리스트 |

---

## 8. 화면 구성 (UI)

1. **러다운 에디터** — 카드 드래그앤드롭, 속성 패널, 러닝타임 합산.
2. **자막 매니저** — 상단/이름자막 표(데이터소스), 행 추가·편집, 미리보기.
3. **소스 보드** — 카메라·서버영상·PIP 후보·인터뷰 슬롯 등록.
4. **오디오 보드** — 마이크 1~3, 버스 M/A~G 매트릭스, 믹스마이너스 표시.
5. **생성 대시보드** — "소재 생성" 실행, 산출물 목록·다운로드·vMix 전송.
6. **진행 콘솔** — 큐 리스트, TALLY, 다음 큐/PIP 전환/인터뷰 온에어 버튼, 패닉 컷.

---

## 9. 대표 워크플로우

```
[기획]  PD/작가가 러다운 카드 구성 + 원고/자막 문안 입력
   │
[생성]  '소재 생성' 실행 → show.vmix · titles · datasources · rundown.json 산출
   │
[적재]  vMix에 프리셋 로드, 데이터소스 폴더 연결, 타이틀 매핑 자동 확인
   │
[리허설] 진행 콘솔로 큐 순차 점검, PIP 소스·인터뷰 오디오 테스트
   │
[생방송] '다음 큐'로 진행, 자막 문안 실시간 수정(SetText), PIP 스왑, 인터뷰 온에어
   │
[종료]  끝타이틀 → 로그·큐 실행기록 저장(회차 아카이브)
```

---

## 10. 개발 로드맵

| 단계 | 범위 |
|---|---|
| **Phase 1** — 코어 | 러다운 에디터, 데이터모델, JWT/RBAC, 프리셋 템플릿 채움, CSV 데이터소스 생성 |
| **Phase 2** — 자막·API | GT Title 매핑, `SetText`/데이터소스 행 제어, TCP TALLY 진행 콘솔 |
| **Phase 3** — PIP·인터뷰 | PIP 슬롯 동적 스왑, vMix Call/전화·화상 인터뷰 프리셋, 믹스마이너스 자동화 |
| **Phase 4** — 자동화·AI | 큐→명령 컴파일러 완성, PPT 실시간 연동, AI 자막/러다운 초안 |
| **Phase 5** — 운영 | 회차 아카이브, 프로그램 템플릿 라이브러리, 다국어·통역 버스 |

---

## 11. 리스크 및 고려사항

- **에디션 종속성**: vMix Call 게스트 수·다중 출력은 4K/Pro/Max에서만 확장 → 대상 에디션 사전 확정 필요.
- **프리셋 스키마 변동**: `.vmix` 내부 구조는 버전별 차이가 있어, **API 빌드(AddInput) 방식**을 기본으로 두고 템플릿 채움을 보조로 운용 권장.
- **네트워크·방화벽**: TCP:8099 / HTTP:8088 접근, vMix Call P2P 연결 조건 확인.
- **실시간 안정성**: 명령 실패 시 재시도·상태 재동기화(XML 재조회) 로직 필수, 패닉 컷 상시 확보.
- **데이터소스 갱신 타이밍**: 파일 저장 후 vMix 반영까지의 지연을 고려해 사전 갱신·확인 절차 마련.

---

## 부록 A. vMix API 명령 예시

```http
# 자막 텍스트 변경 (이름자막)
GET /api/?Function=SetText&Input=lower_third.gtzip&SelectedName=Name.Text&Value=홍길동

# 이름자막 오버레이 ON (Overlay 2)
GET /api/?Function=OverlayInput2In&Input=lower_third.gtzip

# 데이터소스 다음 행 (화자 전환)
GET /api/?Function=DataSourceNextRow&Value=Speakers

# 카메라 컷
GET /api/?Function=CutDirect&Input=1

# 서버영상 오디오 M 인가
GET /api/?Function=AudioBusOn&Input=Server_VOD&Value=M
```

```javascript
// node-vmix (TCP) 실시간 제어 예시
const { ConnectionTCP } = require('node-vmix');
const vmix = new ConnectionTCP('192.0.2.13'); // :8099
vmix.on('connect', () => { vmix.send('SUBSCRIBE TALLY'); });
vmix.on('tally', t => updateConsole(t));
function nextCue(cmd) { vmix.send({ Function: cmd.function, ...cmd.params }); }
```

## 부록 B. 데이터소스 스키마 예시 (`subtitle.csv`)

```csv
Type,Topic,Name,Title,Org
상단,오늘의 이슈: 물가와 금리,,,
이름,,홍길동,경제부 기자,본사
이름,,김철수,교수,○○대학교
이름,,박영희,전화연결,시민단체
```

- `이름` 레이어 ↔ `Name` 컬럼, `직함` 레이어 ↔ `Title` 컬럼으로 Auto 매핑.
- 행 선택(`DataSourceSelectRow`)만으로 자막 전체가 교체됨.

## 부록 C. 큐시트 → vMix 명령 변환 예시 (`rundown.json`)

```json
[
  { "cue": 1, "card": "오프닝타이틀",
    "commands": [ {"function":"Fade","params":{"Input":"opening.gtzip"}} ] },
  { "cue": 2, "card": "카메라",
    "commands": [ {"function":"CutDirect","params":{"Input":"1"}} ] },
  { "cue": 3, "card": "이름자막",
    "commands": [
      {"function":"DataSourceSelectRow","params":{"Value":"Speakers","Row":"1"}},
      {"function":"OverlayInput2In","params":{"Input":"lower_third.gtzip"}} ] },
  { "cue": 4, "card": "서버영상",
    "commands": [
      {"function":"CutDirect","params":{"Input":"Server_VOD"}},
      {"function":"AudioBusOn","params":{"Input":"Server_VOD","Value":"M"}} ] },
  { "cue": 6, "card": "PIP",
    "commands": [
      {"function":"CutDirect","params":{"Input":"Cam1_PIP"}},
      {"function":"SetMultiViewOverlay","params":{"Input":"Cam1_PIP","Value":"1,PPT"}} ] },
  { "cue": 9, "card": "끝타이틀",
    "commands": [ {"function":"Fade","params":{"Input":"ending.gtzip"}} ] }
]
```

---

*본 문서는 초안(Draft)이며, 대상 vMix 에디션·스튜디오 입력 구성·인터뷰 방식이 확정되면 프리셋 생성 전략(템플릿 채움 vs API 빌드)과 오디오 버스 배치를 세부 조정한다.*
