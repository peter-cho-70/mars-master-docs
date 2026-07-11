# 뉴스 방송 시스템 — 전체 아키텍처 설계서

**버전**: 1.1
**작성일**: 2026-06-23 (2026-06-24 MARS/Master 명칭·역할 개편)

---

## 1. 시스템 전체 구성 요약

```
┌─────────────────────────────────────────────────────────┐
│                   백엔드 서버 (Node.js, Phase 2)          │
│  API서버 · DB · 미디어서버 · 인증서버 · WS Sync 서버      │
└───────┬─────────────────────────────┬───────────────────┘
        │ (현재는 JSON 파일로 대체)     │
        ▼                             ▼
┌───────────────────┐    ┌──────────────────────────────┐
│  메인 방송 PC (Mac) │    │  제작 클라이언트 PC 1~4 (브라우저) │
│  OBS + Master 진행앱│ ◀──JSON── │  MARS (기사 작성 + 큐시트 제작) │
└───────────────────┘    └──────────────────────────────┘
```

MARS에서 큐시트를 만들고 Master가 그 큐시트를 불러와 실제 장비를 운영하는 단방향 흐름이다. 지금은 JSON 파일 내보내기/불러오기로 연결되어 있고(아래 6장), 백엔드가 생기면 같은 JSON 포맷을 API로 주고받도록 바꾼다.

---

## 2. 소프트웨어 2종 구분

### MARS — 기사·큐시트 제작 시스템
- **역할**: 기사 작성·검색·출고, 큐시트 편성, 기사/영상 매칭, CG 자막 템플릿, 앵커멘트 편집
- **주 사용자**: 기자, 편집자, 편성장, 영상담당, 자막담당 (PC 1~4)
- **핵심 화면**:
  - 기사 편집: 기사 목록/검색, 2컬럼 에디터 (자막패널 + 앵커/리포트 본문) — `mars-news-editor.html`
  - 큐시트 제작: 큐시트 테이블, 아이템매칭/영상조회/자막조회 탭 — `nps-news-system.html`
- **Master로 큐시트 전달**: 큐시트 제작 화면의 「방송 진행」(▶) 버튼을 누르면 표준 큐시트 JSON을 내보내고 Master를 새 탭으로 연다. 지금은 파일(JSON) 기반이며, 백엔드가 붙으면 같은 JSON 포맷을 그대로 API로 전송하도록 바꿀 수 있다.
- **아이템 편집 모달** (2026-06-24 추가): 큐시트 표의 "형식"(타입) 뱃지나 "영상" 클립 카운터를 클릭(또는 행 더블클릭)하면 아이템 편집 모달이 열린다. 형식(NPS 코드: 타/완/단/출/특/NT), No/아이템명/담당/시간, 카메라 샷, **영상 클립**(파일명 입력 + "찾기"로 실제 파일 선택해 파일명 자동 저장 + "미리보기"로 정지 화면 확인 — Master의 클립 입력 방식과 동일한 패턴)을 한 곳에서 편집한다. 「아이템 추가」/「단신 추가」 토글바 버튼도 이 모달을 새 아이템 추가 모드로 연다. `item.clips`(실제 파일명 배열)가 Master로 내보내는 진짜 클립 데이터이며, 기존 영상조회 탭의 가상 샘플 매칭(`item.videos`)은 더 이상 내보내기에 쓰이지 않는다. 기사/자막 매칭은 다음 단계.
- **Master 큐시트 JSON 가져오기** (2026-06-24 추가): 툴바의 「열기」 버튼으로 Master가 만든(또는 내보낸) 큐시트 JSON을 불러올 수 있다 — `toMasterCuesheet()`의 역변환. Master 타입 키는 TYPE_MAPPING을 거꾸로 찾아 NPS 코드로 변환한다.

