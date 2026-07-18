# Integration_Guide.md — 마스터 장비 연동 단계별 가이드

**버전**: v1.0
**연관 문서**: Expansion_PRD.md
**적용 범위**: Blackmagic Videohub → VMU → AMU 순차 연동

이 문서는 PRD의 아키텍처를 실제로 구현하는 **작업 순서서**입니다. 각 단계는 "완료 조건"을 만족해야 다음 단계로 넘어갑니다.

---

# PART A. 공통 준비 (반나절)

## Step A-1. 네트워크·장비 정보 정리

작업 전 아래 표를 채워 `devices.json`의 초안으로 삼는다.

| 항목 | 예시 | 실제 값 |
|---|---|---|
| Videohub IP | 192.0.2.4 | |
| Videohub 모델/입출력 수 | Smart Videohub 20x20 | |
| 마스터 실행 PC IP | 192.0.2.5 | |
| 방송망 VLAN/서브넷 | 192.0.2.6/24 | |
| VMU 모델/프로토콜 | (Phase 2에서 확정) | |
| AMU 모델/프로토콜 | (Phase 2에서 확정) | |

**완료 조건**: 마스터 PC에서 `ping <Videohub IP>` 응답 확인.

## Step A-2. 수동 프로토콜 테스트 (코드 작성 전 필수)

코드를 한 줄도 쓰기 전에, 터미널로 프로토콜을 직접 눈으로 확인한다. 이 덤프가 이후 파서 테스트의 픽스처(고정 테스트 데이터)가 된다.

```bash
# 1) 프리앰블 캡처 (연결하면 장비가 먼저 말한다)
nc 192.0.2.4 9990 | tee videohub_preamble.txt
# 몇 초 후 Ctrl+C

# 2) 전환 명령 테스트 — 출력 0번에 입력 1번 연결 (0-base 주의)
#    빈 줄(엔터 두 번)이 명령 블록의 끝이다
printf 'VIDEO OUTPUT ROUTING:\n0 1\n\n' | nc 192.0.2.4 9990
```

프리앰블에서 확인할 것:
- `PROTOCOL PREAMBLE:` 블록의 `Version:` 값
- `VIDEOHUB DEVICE:` 블록의 입출력 수
- `INPUT LABELS:` / `OUTPUT LABELS:` — 라벨에 공백/한글이 있는지
- `VIDEO OUTPUT ROUTING:` — 현재 크로스포인트 전체

**완료 조건**: 위 `printf` 명령으로 실제 라우터의 크로스포인트가 바뀌고, 응답으로 `ACK`가 수신됨. `videohub_preamble.txt` 파일이 프로젝트의 `test/fixtures/`에 저장됨.

## Step A-3. 프로젝트 골격 생성

마스터 저장소에 다음 구조를 만든다 (기존 코드는 건드리지 않는다).

```
src/devices/
├── core/
│   ├── types.ts            # DeviceDriver 인터페이스, 액션/상태 타입
│   ├── DeviceManager.ts    # 등록·연결·재연결·이벤트 허브
│   └── ActionExecutor.ts   # 큐시트 행 → 드라이버 호출
├── drivers/
│   ├── videohub/
│   │   ├── VideohubDriver.ts
│   │   ├── protocol.ts     # 블록 파서/직렬화 (순수 함수, 소켓 무관)
│   │   └── protocol.test.ts
│   ├── vmu/                # Phase 2
│   └── amu/                # Phase 2
└── devices.json            # 장비 설정
```

`devices.json` 초안:

```json
{
  "devices": [
    {
      "id": "main_router",
      "type": "videohub",
      "label": "메인 비디오 라우터",
      "host": "192.0.2.4",
      "port": 9990,
      "enabled": true
    }
  ]
}
```

**완료 조건**: `types.ts`에 PRD 4절의 `DeviceDriver` 인터페이스가 정의되고 빌드가 통과함.

---

# PART B. Blackmagic Videohub 연동 (Phase 1)

## Step B-1. 프로토콜 파서 구현 (소켓 없이)

핵심 원칙: **파서는 순수 함수로, 소켓과 분리해서 먼저 완성한다.** TCP 스트림은 패킷 경계가 보장되지 않으므로 "빈 줄로 끝나는 블록" 단위 버퍼링이 필수다.

