# newsformat.md — 뉴스 아이템 형식 정의서

버전: v0.2 (MOS Protocol 정합화)
목적: 뉴스 아이템의 표준 형식을 정의하고, 이를 **MOS Protocol(현행 2.8.5/4.0 기준)과 NRCS(iNEWS, ENPS, Octopus, Dalet 등) 연동 자동화 프로그램**에서 실제로 사용할 수 있는 데이터 모델로 옮긴다.
원칙: **기본형(Base Format)을 정의하고, 변형(Variant)은 기본형의 시퀀스 수정으로 표현한다.** 이렇게 하면 소수의 기본형으로 모든 뉴스 형식을 조립할 수 있다.

**중요한 전제**: MOS Protocol 자체는 "리포트/단신/중계차" 같은 방송 형식을 모른다. MOS가 아는 것은 `Running Order(런다운) → Story(뉴스 아이템) → Item(재생 요소) → Object(실제 미디어)`라는 계층 구조뿐이다. 따라서 이 문서 §1~3에서 정의한 형식·시퀀스·자막 규칙은 MOS 표준 필드가 아니라, **`mosExternalMetadata`(NCS-벤더 확장 메타데이터 슬롯)에 실어 나르는 자체 스키마**로 다룬다. §4에서 이 매핑을 구체적으로 정의한다.

---

## 1. 공통 구성 요소 (Building Blocks)

모든 뉴스 형식은 아래 요소들의 시퀀스(순서 배열)로 표현한다.

### 1.1 화면 요소 (Video Elements)

| 코드 | 명칭 | 설명 |
|---|---|---|
| `ANC` | 앵커샷 | 스튜디오 앵커 단독 샷 (1샷/2샷 구분 가능) |
| `CUT` | 커트 | 앵커멘트 → 리포트 영상 전환 시의 컷 전환 |
| `DIS` | 디졸브 | 앵커 → 영상 전환 시 디졸브 트랜지션 |
| `PKG` | 리포트 영상 | 기자 오디오 + 편집 영상 (완제 패키지) |
| `VCR` | 자료/현장 영상 | 앵커 오디오 위에 얹는 영상 (단신용) |
| `LIVE` | 중계차 현장 | 현장 생중계 영상 |
| `SPLIT-A` | 앵커 갈라치기 | 앵커(스튜디오)와 기자(현장/스튜디오)를 분할 화면으로 |
| `SPLIT-S` | 서버 갈라치기 | 기자 샷과 서버 영상(자료화면)을 같은 화면에 분할 |
| `FULL` | 풀샷 | 스튜디오 전경(앵커+출연자) |
| `GUEST` | 출연자샷 | 기자/인터뷰이 단독 샷 |
| `INT` | 인터뷰 영상 | 사전 촬영된 인터뷰 클립 |
| `HALF` | 반제 | 중계차 아이템 중간에 삽입하는 리포트형 완제 영상 |
| `CHROMA` | 크로마키 | 크로마키 배경 합성 (날씨 등) |
| `CG-FULL` | 전면 그래픽 | 화면 전체 그래픽 (통계, 도표, 그래픽 뉴스) |
| `STUP` | 스탠드업 | 기자가 현장에서 카메라 앞에 서서 말하는 장면 (PKG 내부 요소) |

### 1.2 오디오 요소 (Audio Elements)

| 코드 | 명칭 | 설명 |
|---|---|---|
| `A-ANC` | 앵커 오디오 | 앵커가 스튜디오에서 읽음 |
| `A-RPT` | 기자 오디오 | 기자가 사전 녹음 (리포트) 또는 현장 발화 (중계) |
| `A-INT` | 인터뷰 오디오 | 인터뷰이 발화 |
| `A-NAT` | 현장음 | 자연음(내추럴 사운드), 이펙트 |

### 1.3 자막 요소 (CG / Caption Elements)

