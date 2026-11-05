# Azrok Server Protocol Workflow Draft

Date: 2026-04-01
Goal: draft the server-side communication workflow that best matches the current strongest evidence

## 1. 최소 안전 워크플로우

### Phase 1: connection / login

서버는 아래를 수행한다.

1. TCP 연결 수락
2. `C->S 0x0000` 수신
3. `S->C 0x0000` 전송

`S->C 0x0000` 최소 조건:

- `result_code = 0`
- `lobby_mode` 유효값
- blob shape `0x183 bytes`

### Phase 2: heartbeat

서버는 heartbeat를 유지한다.

- `C->S 0x0016` -> `S->C 0x0016`

`0x0004`는 두 레벨로 나눈다.

- `Observed-playable`
  - 현재는 사실상 optional
- `Binary-faithful target`
  - `S->C 0x0004(sample_kind=0x01, timestamp)` x5

### Phase 3: room bootstrap bundle

서버는 아래 순서로 보낸다.

1. `S->C 0x0003`
2. `S->C 0x0007`
3. `S->C 0x0005`
4. `S->C 0x000A`
5. `S->C 0x000B`

PatHouse용 `0x0003` 안전값:

```text
byte0 = 0x01
string = Data\\Space\\PatHouse\\0
```

`0x0007` 핵심 규칙:

- `+0x125..+0x12F` 비어 있으면 `0xFF`
- `+0x1D4..+0x1D7` clear는 `0xFF`, `0`은 유효 selector
- stat words `57..69`는 `0`

## 2. 서버 decision table

| Client packet | Server action | 현재 판단 |
| --- | --- | --- |
| `0x0000` | `S->C 0x0000` login blob | 확정 |
| `0x0016` | heartbeat ack 유지 | 확정 |
| first `0x0007` | bootstrap이 아직 안 됐으면 `0x0007 + 0x0005 + 0x000A + 0x000B` 1회 | 높음 |
| repeated `0x0007` | ignore | 확정에 가까움 |
| `0x0001` | ignore, no echo | 높음 |
| `0x000C` | log and decode, no blind echo | 최우선 미해결 |
| `0x0017` | 아직 bootstrap 필수로 가정하지 말 것 | 미해결 |
| `0x0064` | early response 금지 | 높음 |

## 3. 최소 workflow에서 제외할 것

아래는 **최소 bootstrap workflow에서 빼야 한다**.

- `S->C 0x0002`
- early `S->C 0x0064`
- `C->S 0x000C` blind echo
- `C->S 0x0017`을 필수 bootstrap trigger로 간주

이유:

- `0x0002`는 gate를 죽인다
- `0x0064`는 dispatch_state를 조기 승격시킨다
- `0x000C`는 의미가 아직 안 닫혔다
- `0x0017`은 이번 live session에서 아예 안 보였다

## 4. state-1 확장 workflow 초안

이건 minimum bootstrap 다음 단계다.

권장 순서:

1. `0x0065` remote roster flush
2. `0x0066` remote actor spawn
3. `0x0068` remote actor state batch
4. `0x0069` action/coord follow-up
5. `0x006E` ready commit
6. 필요 시 `0x006A`, `0x006B`, `0x006C`, `0x006D`, `0x006F`, `0x0070`, `0x0071`

`0x0064`는 여기보다도 앞에 넣지 않는다. 정말 self/world authoritative placement를 시작할 때만 쓴다.

## 5. Hansol / Plaza workflow 초안

현재 strongest-inference draft:

1. room mode `2` 상태
2. outdoor transition helper 발동
3. readiness latch 필요
4. hansol flag 필요
5. `hansol.wmb`
6. Hansol stage machine 진입
7. stage 0에서 local `C->S 0x0064`
8. 이후 state-1 world sync

현재 미해결:

- 위 3, 4를 **순수 packet-only**로 어떻게 자연스럽게 만드는지

## 6. 다음 reverse-engineering 목표

### 1순위

- `C->S 0x000C`
  - field meaning
  - producer path
  - 서버 응답 형식

### 2순위

- Hansol/Plaza packet-only 자연 전환

### 3순위

- `C->S 0x0017`
  - producer
  - strict consumer

### 4순위

- `C->S 0x0064`
  - full serialized layout

## 7. 이 초안의 최종 해석

현재 서버 설계는 두 층으로 생각하는 게 맞다.

```text
Layer 1: packet-only PatHouse bootstrap
Layer 2: post-entry gameplay contract recovery
```

Layer 1은 많이 닫혔고, Layer 2의 첫 관문이 `0x000C`다.