### Master — 방송 제어 시스템 (구 NBS)
- **역할**: 큐시트를 불러오거나 직접 만들어 실제 송출 장비를 제어. 지금은 OBS만 연동하지만, 큐시트·진행 로직은 장비에 묶이지 않도록 "디바이스 어댑터" 구조로 두고 향후 vMix·VMU(영상믹서)·AMU(오디오믹서)·송출서버·자막기 어댑터를 추가한다.
- **주 사용자**: PD 1인 전담 (메인 방송 PC)
- **핵심 화면**: 큐시트 진행뷰(편집 가능), 스위처, 탈리, 오디오, CG, 영상 서버 운영 모드 설정, 타입 관리
- **파일**: `news-broadcast-system.html`
- **현재 어댑터**: OBS (obs-websocket) — 씬 전환, 미디어 소스 제어, 텍스트 소스(CG) 갱신, 오디오 볼륨/뮤트
- **향후 어댑터(예정)**: vMix(API), VMU/AMU(컨트롤 프로토콜), 송출서버(스트림/레코드 제어), 자막기(CG 전송 프로토콜) — 동일한 "씬 전환/CG 전송/서버 교번" 인터페이스를 구현하는 형태로 추가
- **큐시트 직접 작성/수정** (2026-06-24 추가): OBS 연동 편의성을 우선해 "Master 먼저 작성, MARS와 JSON으로 상호 호환" 흐름도 지원한다. 큐시트 좌측 툴바의 「+ 아이템 추가」, 각 행의 ✏️ 편집 버튼으로 아이템 추가/수정/삭제/위아래 이동이 가능하고, 「PDF/설정」 탭 상단의 "큐시트 설정"에서 제목/앵커/PD/방송일시를 고친다.
  - 1단계(완료): 아이템 편집 모달에서 타입, No, 아이템명, 담당, 시간, **카메라**(cam1~4 체크박스, 타입 변경 시 기본 카메라로 맞출지 확인), **송출서버/영상 클립**(서버 자동교번은 타입 규칙이 결정하고 수동 타입일 때만 체크 가능 + 클립 파일명 목록 추가/삭제), **자막**(하단자막 1줄 + 제목/이름/코너/긴급자막 CG 목록 추가/삭제), 앵커멘트, 비고를 편집한다.
  - 이후 단계(예정): 기사 매칭, 영상 미리보기/드래그 매칭, 자막 템플릿 불러오기 등 MARS에 있는 고급 매칭 기능을 단계적으로 Master에도 추가.
  - 역방향 가져오기(완료, 2026-06-24): MARS 툴바의 「열기」 버튼(`openCuesheetFile()`)으로 Master가 내보낸 큐시트 JSON을 불러올 수 있다. Master의 타입 키(TITLE/CM/REPORT 등)는 MARS의 TYPE_MAPPING을 거꾸로 찾아 NPS 코드로 변환하고(매핑에 없으면 합리적 기본값), `sources`는 cam1/cam2 조합으로 샷을, `clips`/`cg`/`ancMent`는 그대로 가져온다. `type:"divider"` 아이템은 MARS의 구분선으로 들어온다.
- **자막(CG) 프리셋 자동 송출** (2026-06-24 추가): "타입"은 OBS 동작(씬/카메라/서버교번)만 정의하고, "내용"(기사·자막·앵커멘트·영상)은 뉴스아이템 하나하나가 곧 프리셋이다 — 새 타입을 만들 필요 없이 같은 타입에 다른 내용의 아이템을 추가하면 된다. 그 내용이 실제로 방송에 나가는 방식도 자동화했다(`applyCGPreset(item, rule)`):
  - 아이템이 PGM에 뜨는 시점(또는 영상 있는 리포트/단신은 「영상 전환」 시점)에 그 아이템의 `cg[]` 배열 전체가 자동으로 해당 OBS 텍스트 소스로 전송된다 — 제목자막→CG_LOWER_THIRD, 이름자막→CG_NAME, 긴급자막→CG_BREAKING(그 외 타입은 CG_LOWER_THIRD로 폴백). PD가 CG 탭에서 매번 ON을 누를 필요가 없다.
  - 자동 OFF는 여전히 타입의 `cgAutoOff`(초)가 0보다 클 때만 동작 — 0인 타입(예: ANCHOR/BRIDGE/CLOSING 기본값)은 다음 컷까지 자막이 유지된다.
  - 영상 클립이 없는 리포트/단신(예: 단신처럼 영상 없이 끝나는 아이템)은 「영상 전환」 단계가 오지 않으므로 앵커멘트 단계 시작 시점에 바로 CG가 나간다. 영상이 있으면 기존처럼 영상 전환 시점에 나간다 — 화면 위 자막이 talking-head 위에 먼저 뜨지 않도록.
  - `item.cg`가 비어 있고 `item.subtitle`만 있는 옛 데이터는 제목자막 1건으로 취급해 그대로 자동 송출된다 (하위 호환).