| 코드 | 명칭 | 설명 |
|---|---|---|
| `T-GEN` | 일반 자막 | 영상 하단 내용 자막 |
| `T-INT` | 인터뷰 자막 | 발언 내용 + 발언자 신원(이름/직책) 표기 |
| `T-BOK` | 복대 자막 | 앵커/영상 하단 고정 요약 자막 (단신의 기본). 필요 시 복수 사용 |
| `T-NAME` | 네임 수퍼 | 기자명, 출연자명, 리포터명 표시 |
| `T-LOC` | 장소/시각 수퍼 | "OO 현장", "잠시 전", "LIVE" 등 |
| `T-HEAD` | 헤드라인 자막 | 헤드라인/예고용 대형 자막 |
| `T-SCORE` | 스코어/데이터 자막 | 스포츠 점수, 날씨 수치 등 데이터형 자막 |

---

## 2. 기본 뉴스 형식 정의 (Base Formats)

### 2.1 리포트 (REPORT / 완제 패키지) — 코드 `RPT`

기자가 기사를 쓰고 본인이 직접 오디오를 녹음, 그 오디오에 맞춰 영상을 편집한 완제 형식. 뉴스의 가장 기본 단위.

**시퀀스:**
```
ANC(앵커멘트) > CUT > PKG(기자 오디오 + 편집 영상)
```

**자막 규칙:**
- PKG 내 필요한 지점에 `T-GEN`(일반 자막)
- 인터뷰 구간에는 `T-INT`(발언자 신원 포함)
- 기자 마무리 멘트("OOO 뉴스 김OO입니다") 부근에 `T-NAME`
- PKG 내부에 `STUP`(스탠드업)이 포함될 수 있음

**길이 조절:** 완제이므로 방송 중 길이 조절 불가. 사전 편집 단계에서 조절.

---

### 2.2 단신 (STRAIGHT / 스트레이트) — 코드 `STR`

기사는 기자가 쓰되, 방송에서는 앵커가 읽는 형식. 문단 단위로 구성되어 있어 **문단 삭제로 전체 뉴스 길이를 조절하는 버퍼 역할**을 한다.

**시퀀스:**
```
ANC(앵커 리드) > DIS > VCR(앵커 오디오 계속 + 자료 영상)
```

**자막 규칙:**
- 기본 `T-BOK`(복대 자막) 1개
- 내용이 길거나 전개가 있으면 복대 자막 복수 교체 사용

**길이 조절:** 문단 단위 삭제 가능 → 큐시트에서 "조절용(Cuttable)" 플래그 관리 권장.

**변형:**
- `STR-A` (앵커 단신): 영상 없이 앵커샷만으로 진행 (초단신)
- `STR-CG` (그래픽 단신): VCR 대신 CG-FULL 사용

---

### 2.3 중계차 (LIVE / 현장연결) — 코드 `LIV`

기자가 외부 현장에서 준비, 해당 아이템 시간에 현장으로 전환하여 진행. 앵커 질문 수에 따라 갈라치기 횟수가 결정된다.

**기본 시퀀스 (질문 2개 기준):**
```
ANC(앵커멘트) > CUT > SPLIT-A(앵커+기자 분할, 질문1)
> LIVE(현장 답변) > SPLIT-S(기자+서버영상 분할)
> SPLIT-A(질문2) > LIVE(현장) > SPLIT-S > LIVE(현장 마무리)
```

**구성 요소 규칙:**
- `SPLIT-A`(앵커 갈라치기) 개수 = 앵커 질문 개수
- `SPLIT-S`(서버 갈라치기)로 기자 발언 중 관련 자료영상 동시 노출
- 중간에 `INT`(인터뷰 영상) 삽입 가능
- **반제(`HALF`)**: 리포트형 완제 영상을 중계 중간에 삽입 재생 가능

**자막 규칙:**
- `T-LOC`("LIVE", 현장 위치) 상시 노출
- `T-NAME`(기자명), 발언 요지에 `T-BOK` 또는 `T-GEN`

**파라미터:** `질문 수(n)`, `반제 유무`, `인터뷰 유무` → 시퀀스 자동 생성 가능

---

### 2.4 출연 (STUDIO GUEST / 대담) — 코드 `GST`