```typescript
// src/devices/drivers/videohub/protocol.ts

/** 스트림 청크를 누적해 완성된 블록 단위로 잘라내는 버퍼 */
export class BlockBuffer {
  private buf = '';

  /** 수신 청크를 넣고, 완성된 블록(빈 줄로 종료)들을 반환 */
  push(chunk: string): string[] {
    this.buf += chunk;
    const blocks: string[] = [];
    let idx: number;
    // 블록 구분자: \n\n (CRLF 장비 대비 \r 제거)
    while ((idx = this.buf.indexOf('\n\n')) !== -1) {
      blocks.push(this.buf.slice(0, idx).replace(/\r/g, ''));
      this.buf = this.buf.slice(idx + 2);
    }
    return blocks;
  }
}

export interface ParsedBlock {
  header: string;               // 예: 'VIDEO OUTPUT ROUTING'
  lines: string[];              // 헤더 이후의 데이터 행들
}

export function parseBlock(raw: string): ParsedBlock {
  const lines = raw.split('\n').filter(l => l.length > 0);
  const header = lines[0].replace(/:$/, '');
  return { header, lines: lines.slice(1) };
}

/** 'INPUT LABELS' 행 파싱: "3 CAM 4 무선" → { index: 3, label: 'CAM 4 무선' } */
export function parseLabelLine(line: string) {
  const sp = line.indexOf(' ');
  return { index: Number(line.slice(0, sp)), label: line.slice(sp + 1) };
}

/** 'VIDEO OUTPUT ROUTING' 행 파싱: "5 2" → 출력 5 ← 입력 2 */
export function parseRouteLine(line: string) {
  const [output, input] = line.split(' ').map(Number);
  return { output, input };
}

/** 전환 명령 직렬화 */
export function buildRouteCommand(routes: { output: number; input: number }[]) {
  return 'VIDEO OUTPUT ROUTING:\n'
    + routes.map(r => `${r.output} ${r.input}`).join('\n')
    + '\n\n';
}
```

파서 테스트 — **Step A-2에서 캡처한 실제 덤프를 그대로 사용**하고, 반드시 "쪼개진 수신" 케이스를 포함한다:

```typescript
// protocol.test.ts 핵심 케이스
it('패킷이 임의 위치에서 쪼개져도 블록을 복원한다', () => {
  const dump = fs.readFileSync('test/fixtures/videohub_preamble.txt', 'utf8');
  const buf = new BlockBuffer();
  const blocks: string[] = [];
  // 7바이트씩 잘라 넣어 스트림 분할을 시뮬레이션
  for (let i = 0; i < dump.length; i += 7) {
    blocks.push(...buf.push(dump.slice(i, i + 7)));
  }
  expect(blocks.some(b => b.startsWith('VIDEO OUTPUT ROUTING'))).toBe(true);
});

it('라벨에 공백/한글이 있어도 파싱된다', () => {
  expect(parseLabelLine('3 CAM 4 무선')).toEqual({ index: 3, label: 'CAM 4 무선' });
});
```

**완료 조건**: 실장비 덤프 픽스처로 파서 테스트 전부 통과. 분할 수신 케이스 포함.

## Step B-2. 드라이버 구현 (연결·명령·상태)