---

## 3. 백엔드 서버 상세

### 기술 스택

| 레이어 | 기술 | 역할 |
|--------|------|------|
| API 서버 | Node.js + Express | REST API, WebSocket 라우팅 |
| 실시간 동기화 | Socket.io | 큐시트 변경사항 전체 클라이언트 브로드캐스트 |
| 데이터베이스 | PostgreSQL | 기사, 큐시트, 자막, 사용자, 영상 메타 |
| 파일 스토리지 | 로컬 NAS or S3 호환 | 영상 클립, CG 이미지 |
| 인증 | JWT (Access + Refresh) | 로그인, 권한 검증 |
| OBS 브리지 | obs-websocket-js | 서버 ↔ OBS ↔ Master 중계 |

### 핵심 API 엔드포인트

```
POST   /auth/login              로그인 → JWT 발급
POST   /auth/refresh            토큰 갱신

GET    /articles                기사 목록 (검색/필터)
POST   /articles                기사 생성
PUT    /articles/:id            기사 수정
POST   /articles/:id/publish    기사 출고

GET    /cuesheets               큐시트 목록
POST   /cuesheets               큐시트 생성
PUT    /cuesheets/:id           큐시트 수정
PUT    /cuesheets/:id/confirm   큐시트 확정

GET    /media                   영상 목록
POST   /media/upload            영상 업로드
PUT    /cuesheet-items/:id/media 영상 매칭

GET    /cg-templates            CG 자막 템플릿
POST   /cg/send                 OBS 자막 전송 (→ OBS 브리지)

WS     /ws/cuesheet/:id         큐시트 실시간 동기화
WS     /ws/obs                  OBS 상태 브로드캐스트
```

### 실시간 동기화 (WebSocket 이벤트)

```javascript
// 서버 → 모든 클라이언트
socket.broadcast('cuesheet:updated',  { itemId, changes })
socket.broadcast('cuesheet:confirmed', { cuesheetId })
socket.broadcast('obs:scene:changed',  { sceneName })
socket.broadcast('obs:media:ended',    { inputName })

// 클라이언트 → 서버 → OBS
socket.emit('obs:cut',  { sceneName })
socket.emit('obs:pvw',  { sceneName })
socket.emit('cg:send',  { sourceName, text })
```

---

## 4. 메인 방송 PC (Mac) 구성

### 하드웨어
```
Mac (Apple Silicon M2 Pro 이상 권장)
├── 모니터 1 (27인치 이상): OBS 멀티뷰
│   └── 8분할: PGM · PVW · CAM1 · CAM2 · CAM3 · CAM4 · SRV1 · SRV2
├── 모니터 2 (24인치): Master 방송 진행 앱 (브라우저 전체화면)
└── (선택) 모니터 3: 큐시트 뷰어 / 서브 모니터링
```

### 연결 장비
```
카메라 4대:  NDI 카메라 or HDMI→USB 캡처카드 (Elgato, AVerMedia)
서버 3대:   OBS Media Source (SERVER1, SERVER2, SERVER3)
마이크 2개: 앵커1 MIC, 앵커2 MIC → USB 오디오 인터페이스
네트워크:   유선 기가비트 필수 (Wi-Fi 금지)
```