기자나 인터뷰이가 스튜디오에 나와 앵커와 대화하는 형식.
- 외부 인터뷰이: 사전 녹화가 많음
- 기자/변호사 등 전문가: 생방송 직접 출연이 일반적

**기본 시퀀스:**
```
ANC(소개 멘트) > FULL(풀샷) > GUEST(출연자샷)
> SPLIT-S(출연자+서버영상) > FULL > GUEST > SPLIT-S ...
```

**구성 요소 규칙:**
- 질문/답변 반복 구조 → `FULL`/`GUEST`/`SPLIT-S` 교차가 문답 수만큼 반복
- 사전 녹화 출연은 `VCR`로 대체 재생

**자막 규칙:**
- `T-NAME`(출연자 이름/직책) 답변 시작 시 노출
- 핵심 발언 `T-BOK` 병행 가능

---

### 2.5 날씨 (WEATHER) — 코드 `WEA`

기본은 사전 녹화(크로마키 배경), 특보·장마·호우 시에는 생방송 중계로 전환.

**기본 시퀀스 (녹화):**
```
ANC(연결 멘트) > CUT > CHROMA(기상캐스터 + 크로마 그래픽, 사전 녹화)
```

**특보 시퀀스 (생방송):**
```
ANC > SPLIT-A(앵커 질문) > CHROMA/LIVE(캐스터 생방송 진행) > SPLIT-A(추가 질문) > ...
```

**자막 규칙:**
- `T-SCORE`(기온/강수 데이터), `T-NAME`(캐스터명)
- 특보 시 `T-HEAD`(특보 자막) 상시

---

### 2.6 스포츠 (SPORTS) — 코드 `SPO`

두 가지 운영 형태:
1. **코너형**: 메인 뉴스 내 코너로 편성 (앵커 또는 스포츠 담당이 진행)
2. **독립형**: 별도 타이틀 + 전담 진행자로 스포츠 뉴스 프로그램 운영

**시퀀스 (독립형):**
```
TITLE(스포츠 타이틀) > ANC(스포츠 앵커) > [RPT | STR | LIVE 아이템 반복] > CLOSING
```

**자막 규칙:**
- `T-SCORE`(경기 결과/순위표) 적극 사용
- 하이라이트 영상엔 `T-GEN` + `T-LOC`(경기장/일시)

---

## 3. 확장 형식 (조사 기반 추가 정의)

기본형에서 파생되거나, 방송 뉴스에서 통용되는 추가 형식들.

### 3.1 헤드라인 (HEADLINE) — 코드 `HED`
뉴스 시작부에 주요 아이템을 예고. 아이템별 대표 영상 + `T-HEAD` 자막 + 앵커/성우 오디오.
```
TITLE > [VCR + T-HEAD] x n개 > ANC(오프닝 인사)
```

### 3.2 앵커멘트 단독 (ANCHOR ONLY) — 코드 `ANC-O`
영상 없이 앵커샷만으로 전하는 짧은 소식, 사과/정정 멘트, 클로징 멘트.
```
ANC (T-BOK 선택)
```

### 3.3 브릿지/코너 타이틀 (BRIDGE) — 코드 `BRG`
코너 전환용 짧은 타이틀 영상. 오디오는 시그널 음악.
```
TITLE(코너 타이틀 영상, 3~7초)
```

### 3.4 그래픽 뉴스 (CG NEWS) — 코드 `CGN`
통계·수치 중심 아이템. 앵커 오디오 + 전면 그래픽 진행.
```
ANC > DIS > CG-FULL(데이터 그래픽, 앵커 오디오 계속)
```

### 3.5 일문일답 / 인터뷰 전문 (Q&A) — 코드 `QNA`
사전 촬영한 인터뷰를 문답 그대로 편집해 방송. 출연(GST)의 녹화 변형.
```
ANC(소개) > CUT > INT(문답 편집본, T-INT 상시)
```

### 3.6 스케치/르포 (SKETCH) — 코드 `SKT`
현장 분위기 전달 중심. 내레이션 최소화, 현장음(`A-NAT`) 중심의 리포트 변형.
```
ANC > CUT > PKG(현장음 중심 편집)
```

