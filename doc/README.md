# MARS/Master 문서 모음 — 통합 인덱스

뉴스 자동송출 시스템의 기획서·가이드·매뉴얼 인덱스입니다.
브라우저에서 보기 좋은 버전: **[doc/index.html](index.html)** (server.py 실행 후 `http://localhost:8080/doc/index.html`, 검색 필터 지원) — 여기서 문서를 클릭하면 원본 마크다운을 제목·표·코드블록·체크리스트가 정리된 화면(`doc/viewer.html`)으로 바로 보여줍니다. GitHub에서 이 파일을 직접 보고 있다면 아래 표의 링크는 GitHub 자체 렌더링으로 열립니다.

문서는 성격별로 4곳에 나뉩니다:

| 폴더 | 성격 |
|---|---|
| `doc/spec/` | 기획·설계 — 제품이 무엇이고 어디로 가는지 (PRD, 아키텍처, 데이터 모델) |
| `doc/guide/` | 설정·연동 가이드 — 장비를 연결하고 설정하는 절차 |
| `user-guide/` | 사용자 매뉴얼 — 완성된 기능의 사용법 (화면 캡처 포함, PDF 내보내기 가능) |
| `doc/archive/` | 초기 프로토타입·원본 자료 — 이력 보존용, 현재 미사용 |

---

## 🚀 시작하기 · 사용자 매뉴얼

| 문서 | 상태 | 설명 |
|---|---|---|
| [README](../README.md) | 현행 | 프로젝트 개요, 실행 방법, 날짜별 변경 이력 |
| [개발 현황 (STATUS)](STATUS.md) | 현행 | 완료(실장비 검증)/진행 중/미착수 구분과 단기 일정 — 2026-07-15 기준 |
| [전체 시스템 입문 매뉴얼](../user-guide/getting-started-manual.html) | 현행 | 약 20페이지 전체 개요 — MARS 제작부터 Master 진행까지 |
| [자막 IN/OUT 타이밍 가이드](../user-guide/subtitle-in-out-guide.html) | 현행 | 자막별 등장/퇴장 시점 설정, 타임라인 트림 사용법 |
| [전환 효과 설정 가이드](guide/전환%20효과%20설정%20가이드.html) | 현행 | 아이템 간 전환과 타입별 기본 효과 설정 방법 |

## 📐 기획 · 설계 (`doc/spec/`)

| 문서 | 버전/일자 | 상태 | 설명 |
|---|---|---|---|
| [NEWS_BROADCAST_PRD.md](spec/NEWS_BROADCAST_PRD.md) | v1.0 · 06-23 | 기준 문서 | 최초 PRD — Phase 1~3 로드맵, 권한 체계, 데이터 모델 |
| [system-architecture.md](spec/system-architecture.md) | v1.1 · 06-24 | 기준 문서 | MARS/Master 역할 분리, 핸드오프 흐름, Phase 2 백엔드 계획 |
| [newsformat.md](spec/newsformat.md) | v0.2 · 07-10 | 설계 단계 | 뉴스 형식 표준화 + MOS Protocol/NRCS 연동 데이터 모델 |
| [login.md](spec/login.md) | v0.1 · 07-10 | 설계 단계 | 로컬 계정 → 소셜 로그인 구현 계획 (구현 착수 전) |
| [개발 히스토리 회고](spec/개발-히스토리-회고.html) | 07-10 | 현행 | 9번의 커밋·30개 세션 메모리 기반 반복 오류 패턴 6가지와 개선 지점 (claude.ai 아티팩트 이관) |
| [중간보고서 — 상업화 로드맵](spec/중간보고서-상업화로드맵.html) | 07-10 | 현행 | 완료/미착수 현황, login.md 아키텍처 결정 사항, 상업화 로드맵, 7/17까지 할 일 (claude.ai 아티팩트 이관) |
| [OnAir Connect — 초기 구상 대화록](spec/OnAir_Connect_초기구상.md) | 07-04 이전 | 기원 문서 | 상업화 방향을 처음 논의한 원본 대화 — 아래 리포트·제안서·login.md의 출발점 |
| [vMix 사용자 불편사항 분석](spec/vMix_사용자_불편사항_분석_리포트.md) | 07-04 | 리서치 | 리뷰·포럼 정성 분석 — 상업화 기획 근거 자료 |
| OnAir_Connect_제안서.pptx | 07-10 | 제안서 | 상업화 제품(OnAir Connect) 제안 덱 — `doc/spec/` (바이너리, 파워포인트로 열기) |
| [Expansion_PRD.md](spec/Expansion_PRD.md) | v1.0 · 07-10 | 진행 중 | Videohub→VMU→AMU 장비 확장 — Phase 1 실장비 검증 완료 |
| [Live.md](spec/Live.md) | v0.1 · 07-01 | 부분 구현 | 시사교양 라이브 제작 큐시트 기획 (MARS 제작 큐시트 탭의 근거) |
| [Cuesheet-UI.md](spec/Cuesheet-UI.md) | 07-01 | 부분 구현 | 제작 큐시트 3패널 UI/UX 설계 (Live.md 하위 문서) |