### OBS 씬 컬렉션: NEWS_BROADCAST
```
TITLE              타이틀 그래픽
CM_PRE             전 CM
CAM1_ANCHOR        앵커1 단독
CAM1_CAM2_2SHOT    앵커 투샷
CAM3_WIDE          와이드
CAM4_CLOSEUP       클로즈업
SRV1_VCR           서버1 VCR 풀스크린
SRV2_VCR           서버2 VCR 풀스크린
SRV3_VCR           서버3 예비
CAM1_SRV1_PIP      앵커+서버1 PIP (뉴스탑)
CAM1_SRV2_PIP      앵커+서버2 PIP
LIVE_EXT           외부 중계
WEATHER            날씨
LIVE_STOCK         증권 LIVE
CLOSING            클로징
BLACK              블랙 (비상)
```

### OBS 소스 명칭 (필수 준수)
```
CAM1, CAM2, CAM3, CAM4        카메라 Video Capture Device
SERVER1, SERVER2, SERVER3     미디어 소스 (VLC or Media Source)
앵커1_마이크, 앵커2_마이크       오디오 입력 캡처
CG_LOWER_THIRD                하단 자막 텍스트 소스
CG_NAME                       이름 자막 텍스트 소스
CG_BREAKING                   긴급 자막 텍스트 소스
LOGO_OVERLAY                  로고 이미지 소스
```

---

## 5. 제작 클라이언트 권한 체계

### 권한 레벨 (5단계)

| 레벨 | 코드 | 직책 | 주요 권한 |
|------|------|------|---------|
| 5 | ADMIN | 편성장 / PD | 전체 관리, 큐시트 확정, 사용자 관리 |
| 4 | EDITOR | 기자 / 편집자 | 기사 작성·출고, 자막 등록 |
| 3 | MEDIA | 영상 담당 | 영상 업로드·매칭, 미디어 관리 |
| 2 | CG | 자막 / CG 담당 | CG 템플릿 관리, OBS 자막 전송 |
| 1 | MONITOR | 기술 / 보조 | 읽기 전용, 상태 모니터링 |

### 기능별 접근 권한 매트릭스

| 기능 | ADMIN | EDITOR | MEDIA | CG | MONITOR |
|------|:-----:|:------:|:-----:|:--:|:-------:|
| 큐시트 편집 | ✓ | 조회 | 조회 | 조회 | 조회 |
| 큐시트 확정 | ✓ | — | — | — | — |
| 기사 작성 | ✓ | ✓ | — | — | — |
| 기사 출고 | ✓ | ✓ | — | — | — |
| 영상 업로드 | ✓ | — | ✓ | — | — |
| 영상 매칭 | ✓ | — | ✓ | — | — |
| CG 템플릿 관리 | ✓ | ✓ | — | ✓ | — |
| OBS CG 전송 | ✓ | — | — | ✓ | — |
| OBS 씬 전환 | ✓ | — | — | — | — |
| 사용자 관리 | ✓ | — | — | — | — |
| 시스템 로그 | ✓ | — | — | — | ✓ |

### SW별 접근 화면 제한

| SW | ADMIN | EDITOR | MEDIA | CG | MONITOR |
|----|:-----:|:------:|:-----:|:--:|:-------:|
| MARS 기사편집 | ✓ | ✓ | — | — | 조회 |
| MARS 큐시트탭 | ✓ | 조회 | 조회 | 조회 | 조회 |
| MARS 영상매칭탭 | ✓ | — | ✓ | — | — |
| MARS 자막탭 | ✓ | ✓ | — | ✓ | — |
| Master 방송진행 | ✓ | — | — | — | 조회 |

---

## 6. 파일명·데이터 규칙

### 영상 파일명 규칙
```
[프로그램코드]-[기자명]-[순서]-[타입]_[설명].mp4

예:
0600-김태운-1-VCR1_월드컵-메시최다골.mp4
0600-이문현-1-완제-6.3재보궐결과.mp4
0600-기자명-2-동영상D-투데이축구.mp4
0025-정병화-1-완제-뉴스25이란IAE.mp4

프로그램 코드:
0600 = 뉴스투데이(6:00)
0900 = 아침뉴스(9:00)
1200 = MBC12뉴스
2100 = 뉴스데스크(21:00)
0025 = 뉴스25
```