### 3.7 특보 (BREAKING) — 코드 `BRK`
정규 편성을 중단하고 진행. 기본형 조합으로 구성하되 다음 특성:
- `T-HEAD`(특보 자막) 상시 노출
- `LIV`(중계차) 및 `GST`(전문가 출연) 비중 확대
- 큐시트가 실시간으로 재배열됨 → 시스템은 아이템 순서 변경/삽입에 즉시 대응해야 함

### 3.8 마무리/클로징 (CLOSING) — 코드 `CLO`
```
ANC(클로징 멘트) > TITLE(엔딩 타이틀/크레딧)
```

---

## 4. MOS Protocol 데이터 모델 매핑

### 4.1 계층 구조 매핑

| 우리 개념 | MOS 표준 엘리먼트 | 비고 |
|---|---|---|
| 런다운(뉴스 프로그램 1회분) | `roCreate` / `<ro>` (Running Order) | `roID`, `roSlug`, `roEdStart`, `roEdDur` |
| 뉴스 아이템(꼭지 1개, 예: "태풍 피해 종합") | `<story>` | `storyID`, `storySlug`, `storyNum` |
| 아이템 내 재생 요소(앵커멘트/PKG/CG 등 개별 트리거 단위) | `<item>` | `itemID`, `itemSlug`, `objID`, `mosID`, `itemChannel`, `itemEdDur` |
| 실제 미디어(서버 클립/그래픽/그래픽 템플릿) | `mosObj` | `objID`, `objSlug`, `objDur`, `objType`, `status` |
| §1~3의 형식 코드·시퀀스·자막 규칙 | `mosExternalMetadata` (story 또는 item에 부착) | MOS 표준에 없는 정보 → §4.3 참조 |

**핵심 구조 (MOS DTD 기준):**
```
roCreate(roID, roSlug, roChannel?, roEdStart?, roEdDur?, roTrigger?, mosExternalMetadata*, story*)
  story(storyID, storySlug?, storyNum?, mosExternalMetadata*, item*)
    item(itemID, itemSlug?, objID, mosID, mosAbstract?, itemChannel?, itemEdStart?, itemEdDur?, itemUserTimingDur?, itemTrigger?, mosExternalMetadata*)
```

우리 큐시트의 **"아이템"(리포트 1건, 중계차 1건 등)은 MOS의 `story`에 대응**하고, 그 안의 **개별 화면 요소(§1.1의 ANC/PKG/SPLIT-A 등)는 각각 `item`에 대응**시킨다. 예를 들어 `LIV`(중계차) 아이템 하나는 MOS story 1개 + item 여러 개(앵커멘트 프롬프터 item, 현장 LIVE 소스 item, 반제 PKG item 등)로 구성된다.

### 4.2 필드 매핑 표

| §5 큐시트 필드(이전 v0.1) | MOS 대응 필드 | 매핑 방식 |
|---|---|---|
| `rundownId` | `roID` | 1:1 |
| `title`(프로그램명) | `roSlug` | 1:1 |
| `onAirDate` | `roEdStart` + `roEdDur` | 1:1 |
| `seq`(순번) | story의 RO 내 순서(위치 자체가 순번, 별도 필드 없음) | RO 내 story 배열 순서 |
| `itemId` | `storyID`(아이템=story 기준) 또는 `itemID`(요소 단위) | §4.1 구조 참고 — **이전 버전의 "itemId↔objID" 표현은 부정확했으므로 폐기.** `objID`는 미디어 자체의 ID, `itemID`는 그 미디어를 story 안에서 가리키는 참조의 ID로 서로 다른 개념 |
| `format`(형식 코드) | `mosExternalMetadata` 내 커스텀 필드 (`ncs:format`) | MOS 표준에 없음 → §4.3 |
| `slug` | `storySlug` | 1:1 |
| `sequence` | `mosExternalMetadata` 내 커스텀 필드 (`ncs:sequence`) | MOS 표준에 없음 |
| `videoSrc` | `objID` + `mosID`(어느 미디어 서버의 어느 오브젝트인지) | 서버형 소스일 때만 해당, 중계차 회선은 `itemChannel`로 표현 |
| `cgList` | `mosExternalMetadata` 내 커스텀 필드 (`ncs:cgList`) | MOS 표준에 없음 |
| `planned` / `itemEdDur` | `itemEdDur`(item 단위), story 합산은 자체 계산 | MOS는 item 단위 예정 길이만 표준 지원 |
| `actual` | `itemUserTimingDur` | MOS 4.0 기준 실제 온에어 타이밍 |
| `cuttable`(문단 삭제 가능 여부) | `mosExternalMetadata` 내 커스텀 필드 (`ncs:cuttable`) | MOS 표준에 없음 |
| `status` | `roElementStat` / `itemStatus`(MOS 상태 값) | §4.5 상태값 매핑 참고 |

