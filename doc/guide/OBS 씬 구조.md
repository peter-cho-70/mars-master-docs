# OBS 씬 구조 — 현재 상태 스냅샷

**작성일**: 2026-07-09
**대상**: `news-broadcast-system-obs.html`(Master OBS판)이 실제로 연동한 OBS 인스턴스(obs-websocket, 이 세션 기준 `192.0.2.10:4455`)
**성격**: 특정 시점의 실제 조회 결과를 정리한 스냅샷 — 씬을 추가/삭제하면 이 문서는 오래된 내용이 된다. 필요하면 Master 스위처 탭의 "OBS 씬/소스 목록 → 새로고침"으로 언제든 최신 목록을 다시 확인할 수 있다.

---

## 1. 기본 개념 — vMix와 다른 점

- vMix: "List" 인풋 하나에 파일을 여러 개 미리 올려두고, 그중 몇 번째를 재생할지 고른다(사전 등록 필요).
- OBS: 그런 "리스트" 개념이 없다. 대신 **미디어 소스(source) 하나가 파일 경로 하나만 들고 있고**, Master가 큐시트의 파일명을 매 재생마다 `SetInputSettings`로 그 소스에 새로 꽂아넣는다. 사전 등록이 필요 없다([[mars-master-obs-version]] 메모리의 실제 재생 테스트로 검증됨).
- 그래서 OBS 쪽에 필요한 건 "재생목록"이 아니라 **① 컷 대상이 되는 씬**과 **② 그 씬 안에 자리 잡은, 파일을 갈아끼울 미디어 소스** 두 가지뿐이다. 소스 자체는 지우면 안 된다(지우면 `SetInputSettings`가 대상을 못 찾아 실패한다) — 미리 채워둔 재생목록 내용만 정리해도 무방하다.

Master의 데이터 모델(`switcherSources[]`)은 이 둘을 각각 `obsScene`(컷 대상 씬 이름)과 `obsSource`(SRV 전용, 파일을 갈아끼울 미디어 소스 이름) 필드로 가지고 있다.

---

## 2. 전체 씬 목록 (20개) + 포함된 소스

| 씬 이름 | 포함된 소스 | 추정 용도 |
|---|---|---|
| `TITLE` | SERVER1 | 타이틀 영상 |
| `CM_PRE` | SERVER1 | CM(광고) |
| `CAM1_ANCHOR` | CAM1, 이미 | 앵커 캠(1번) |
| `CAM2_ANCHOR` | CAM2, CG_LOWER_THIRD, 앵커이미 | 앵커 캠(2번, 리포트/단신 기본 앵커 샷) |
| `CAM1_CAM2_2SHOT` | CAM1, CAM2 | 앵커 투샷 |
| `CAM3_WIDE` | CAM3 | 와이드 샷 |
| `CAM4_CLOSEUP` | CAM4 | 클로즈업 샷 |
| `SRV1_VCR` | SERVER1 | 서버1 영상 단독 재생 |
| `SRV2_VCR` | SERVER2 | 서버2 영상 단독 재생 |
| `SRV3_VCR` | SERVER3 | 서버3 영상 단독 재생 |
| `CAM1_SRV1_PIP` | SERVER1, CAM1 | 카메라+서버1 PIP(화면 속 화면) |
| `CAM1_SRV2_PIP` | SERVER2, CAM1 | 카메라+서버2 PIP |
| `WEATHER` | CG_LOWER_THIRD, CAM2, weather, SERVER1 | 날씨 코너(합성) |
| `CLOSING` | CAM1, CAM2, SERVER1 | 클로징 |
| `LIVE_STOCK` | BLACK_COLOR | 라이브 중계(대기 화면, 아직 미구성) |
| `LIVE_EXT` | BLACK_COLOR | 외부 연결(대기 화면, 아직 미구성) |
| `Prompt` | Prompt-text | 프롬프터 표시용 |
| `PVW_MONITOR` | SERVER3, PVW_TITLE_TEXT | PD/운영자 모니터링용(온에어 아님) |
| `CG_POOL` | CG_NAME, CG_BREAKING, 앵커1_마이크, 앵커2_마이크 | CG/오디오 소스 보관용 풀(단독 컷 대상 아님) |
| `BLACK` | BLACK_COLOR | 블랙(안전 화면) |
| `DEMO_MASTER_TEST` *(신규 샘플)* | DEMO_MASTER_SRV | 2026-07-09 검증용으로 새로 만든 샘플 — 지워도 무방 |