### 클립-큐시트 자동 매칭 규칙
```
아이템번호_기자이름.mp4         단일 클립
아이템번호a_기자이름.mp4        다중 클립 첫 번째
아이템번호b_기자이름.mp4        다중 클립 두 번째

예:
01_이문현.mp4
03a_이재욱.mp4
03b_이재욱.mp4
```

### 큐시트 JSON 구조 (MARS → Master 표준 포맷)
MARS 큐시트 제작 화면의 「방송 진행」(▶) 버튼이 내보내고, Master가 PDF/JSON 드롭 영역이나 파일 열기로 그대로 불러오는 포맷이다. `items[].type`은 Master의 `TYPE_RULES`/`SCENE_MAP` 키와 1:1로 맞아야 한다 (`TITLE`/`CM`/`OPEN`/`ANCHOR`/`BRIDGE`/`REPORT`/`NT`/`LIVE`/`WEATHER`/`STOCK`/`CLOSING`, 구획선은 `divider`로 변환 후 제외).

```json
{
  "title": "뉴스투데이-1,2부",
  "anc": "손령 정슬기",
  "pd": "박철현",
  "date": "2026-06-23",
  "broadcastAt": "06:00:00",
  "duration": "00:58:00",
  "items": [
    {
      "id": 1,
      "no": "1",
      "type": "REPORT",
      "item": "[:]이란, IAEA 사찰 재개 수용",
      "reporter": "허유신",
      "dur": "01:50",
      "sources": ["cam1"],
      "transIn": "Cut",
      "subtitle": "이란, IAEA 사찰 수용..",
      "clips": ["0600-허유신-1-완제.mp4"],
      "cg": [{"type":"제목자막","text":"이란, IAEA 사찰 수용.."},{"type":"이름자막","text":"허유신 기자"}],
      "ancMent": "이란이 IAEA 사찰을 수용했습니다...",
      "note": ""
    }
  ]
}
```

- `sources`: 카메라(`cam1~4`)/서버(`srv1~3`) 중 어떤 게 실제 PGM에 쓰이는지는 Master의 `TYPE_RULES[type]`가 우선 결정한다 (예: REPORT/ANCHOR는 `srvAuto:true`라 영상 서버 운영 모드의 교번 로직(`getAutoSrv`)을 따른다). `sources`는 큐시트 표의 소스 뱃지 표시용.
- `ancMent`: 앵커멘트 — Master 진행 화면의 현재 아이템 패널에 참고용으로 표시되며, 실제 OBS 제어에는 쓰이지 않는다.
- `clips`: 파일명(또는 경로) 배열. Master가 표시할 때는 마지막 `/` 이후 파일명만 보여준다.

### 아이템 타입 레지스트리 (`item-types.json`) — 타입 ↔ OBS 연동 설정
`items[].type`이 실제로 어떤 OBS 씬·카메라·서버교번·전환·자막오프타이밍으로 이어지는지는 큐시트 JSON이 아니라 별도의 "타입 레지스트리"가 결정한다. 두 앱 모두 같은 형식을 쓴다.

```json
{
  "itemTypes": [
    { "key":"REPORT", "label":"리포트", "scene":"SRV{N}_VCR", "cams":["cam1"],
      "srvAuto":true, "sequential":true, "transIn":"Cut", "transOut":"Cut", "cgAutoOff":5 }
  ],
  "leadinScene": "CAM1_ANCHOR"
}
```