### 4.3 커스텀 메타데이터 설계 (`mosExternalMetadata`)

MOS는 벤더/사이트별 확장을 위해 `mosExternalMetadata(mosScope?, mosSchema, mosPayload)` 구조를 정식으로 제공한다. §1~3에서 정의한 형식 코드, 시퀀스, 자막 목록, 조절 가능 여부는 전부 이 안에 담는다.

- `mosScope`: `STORY`(아이템 전체에 적용) 또는 `PLAYLIST`(온에어 재생 목록에만 적용) 중 선택. 형식·시퀀스 정보는 보통 `STORY` 스코프.
- `mosSchema`: 자체 네임스페이스 지정, 예) `urn:onairconnect:newsformat:v1`
- `mosPayload`: 실제 데이터 (XML, 자유 구조)

**예시 — 중계차(LIV) 아이템의 story에 부착되는 mosExternalMetadata:**

```xml
<story>
  <storyID>ST-0710-003</storyID>
  <storySlug>태풍 북상_부산 현장연결</storySlug>
  <storyNum>03</storyNum>
  <mosExternalMetadata>
    <mosScope>STORY</mosScope>
    <mosSchema>urn:onairconnect:newsformat:v1</mosSchema>
    <mosPayload>
      <ncsFormat>LIV</ncsFormat>
      <ncsSequence>ANC&gt;CUT&gt;SPLIT-A&gt;LIVE&gt;SPLIT-S&gt;SPLIT-A&gt;LIVE&gt;SPLIT-S&gt;LIVE</ncsSequence>
      <ncsParams questions="2" half="true" interview="false"/>
      <ncsCuttable>false</ncsCuttable>
      <ncsCgList>
        <cg type="T-LOC" text="LIVE 부산 현장"/>
        <cg type="T-NAME" text="박OO 기자"/>
      </ncsCgList>
    </mosPayload>
  </mosExternalMetadata>
  <item>
    <itemID>IT-0710-003-01</itemID>
    <itemSlug>앵커멘트</itemSlug>
    <objID/>
    <itemChannel>PROMPTER</itemChannel>
  </item>
  <item>
    <itemID>IT-0710-003-02</itemID>
    <itemSlug>현장 LIVE 소스</itemSlug>
    <objID>OBJ-MNG-2</objID>
    <mosID>MNG-SERVER-1</mosID>
    <itemChannel>LIVE</itemChannel>
  </item>
  <item>
    <itemID>IT-0710-003-03</itemID>
    <itemSlug>반제 PKG</itemSlug>
    <objID>OBJ-CL-4471</objID>
    <mosID>VIDEOSERVER-1</mosID>
    <itemEdDur>00:00:45</itemEdDur>
  </item>
</story>
```

이렇게 하면 **NRCS/자동화 프로그램은 표준 MOS 파서로 story/item 구조(순서, 미디어 참조)를 그대로 처리**하면서, **우리 자동화 로직(vMix 시퀀스 트리거, 자막 자동 호출)은 `mosPayload`만 별도로 읽어 처리**하는 구조가 된다. 표준 파서와 우리 로직이 서로 간섭하지 않는 것이 핵심 이점이다.