```typescript
// src/devices/drivers/videohub/VideohubDriver.ts (핵심 흐름 요약)
import net from 'node:net';

export class VideohubDriver implements DeviceDriver {
  readonly capabilities = ['video_route'];
  status: DriverStatus = 'disconnected';

  private socket?: net.Socket;
  private buffer = new BlockBuffer();
  private state = {
    inputLabels: new Map<number, string>(),
    outputLabels: new Map<number, string>(),
    routing: new Map<number, number>(),   // output → input
  };
  private pending: Array<{ resolve: Function; reject: Function; timer: NodeJS.Timeout }> = [];
  private backoffMs = 1000;

  async connect() {
    this.status = 'connecting';
    this.socket = net.connect(this.cfg.port, this.cfg.host);
    this.socket.setNoDelay(true);                 // 지연 최소화 (Nagle off)
    this.socket.setEncoding('utf8');

    this.socket.on('data', chunk => {
      for (const raw of this.buffer.push(chunk as string)) this.handleBlock(raw);
    });
    this.socket.on('close', () => this.scheduleReconnect());
    this.socket.on('error', () => { /* close가 이어서 발생 → 거기서 처리 */ });
  }

  private handleBlock(raw: string) {
    // ACK/NAK는 헤더 없는 단일 행 블록
    if (raw === 'ACK') return this.resolvePending(true);
    if (raw === 'NAK') return this.resolvePending(false);

    const block = parseBlock(raw);
    switch (block.header) {
      case 'INPUT LABELS':
        for (const l of block.lines) {
          const { index, label } = parseLabelLine(l);
          this.state.inputLabels.set(index, label);
        }
        break;
      case 'OUTPUT LABELS':
        for (const l of block.lines) {
          const { index, label } = parseLabelLine(l);
          this.state.outputLabels.set(index, label);
        }
        break;
      case 'VIDEO OUTPUT ROUTING':
        for (const l of block.lines) {
          const { output, input } = parseRouteLine(l);
          this.state.routing.set(output, input);
        }
        // 프리앰블 수신 완료 판단: 최초 라우팅 블록 수신 시 connected 전환
        if (this.status !== 'connected') {
          this.status = 'connected';
          this.backoffMs = 1000;                  // 백오프 리셋
          this.emit('connected');
        }
        this.emit('stateChanged', this.getState());
        break;
      // 그 외 블록(PROTOCOL PREAMBLE, VIDEOHUB DEVICE 등)은 필요 시 파싱, 미지 블록은 무시
    }
  }

  async execute(action: DeviceAction): Promise<ActionResult> {
    if (action.action !== 'route') throw new Error(`지원하지 않는 액션: ${action.action}`);
    if (this.status !== 'connected') {
      // PRD VH-8: 오프라인 시 큐잉하지 않고 즉시 실패 반환
      return { ok: false, error: 'device_offline' };
    }
    const output = this.resolvePort(action.params.output, this.state.outputLabels);
    const input  = this.resolvePort(action.params.input,  this.state.inputLabels);

    const started = Date.now();
    await this.send(buildRouteCommand([{ output, input }]), action.options?.timeoutMs ?? 2000);
    return { ok: true, elapsedMs: Date.now() - started };
  }

  /** 라벨 문자열이면 포트 번호로 해석 (VH-5) */
  private resolvePort(v: number | string, labels: Map<number, string>): number {
    if (typeof v === 'number') return v;
    for (const [idx, label] of labels) if (label === v) return idx;
    throw new Error(`라벨을 찾을 수 없음: ${v}`);
  }

  /** 순서 보장: 이전 ACK 수신 후 다음 전송 (VH-7) — pending 큐로 직렬화 */
  private send(payload: string, timeoutMs: number): Promise<void> { /* ... */ }

  private scheduleReconnect() {
    this.status = 'reconnecting';
    this.emit('disconnected');
    this.rejectAllPending('connection_lost');
    setTimeout(() => this.connect(), this.backoffMs);
    this.backoffMs = Math.min(this.backoffMs * 2, 30_000);  // 1s→2s→4s…최대 30s
  }
}
```

구현 시 주의:
- **connected 판정**: 소켓 open이 아니라 **프리앰블(라우팅 테이블) 수신 완료** 시점으로 한다. 그래야 라벨 해석이 항상 안전하다.
- **하드웨어 패널 병행**: 다른 컨트롤러가 전환하면 장비가 변경 블록을 푸시한다 → `handleBlock`이 그대로 처리하므로 별도 폴링 불필요.
- **명령 직렬화**: ACK가 오기 전 다음 명령을 보내면 응답 매칭이 꼬인다. pending 큐로 한 번에 하나씩.

**완료 조건**: 실장비 대상 통합 테스트 통과 —
- [ ] 연결 시 라벨/라우팅 테이블이 상태에 정확히 로드
- [ ] `execute(route)` 로 실제 크로스포인트 전환 + ACK + 지연(ms) 로그
- [ ] 하드웨어 패널 전환 시 `stateChanged` 이벤트 발생
- [ ] LAN 분리 → `reconnecting` → 케이블 복구 → 30초 내 자동 복귀 + 상태 재동기화
- [ ] 오프라인 중 `execute` → 즉시 `device_offline` 실패 (지연 실행 없음)

## Step B-3. Device Manager 연결

```typescript
// 초기화 흐름
const manager = new DeviceManager();
manager.registerDriverType('videohub', cfg => new VideohubDriver(cfg));
await manager.loadConfig('devices.json');   // enabled=true 장비 자동 connect
manager.on('deviceStatusChanged', ({ id, status }) => ui.updateIndicator(id, status));
```

Device Manager의 책임 경계:
- 드라이버 예외를 **격리**한다 — 드라이버 하나가 throw해도 다른 장비·본체에 전파 금지 (try/catch + 로그)
- 장비별 상태를 모아 UI 상태등(UI-2)에 공급
- 종료 시 전체 `disconnect()` 정리

**완료 조건**: 마스터 실행 → 상태등에 `main_router` 녹색 표시. 라우터 전원 차단 시 적/황색 전환 및 복구 확인.

## Step B-4. 큐시트 액션 연동

1. 큐시트 스키마에 라우터 행 추가 (PRD 7.1). 마스 측 수정이 필요하면 이 시점에 협의.
2. `ActionExecutor`에 라우팅 분기 추가:

```typescript
async function runCueRow(row: CueRow) {
  const driver = manager.get(row.device);
  const result = await driver.execute(toDeviceAction(row));
  log.write({ row: row.no, device: row.device, ...result, at: Date.now() });

  if (!result.ok) {
    if (row.onFailure === 'pause_cuesheet') cuesheet.pause(row.no);
    else ui.warn(`행 ${row.no}: ${row.device} 실패(${result.error}) — 계속 진행`);
  }
}
```

3. 큐시트 로드 시 사전 검증(PRD 7.2): 장비 존재 → capability 매칭 → (연결 시) 라벨 존재 확인.

**완료 조건**: vMix 컷 + 라우터 전환이 섞인 테스트 큐시트 1편이 처음부터 끝까지 실행되고, 실행 로그에 각 행의 성공/소요시간이 남음.

## Step B-5. UI (매트릭스 뷰 + 비상 수동 조작)

- 상태등(B-3에서 완료) 다음으로 **라우팅 매트릭스 그리드**: 행=출력, 열=입력, 현재 크로스포인트 하이라이트. `stateChanged` 이벤트로 실시간 갱신.
- 셀 클릭 = 수동 전환(비상용). 방송 중 오조작 방지를 위해 "확인" 1단계 또는 잠금 토글을 둔다.

**완료 조건**: 하드웨어 패널로 전환해도 그리드가 1초 내 반영. 그리드 클릭으로 전환 가능.

## Step B-6. 리허설 및 Phase 1 종료 게이트

- 실제 방송 포맷 큐시트(오프닝→본방송→CM→클로징)로 통합 리허설
- 방송 중 라우터 재부팅 시나리오: 송출(vMix) 무중단 + 라우터 자동 복귀 확인
- 실행 로그 파일이 방송 1회분으로 저장되는지 확인

이 게이트를 통과해야 Phase 2 착수.

---

# PART C. VMU / AMU 연동 (Phase 2)

VMU/AMU는 모델별 프로토콜 차이가 크므로, 아래 단계는 **조사 → 어댑터 설계 → 구현** 순서를 강제한다.

## Step C-1. 프로토콜 조사서 작성 (구현 금지 구간)

장비별로 아래 조사서를 채운다. **이 표가 완성되기 전에는 코드를 쓰지 않는다.**

| 조사 항목 | VMU | AMU |
|---|---|---|
| 제조사/모델 | | |
| 프로토콜 문서 확보 여부 (매뉴얼 부록/제조사 요청) | | |
| 전송 계층: TCP / UDP / RS-422·485 / SNMP | | |
| 포트/보레이트 | | |
| 명령 형식: 텍스트 / 바이너리(체크섬 유무) | | |
| 크로스포인트 명령 예시 | | |
| ACK/NAK 응답 유무 | | |
| 상태 푸시 지원 여부 (없으면 폴링 명령은?) | | |
| 라벨 조회 명령 유무 | | |
| 오디오(AMU): 채널 단위 vs 스테레오 페어, 레벨/뮤트 포함? | | |
| 동시 접속 제한 (하드웨어 패널 병행 가능?) | | |

**완료 조건**: 두 장비 모두 Step A-2와 동일한 **수동 터미널 테스트**로 전환 1회 성공 + 응답 캡처 픽스처 저장.
(시리얼 장비면 USB-시리얼 어댑터 + `screen`/`minicom`으로 동일하게 캡처)

## Step C-2. 전송 계층 결정

| 상황 | 선택 |
|---|---|
| TCP 지원 | 드라이버가 직접 TCP 연결 (Videohub와 동일 패턴) |
| 시리얼 전용 + 마스터가 데스크톱(Node) | Node `serialport` 패키지로 직접 연결 |
| 시리얼 전용 + 마스터가 웹 기반 | **시리얼-TCP 게이트웨이**(디바이스 서버 하드웨어 또는 로컬 에이전트) 경유 — OnAir Connect의 로컬 에이전트 패턴 재사용 |

**완료 조건**: 결정 내용과 근거를 조사서에 1줄 기록.

## Step C-3. 드라이버 구현 — Videohub 패턴 복제

새 드라이버는 Videohub 드라이버의 구조를 그대로 따르되, 다음만 교체한다:

1. `protocol.ts` — 해당 장비의 명령 직렬화/응답 파싱 (픽스처 테스트 필수)
2. `capabilities` — VMU: `['video_route']`, AMU: `['audio_route']` (+ 지원 시 `audio_mute`, `audio_level`)
3. **상태 동기화 방식**:

```typescript
// 상태 푸시가 없는 장비: 드라이버 내부 폴링 → 외부에는 동일한 이벤트로 노출
private startPolling() {
  this.pollTimer = setInterval(async () => {
    const routing = await this.queryRouting();       // 장비별 상태 조회 명령
    if (!isEqual(routing, this.state.routing)) {
      this.state.routing = routing;
      this.emit('stateChanged', this.getState());    // 마스터 본체는 푸시/폴링 차이를 모름
    }
  }, 2000);
}
```

4. AMU 액션 스키마는 공통 스키마에 `domain: "audio"`만 다르게:

```json
{ "device": "amu_1", "action": "route",
  "params": { "domain": "audio", "output": "PGM L/R", "input": "MIC 3" } }
```

바이너리 프로토콜인 경우 추가 규칙:
- `BlockBuffer` 대신 **길이 필드/구분 바이트 기반 프레이머**를 구현하고, 체크섬 검증 실패 프레임은 버리고 로그
- 픽스처는 hex 덤프로 저장 (`xxd` 활용)

**완료 조건**: Step B-2와 동일한 통합 테스트 체크리스트를 장비별로 통과 (연결/전환/재연결/오프라인 즉시 실패/패널 병행 동기화).

## Step C-4. 큐시트·검증·UI 확장

- 큐시트 사전 검증에 `domain` ↔ capability 매칭 추가 (AMU 행에 video 라벨을 쓰면 로드 시 경고)
- 매트릭스 뷰를 장비 탭으로 분리: `메인 라우터 | VMU | AMU`
- AMU가 뮤트/레벨을 지원하면 큐시트 액션 `audio_mute`, `audio_level` 추가 — 단, **레벨은 큐시트 자동 실행보다 수동 조작 우선** 검토 (방송 중 자동 레벨 변경은 사고 위험)

**완료 조건**: 3개 장비(라우터+VMU+AMU) 혼합 큐시트 리허설 통과.

## Step C-5. 매크로(살보) 기능

"CM 진입" 하나의 큐로 여러 장비를 동시 제어:

```json
{
  "macro": "CM_진입",
  "steps": [
    { "device": "vmix_main",  "action": "cut",   "params": { "input": "CM_ROLL" } },
    { "device": "main_router","action": "route", "params": { "output": "MON 1", "input": "CM SRC" }, "delayMs": 0 },
    { "device": "amu_1",      "action": "route", "params": { "domain": "audio", "output": "PGM L/R", "input": "CM AUD" }, "delayMs": 200 }
  ]
}
```

- 기본 병렬 실행, `delayMs`로 순차 지정
- 매크로 정의 위치(마스 vs 마스터)는 PRD 오픈 이슈 3번 — 이 단계 착수 전 결정

---

# PART D. 운영 전환 체크리스트

방송 투입 전 최종 점검:

- [ ] 장비망 격리: Videohub/VMU/AMU는 무인증 프로토콜 → 방송 VLAN 외부 접근 방화벽 차단 확인
- [ ] `devices.json` 백업 및 IP 고정(DHCP 예약 또는 정적 IP)
- [ ] 방송 전 자동 점검 루틴: 전 장비 연결 + 큐시트 검증 통과를 "온에어 준비 완료" 조건으로
- [ ] 실행 로그 보존 경로/용량 확인
- [ ] 운영 수칙 문서화: 하드웨어 패널과 마스터 동시 조작 시 우선순위 규칙
- [ ] 장애 대응 카드: "라우터 끊김 → 상태등 확인 → 하드웨어 패널로 수동 전환 → 방송 유지" 절차 1페이지

---

# 부록. 자주 발생하는 문제

| 증상 | 원인 | 조치 |
|---|---|---|
| 연결은 되는데 명령 무반응 | 명령 블록 끝 빈 줄(`\n\n`) 누락 | `buildRouteCommand` 직렬화 확인 |
| 간헐적 파싱 오류 | 패킷 분할 미처리 | `BlockBuffer` 경유 여부 확인, 분할 수신 테스트 재실행 |
| 라벨 해석 실패 | 프리앰블 수신 전 `connected` 판정 | connected 시점 = 라우팅 블록 수신 완료로 수정 |
| 첫 전환만 되고 이후 무시 | ACK 대기 없이 연속 전송 | pending 큐 직렬화 확인 |
| 재연결 후 상태 불일치 | 재연결 시 상태 초기화 누락 | connect() 진입 시 state Map clear 후 프리앰블로 재구성 |
| NAK 반복 | 포트 번호 1-base 착각 | Videohub는 **0-base** — 큐시트 입력 규칙 통일 |