- **Master**: 「PDF/설정」 탭 → 「타입 관리 열기」에서 타입을 추가/삭제하고 씬·카메라·서버교번·전환·자막오프타이밍을 편집한다. `localStorage.nbsItemTypes`에 저장되고, 저장 시 `TYPE_RULES`/`SCENE_MAP`/`TYPE_LABELS`가 다시 만들어진다.
- **MARS**: 툴바의 ⚙ 「Master 타입 설정」에서 자체 레지스트리 사본(`localStorage.marsItemTypes`)과, NPS 코드(타/단/완 직접 매핑, '특'은 키워드 규칙 목록)→Master 타입 키 매핑(`localStorage.marsTypeMapping`)을 편집한다.
- 두 앱 다 위 JSON 포맷으로 내보내기/가져오기 가능 — Master에서 타입을 바꾼 뒤 내보낸 `item-types.json`을 MARS에 가져오면 MARS의 매핑 드롭다운 선택지도 같이 갱신된다.
- 기본값 배열(`DEFAULT_ITEM_TYPES`)은 두 HTML 파일에 각각 복사돼 있다 — 새 타입을 영구 기본값으로 추가하려면 양쪽 다 고쳐야 한다 (또는 내보내기/가져오기로 동기화).

---

## 7. 개발 로드맵

### Phase 1 — 현재 (HTML 프로토타입 완료)
- [x] Master 방송제어 앱 (`news-broadcast-system.html`) — OBS 어댑터, 영상 서버 운영 모드 설정
- [x] MARS 큐시트 제작 화면 (`nps-news-system.html`)
- [x] MARS 기사편집 화면 (`mars-news-editor.html`)
- [x] OBS WebSocket 연동 (Master)
- [x] MARS → Master 큐시트 JSON 내보내기/불러오기 (파일 기반)
- [x] 큐시트 구조 및 규칙 문서 (`obsnewscontrol.md`)

### Phase 2 — 백엔드 연동
- [ ] Node.js API 서버 구축
- [ ] PostgreSQL DB 스키마 설계
- [ ] JWT 인증·권한 미들웨어
- [ ] Socket.io 실시간 동기화
- [ ] 파일 업로드 API (영상)
- [ ] MARS → Master 큐시트 전달을 파일 대신 API로 전환 (포맷은 동일하게 유지)

### Phase 3 — 통합 연동
- [ ] MARS 내부 기사편집 ↔ 큐시트 제작 화면 데이터 연동 API
- [ ] MARS ↔ Master 큐시트 실시간 동기화 (확정 즉시 반영)
- [ ] Master 디바이스 어댑터 확장: vMix / VMU / AMU / 송출서버 / 자막기
- [ ] PDF 큐시트 자동 파싱 (pdfplumber)

### Phase 4 — 운영 안정화
- [ ] 다중 사용자 충돌 방지 (Optimistic Lock)
- [ ] 방송 로그 기록 및 조회
- [ ] 자동 백업 및 복구
- [ ] iPad/태블릿 반응형 최적화

---

## 8. 방송 전 체크리스트 (표준 SOP)

```
□ 1. 백엔드 서버 가동 확인
□ 2. 메인 방송 PC OBS 실행 → WebSocket 활성화 (4455)
□ 3. OBS 스튜디오 모드 ON
□ 4. Master 브라우저 열기 → OBS 연결 (초록 도트 확인)
□ 5. 큐시트 확정 상태 확인 (MARS에서 ADMIN 확정)
□ 6. 카메라 1~4 신호 확인 (OBS 멀티뷰)
□ 7. SRV1에 첫 번째 클립 로드 확인
□ 8. SRV2에 두 번째 클립 사전 로드 확인
□ 9. 앵커 MIC 레벨 확인 (Master 오디오 탭)
□ 10. CG 소스 정상 확인 (CG_LOWER_THIRD, CG_NAME)
□ 11. 제작 클라이언트 5대 로그인 및 권한 확인
□ 12. 큐시트 실시간 동기화 테스트
□ 13. 리허설 1회 진행
□ 14. 서버 교대 카운터 0 초기화 (Master 처음부터 버튼)
```

---

*이 문서는 뉴스 방송 시스템의 기준 설계 문서입니다.*  
*실제 방송 적용 전 충분한 테스트 환경에서 검증하세요.*