### 4.4 MOS 메시지 흐름 (런다운 생명주기)

| 단계 | 메시지 | 방향 | 우리 시스템에서의 역할 |
|---|---|---|---|
| 런다운 최초 생성 | `roCreate` | NRCS → MOS(자동화 서버) | 프로그램 개편/신규 방송 시 전체 story/item 목록 전송 |
| 런다운 전체 교체 | `roReplace` | NRCS → MOS | 대규모 개편(순서 대폭 변경) 시 |
| 아이템 순서 변경/삽입/삭제/스왑 | `roElementAction` | NRCS → MOS | **특보(§3.7) 대응의 핵심.** MOS 2.8부터는 개별 `roStoryInsert/Move/Delete/Swap` 대신 이 메시지 하나로 통합 처리 |
| 메타데이터만 갱신 | `roMetadataReplace` | NRCS → MOS | 앵커 교체, 슬러그 수정 등 시퀀스 변경 없는 편집 |
| 상태 보고(단건) | `roElementStat` | MOS → NRCS | item/story 단위 준비 상태(READY/NOT READY 등) 보고 — §4.5 |
| 방송 준비 완료 선언 | `roReadyToAir` | NRCS → MOS | 큐시트 확정, 자동화 시스템에 "이 런다운은 방송 가능" 통지 |
| 재생 트리거/큐잉 | `roItemCue`, `roCtrl` | MOS ↔ NRCS (Profile 5) | **온에어 중 실제 재생 시점 동기화.** vMix 트리거와 직접 연결되는 지점 |
| 동기화 복구 | `roReq` → `roList` | MOS → NRCS → MOS | 자동화 시스템이 사용자 조작 등으로 로컬 순서가 NRCS와 어긋났을 때, 최신 전체 목록을 재요청해 강제 동기화 |

**중요 규칙**: MOS 스펙은 순서 변경 시 "삭제 후 재삽입" 대신 반드시 `roElementAction`(move류)을 쓰라고 명시한다. 삭제로 처리하면 수신측이 해당 story의 본문을 완전히 지운 것으로 간주해 버릴 수 있어, 특보 중 아이템을 임시로 뒤로 밀었다가 다시 앞으로 가져오는 경우에도 삭제가 아니라 이동으로 처리해야 한다.

### 4.5 상태값(Status) 매핑

이전 버전에서 쓴 `READY / STANDBY / 방송됨 / DROP` 같은 자체 상태값은 MOS `roElementStat`/`itemStatus`가 사용하는 표준 상태 개념과 아래와 같이 맞춘다. (구체적 열거값은 벤더/NRCS 구현체마다 다르므로, 실제 연동 시 대상 NRCS의 상태 코드표 확인 필요.)

| 우리 상태 | MOS/NRCS 측 대응 개념 |
|---|---|
| `READY` | item이 재생 가능 상태로 `roElementStat`에 정상 보고됨 |
| `STANDBY` | cue는 되었으나 온에어 전 대기 (`roItemCue` 수신, 재생 미실행) |
| `ON-AIR` | 실제 재생 중 (Profile 5 `roCtrl` 진행 상태) |
| `PLAYED` | 재생 완료, `itemUserTimingDur` 기록됨 |
| `DROPPED` | 특보 등으로 순서에서 제외 — `roElementAction`(delete/move) 처리됨 |
| `DISCONNECTED` | 자동화 측에서 사용자가 로컬로 순서를 강제 변경해 NRCS와 동기화가 끊긴 상태. MOS 스펙상 이 경우 시스템은 즉시 `roReq`로 재동기화해야 함 |

### 4.6 지원 MOS Profile 범위