---

## 3. 전체 소스(미디어 소스 등) 목록 (19개 — 샘플 포함)

| 소스 이름 | 종류(kind) | 비고 |
|---|---|---|
| `SERVER1` | `ffmpeg_source` | **SRV1** 후보 — 실제 재생 테스트에서 사용, 정상 동작 확인됨 |
| `SERVER2` | `ffmpeg_source` | **SRV2** 후보 |
| `SERVER3` | `ffmpeg_source` | **SRV3** 후보 |
| `DEMO_MASTER_SRV` | `ffmpeg_source` | 샘플용, 실제 재생까지 검증됨 |
| `weather` | `ffmpeg_source` | 날씨 코너 전용 영상(SRV로 재사용하지 말 것 — WEATHER 씬 전용) |
| `CAM1` | `color_source_v3` | ⚠ 지금은 실제 카메라 캡처가 아니라 단색 placeholder — 실카메라 연결 전 임시 |
| `CAM2` | `color_source_v3` | ⚠ 위와 동일, placeholder |
| `CAM3` | `macos-avcapture` | 실제 카메라 캡처 |
| `CAM4` | `macos-avcapture` | 실제 카메라 캡처 |
| `BLACK_COLOR` | `color_source_v3` | 블랙/대기 화면용 |
| `CG_LOWER_THIRD` | `text_ft2_source_v2` | 텍스트 CG |
| `CG_NAME` | `text_ft2_source_v2` | 텍스트 CG |
| `CG_BREAKING` | `text_ft2_source_v2` | 텍스트 CG |
| `TITLE_TEXT` | (조회 시점에 따라 있을 수 있음) | 텍스트 CG |
| `PVW_TITLE_TEXT` | `text_ft2_source_v2` | 모니터링용 텍스트 |
| `Prompt-text` | `text_ft2_source_v2` | 프롬프터 텍스트 |
| `앵커1_마이크` / `앵커2_마이크` | `coreaudio_input_capture` | 실제 마이크 캡처 |
| `앵커이미` / `이미` | `image_source` | 정지 이미지 |

> `kind`가 `ffmpeg_source`인 것만 "미디어 소스"(파일 재생용)다 — Master 스위처 탭의 "OBS 씬/소스 목록"도 이 종류만 굵게 표시한다. `color_source_v3`/`macos-avcapture`/`text_ft2_source_v2`/`image_source`/`coreaudio_input_capture`는 각각 단색·카메라·텍스트·이미지·오디오 캡처이며 SRV 후보가 아니다.

---

## 4. Master 스위처 소스 매핑 — 적용 완료 (2026-07-09)

처음 조회 시점엔 `switcherSources[]`의 `obsScene`/`obsSource`가 10개 슬롯 전부 빈 값이었으나, 아래 추천 매핑을 실제로 "스위처 소스 관리"에 저장했다 — 새로고침 후에도 유지되는 것까지 확인됨. `dve1-3`은 이름 규칙(PIP/투샷)에 근거한 추정이라 실제 화면과 맞는지 한 번 확인 권장(나머지 특수 씬 정리는 운영자가 직접 진행 예정 — 5장 참고):

| switcherSources id | 저장된 `obsScene` | 저장된 `obsSource` | 근거 |
|---|---|---|---|
| `cam1` | `CAM1_ANCHOR` | (해당 없음 — CAM 슬롯은 obsScene만 씀) | 이름 일치 |
| `cam2` | `CAM2_ANCHOR` | — | REPORT/ANCHOR 타입 규칙(`rule.cams:['cam2']`)과 일치, 실제 검증 완료 |
| `cam3` | `CAM3_WIDE` | — | 이름 일치 |
| `cam4` | `CAM4_CLOSEUP` | — | 이름 일치 |
| `srv1` | `SRV1_VCR` | `SERVER1` | **실제 재생 테스트로 검증됨** |
| `srv2` | `SRV2_VCR` | `SERVER2` | 이름 일치(패턴 동일) |
| `srv3` | `SRV3_VCR` | `SERVER3` | 이름 일치(패턴 동일) |
| `dve1` | `CAM1_SRV1_PIP` | (dve는 obsScene만 씀) | PIP=DVE로 추정 |
| `dve2` | `CAM1_SRV2_PIP` | — | PIP=DVE로 추정 |
| `dve3` | `CAM1_CAM2_2SHOT` | — | 투샷=DVE로 추정 |