## 🔧 설정 · 연동 가이드 (`doc/guide/`)

| 문서 | 일자 | 상태 | 설명 |
|---|---|---|---|
| [🚨 troubleshooting.md](guide/troubleshooting.md) | 07-10 | 현행 | **실전 문제해결 가이드** — 실제 발생 사례 기반 증상별 진단·해결책 |
| [Integration_Guide.md](guide/Integration_Guide.md) | v1.0 · 07-10 | 진행 중 | 장비 연동 단계별 작업 순서서 (Expansion_PRD의 실행 문서) |
| [OBS 씬 구조.md](guide/OBS%20씬%20구조.md) | 07-09 기준 | 스냅샷 | 실제 OBS 씬 20개·소스 19개 구조와 추천 매핑 (시점 기록물) |
| [OBS_SETUP_GUIDE.html](guide/OBS_SETUP_GUIDE.html) | 06-23 | 초기 버전 | OBS 설치·websocket 초기 설정 — 최신 씬 구조는 위 문서 우선 |

## 🎓 바이브 코딩 교재 (`doc/textbook/`)

이 프로젝트를 진행하며 만든 학습 교재 — 두 트랙으로 분권. **[트랙 안내](textbook/index.html)**에서 시작.

| 트랙 | 문서 | 대상 |
|---|---|---|
| 비기너 | [비기너 교재 — 6단계](textbook/beginner/바이브코딩-비기너-교재-6단계.html) | 첫 프로그램: 환경→PRD→Git→배포→DB |
| 중급자 | [중급자 교재 — 5장](textbook/intermediate/바이브코딩-중급자-교재.html) | 모델 운용, 클로드 200%, ★실전 사례 연구, 하드닝, 에이전트 스택 |
| (딸림) | [모델 선택 가이드](textbook/intermediate/model-selection-guide.html) · [AI 에이전트 스택 설명서](textbook/intermediate/바이브코딩_AI에이전트_스택_설명서.html) | 중급자 트랙 부교재 |

**판본 이력(확정)**: 비기너 v1.0(5단계) → 통합본 v1.1(6단계) → 통합본 v1.2(1~8장) → **2026-07-10 분권**: 비기너 **v2.0** + 중급자 **v1.0**. 이후 두 권은 독립 버전 관리, 통합본 v1.2는 동결 — 원본은 `textbook/archive/`에 보존("분권 전 원본" 표기).

## 🗄 아카이브 (`doc/archive/`)

참고용입니다. 같은 내용의 최신 버전이 spec/guide에 있으면 그쪽이 항상 우선입니다.

| 파일 | 설명 |
|---|---|
| `NEWS_BROADCAST_PRD.html` | PRD의 HTML 변환본 (원본 md가 기준) |
| `news-cuesheet-app.html` / `app2.html` | 06-23 최초 단일 화면 프로토타입 |
| `cuesheet_parser.py` | PDF 파서 초기판 — 현재 Master 내장 파서로 대체 |
| `document_pdf*.pdf` (3종) | 파서 개발에 쓰인 실제 큐시트 PDF 원본 |
| `*.png` (5종) | 06-23 기획 단계 설계 다이어그램 |

---

**문서 갱신 규칙** (프로젝트 관행): 새 기능이 완성되면 `user-guide/`에 자체 HTML 가이드를 추가하고, 이 인덱스(`index.html` + `README.md`)에도 항목을 추가한다. 시점 기록물(스냅샷)은 갱신하지 않고 새 날짜로 다시 만든다.