| Profile | 내용 | 채택 여부 | 사유 |
|---|---|---|---|
| Profile 0/1/2 | 기본 연결, RO 생성/조회, Story/Item 구조 | **필수** | 큐시트 동기화의 최소 요건 |
| Profile 3/4 | 아이템 상태 피드백 확장 | **필수** | `roElementStat` 세밀 보고로 §4.5 상태 매핑 구현 |
| Profile 5 | `roItemCue`, `roCtrl` (아이템 큐잉/제어) | **필수(핵심)** | vMix 트리거와 실시간 연동하려면 이 프로파일이 있어야 "지금 이 item이 재생된다"는 신호를 받을 수 있음 |
| Profile 6 | 멀티 서버 환경 `mosID`/`ncsID` 명명 규칙 | 선택 | 서버가 1대뿐인 초기 단계에서는 불필요, 다중 vMix 인스턴스/다중 서버로 확장 시 채택 |

### 4.7 형식별 기본 시퀀스 템플릿 (시스템 프리셋)

시스템은 `ncsFormat` 코드를 선택하면 기본 시퀀스를 자동 생성해 `mosPayload`에 채우고, 파라미터로 변형한다. story 생성 시 이 템플릿을 기반으로 §4.1의 item들을 자동 생성한다.

```yaml
RPT:
  sequence: [ANC, CUT, PKG]
  params: { stup: false }

STR:
  sequence: [ANC, DIS, VCR]
  params: { bokCount: 1, cuttableParagraphs: [] }

LIV:
  sequence_rule: "ANC > CUT > (SPLIT-A > LIVE > SPLIT-S) x n > LIVE(end)"
  params: { questions: 2, half: false, interview: false }

GST:
  sequence_rule: "ANC > (FULL > GUEST > SPLIT-S) x n"
  params: { questions: 3, prerecorded: false }

WEA:
  sequence: [ANC, CUT, CHROMA]
  params: { live: false, anchorQnA: false }

SPO:
  sequence_rule: "TITLE > ANC > items[] > CLOSING"
  params: { standalone: true }
```

---

## 5. 큐시트 예시 (뉴스 9, 45분 기준 발췌)

| 순번 | 형식 | 슬러그 | 담당 | 시퀀스 요약 | 예정 | 누계 | 조절 | 상태 |
|---|---|---|---|---|---|---|---|---|
| 01 | HED | 헤드라인 | A1/A2 | TITLE>VCR x4 | 0:50 | 0:50 | - | READY |
| 02 | RPT | 태풍 피해 종합 | 김OO | ANC>CUT>PKG | 2:10 | 3:00 | - | READY |
| 03 | LIV | 부산 현장연결 | 박OO | ANC>SPLIT-A x2>LIVE | 3:00 | 6:00 | - | STANDBY |
| 04 | STR | 항공편 결항 | A2 | ANC>DIS>VCR | 0:40 | 6:40 | 문단2 | READY |
| 05 | GST | 전문가 출연: 태풍 전망 | 이OO 교수 | FULL>GUEST>SPLIT-S x3 | 4:00 | 10:40 | - | READY |
| 06 | CGN | 태풍 경로 그래픽 | A1 | ANC>DIS>CG-FULL | 1:00 | 11:40 | - | READY |
| ... | | | | | | | | |
| 21 | SPO | 스포츠 코너 | 스포츠A | TITLE>ANC>RPT x3 | 6:00 | 40:00 | - | READY |
| 22 | WEA | 날씨 | 최캐스터 | ANC>CUT>CHROMA | 2:00 | 42:00 | - | 녹화완료 |
| 23 | CLO | 클로징 | A1/A2 | ANC>TITLE | 0:30 | 42:30 | - | READY |

---

## 6. 시스템 구현 시 고려사항 (OnAir Connect 연동 관점)