**설정 방법**: Master → 스위처 탭 → "OBS 씬/소스 목록"에서 "새로고침" → 원하는 씬/소스 옆 "→cam1" 등 버튼 클릭 → 설정(PDF/설정) 탭 "스위처 소스 관리"에서 "저장" 클릭.

---

## 4-1. CG 자막용 브라우저 소스 `CG_OVERLAY` (2026-07-09 추가)

위 4장의 매핑 10개 씬(`CAM1_ANCHOR`/`CAM2_ANCHOR`/`CAM3_WIDE`/`CAM4_CLOSEUP`/`SRV1_VCR`/`SRV2_VCR`/`SRV3_VCR`/`CAM1_SRV1_PIP`/`CAM1_SRV2_PIP`/`CAM1_CAM2_2SHOT`) 전부에 **같은 브라우저 소스 하나**(`CG_OVERLAY`, URL `http://192.0.2.10:8080/obs-cg-overlay.html`, 1920×1080)를 공유 참조로 추가했다 — 씬마다 새로 만든 게 아니라 하나의 소스를 여러 씬에 걸쳐 재사용한 것이라, 나중에 URL을 한 번만 바꿔도 전부 적용된다. 각 씬에서 가장 위(맨 앞) 순서로 들어가 있어 카메라/영상 위에 정상적으로 겹쳐 보이는 구조다.

⚠️ **확인 필요**: obs-websocket의 `GetSourceScreenshot`가 이 브라우저 소스만은 캡처를 못 하는 것으로 확인됐다(구조/설정은 전부 정상인데 스크린샷만 계속 빈 화면으로 나옴 — 간단한 빨간 배경 테스트 페이지로도 재현됨, OBS 브라우저 소스의 알려진 스크린샷 API 한계로 추정). 그래서 **API로는 최종 확인이 안 됐고, 실제 OBS 화면에서 직접 눈으로 확인이 필요하다** — 프로그램 모니터에서 위 10개 씬 중 하나를 띄운 상태로 Master의 "▶ 테스트 자막 8종 전송" 버튼을 눌러보고 실제로 보이는지 확인해달라.

## 5. 매핑되지 않는 씬들 (일반 슬롯 밖의 특수 씬)

`TITLE`/`CM_PRE`/`WEATHER`/`CLOSING`/`LIVE_STOCK`/`LIVE_EXT`/`Prompt`/`PVW_MONITOR`/`CG_POOL`/`BLACK`은 위 10개 일반 슬롯(cam1-4/srv1-3/dve1-3) 어디에도 딱 맞지 않는다. 지금 Master의 `applyItemToOBS`/`startAnchorPhaseOBS` 로직은 아이템 타입별로 **일반 슬롯(카메라 또는 서버)만 골라 컷**하는 구조라, 이런 타입별 전용 합성 씬(예: WEATHER 씬처럼 날씨 영상+카메라+CG가 이미 한 씬에 합쳐진 구성)을 그대로 활용하려면 별도 연동 로직이 필요하다 — **지금은 반영되어 있지 않다.** 당장 문제는 아니지만(카메라/서버 슬롯만으로도 방송은 가능), 이 특수 씬들을 실제로 쓰고 싶다면 이후 별도로 다뤄야 한다.

---

## 6. 참고

- 이 스냅샷을 만든 방법(재현 가능): Master 페이지에서 `obsCall('GetSceneList')` + `obsCall('GetInputList')` + 각 씬마다 `obsCall('GetSceneItemList', {sceneName})`.
- `DEMO_MASTER_TEST`/`DEMO_MASTER_SRV`는 실제 재생 파이프라인 검증용으로 2026-07-09에 만든 샘플이다 — 필요 없으면 OBS에서 지워도 되고, 참고용으로 남겨둬도 무방하다.
- 관련 메모리: `mars-master-obs-version` (OBS판 전체 구현 이력), `master-switcher-source-management` (switcherSources 데이터 모델 배경).