1. **형식 = 프리셋, 아이템 = 인스턴스**: 형식 코드를 고르면 시퀀스/자막 슬롯이 자동 생성되고, 개별 story에서 수정하는 구조 (§4.7 템플릿).
2. **길이 버퍼 관리**: `ncsCuttable` 플래그가 있는 단신을 시스템이 인식해, 방송 중 시간 초과 시 "삭제 후보 문단"을 즉시 제안. MOS 표준 필드가 아니므로 반드시 `mosPayload` 안에서 관리.
3. **실시간 재배열**: 특보(§3.7) 대응 시 아이템 재배열·삽입·드롭은 표준 `roElementAction`으로 처리하고(삭제 후 재삽입 금지, §4.4 참고), 누계 시간은 로컬에서 자동 재계산.
4. **vMix 매핑**: 시퀀스 요소(§1.1)를 vMix 입력/오버레이에 매핑하는 테이블을 별도 관리 — 예: `SPLIT-A` → vMix Multi View 프리셋, `T-BOK` → GT Title 입력, `PKG` → 서버 클립 재생 입력. 이 매핑 테이블은 MOS 메시지가 아니라 우리 자동화 서버 내부 설정.
5. **자막 슬롯 사전 등록**: story별 `ncsCgList`를 큐시트 단계에서 등록해두면, 방송 시 오퍼레이터는 순서대로 호출만 하면 되는 구조.
6. **MOS 프로토콜 정합성**: 자체 필드(`format`, `cgList`, `cuttable` 등)는 표준 MOS 엘리먼트가 아니므로 전부 `mosExternalMetadata`(§4.3)로 격리하고, 순서·상태·재생 트리거는 표준 메시지(`roElementAction`, `roElementStat`, `roItemCue`)만 사용한다. 이래야 iNEWS/ENPS/Octopus/Dalet 등 서로 다른 NRCS와도 표준 파서 레벨에서 호환된다.
7. **동기화 깨짐 대응**: 자동화 시스템에서 사용자가 로컬로 순서를 강제 조작한 경우 `DISCONNECTED` 상태를 명시적으로 다루고, `roReq`/`roList`로 즉시 재동기화하는 로직을 필수 구현 항목으로 둔다(§4.5).
8. **Profile 5 연동이 핵심 종속성**: vMix 자동 트리거 기능은 `roItemCue`/`roCtrl`(Profile 5) 지원 없이는 "지금 이 아이템이 온에어되었다"는 신호를 받을 방법이 없다. 연동 대상 NRCS가 Profile 5를 지원하는지 초기 검토 단계에서 반드시 확인.

---

## 부록. 형식 코드 요약표

| 코드 | 형식 | 오디오 주체 | 방송 중 길이조절 | 핵심 특징 |
|---|---|---|---|---|
| RPT | 리포트 | 기자(녹음) | 불가 | 완제 패키지 |
| STR | 단신 | 앵커(생) | **가능(문단 삭제)** | 복대 자막, 시간 버퍼 |
| LIV | 중계차 | 기자(현장 생) | 부분 가능 | 갈라치기 x 질문 수, 반제 |
| GST | 출연 | 출연자(생/녹화) | 부분 가능 | 풀샷/서버 갈라치기 교차 |
| WEA | 날씨 | 캐스터 | 불가(녹화)/가능(생) | 크로마키, 특보 시 생방송 |
| SPO | 스포츠 | 전담 앵커 | 코너 단위 | 코너형/독립형 |
| HED | 헤드라인 | 앵커/성우 | 아이템 수 조절 | 대형 자막 |
| ANC-O | 앵커 단독 | 앵커 | 가능 | 영상 없음 |
| BRG | 브릿지 | 음악 | 불가 | 코너 전환 |
| CGN | 그래픽 뉴스 | 앵커 | 가능 | 전면 CG |
| QNA | 일문일답 | 인터뷰이(녹화) | 불가 | 인터뷰 자막 상시 |
| SKT | 스케치 | 현장음 중심 | 불가 | 르포형 |
| BRK | 특보 | 혼합 | 실시간 재배열 | 형식 조합 |
| CLO | 클로징 | 앵커 | 가능 | 엔딩 |

---

## 참고

- MOS Protocol 명세(엘리먼트 정의, roCreate/story/item 구조, roElementAction, mosExternalMetadata 등): mosprotocol.com 공식 문서(버전 2.6~4.0)
- 실제 연동 시 대상 NRCS(iNEWS, ENPS, Octopus, Dalet 등)의 벤더별 구현 편차(특히 상태 코드, Profile 지원 범위)는 반드시 별도 확인 필요 — 이 문서의 §4는 MOS 표준 스펙 기준이며 벤더 확장은 포함하지 않음.
