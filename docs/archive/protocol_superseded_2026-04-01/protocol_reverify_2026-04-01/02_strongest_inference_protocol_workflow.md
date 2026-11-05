# Strongest-Inference Gameplay Flow And Protocol Workflow Draft

Date: 2026-04-01
Goal: draft the server-side communication workflow that best matches the re-verified binary state machine

## 1. Workflow A: initial packet-only PatHouse bootstrap

This is the strongest current draft for "packet-only and actually progresses".

### Phase A: connection and login shell

1. Accept TCP connection.
2. Receive `C->S 0x0000`.
3. Reply with `S->C 0x0000` login blob.

Required fields in `S->C 0x0000`:

- `result_code = 0`
- `lobby_mode = 0 or 1`
- valid `0x183`-byte blob shape

Effect:

- client enters pet/lobby shell path first

### Phase B: heartbeat maintenance

1. Continue heartbeat exchange with `0x0016`.
2. Do not rely on `0x0004` as the first-room hard gate.

Pragmatic recommendation:

- keep heartbeat alive
- if you want strict calibration fidelity, use the true `0x0004` sample form:
  - `payload[0] = 0x01`
  - `payload[1..4] = timestamp`
  - 5 samples
- but for initial PatHouse bring-up, `0x0004` is lower priority than `0x0003/0x0007`

### Phase C: room bootstrap bundle

Send, in this order:

1. `S->C 0x0003`
2. `S->C 0x0007`
3. `S->C 0x0005`
4. `S->C 0x000A`
5. `S->C 0x000B`

Why this order:

- `0x0003` stores the space root first
- `0x0007` imports setup state and enqueues default room `100`
- `0x0005` updates post-load state dword
- `0x000A/0x000B` fill registry/curve state before gameplay continues

### Phase D: client follow-up handling

Observed current session behavior:

- client sends repeated `C->S 0x0007`
- later sends repeated `C->S 0x000C`

Server rules:

- first `C->S 0x0007` after bootstrap:
  - if you did not already send the room bundle, send it once
- repeated `C->S 0x0007`:
  - ignore
- `C->S 0x0001`:
  - do not echo
- `C->S 0x000C`:
  - log and study
  - do not blind-echo

### Phase E: state-1 boundary

Do not send `S->C 0x0064` during the above phases.

Reason:

- `0x0064` immediately flips `dispatch_state = 1`
- that can cut off still-needed state-0 post-load processing

## 2. Workflow B: later state-1 world sync

This is not required for first PatHouse entry, but it is the likely server contract for fuller gameplay.

### Minimal safe ordering

1. `0x0065` remote roster flush
2. `0x0066` remote actor spawn records
3. `0x0068` remote actor state records
4. `0x0069` action or coordinate follow-up
5. `0x006E` ready/mode commit
6. optional `0x006A`, `0x006B`, `0x006C`, `0x006D`, `0x006F`, `0x0070`, `0x0071`

Reasoning:

- `0x0065/0x0066` establish actor list
- `0x0068/0x0069` move/update actors
- `0x006E` commits ready state and marks internal ready byte

### `0x0064` usage rule

Use `0x0064` only when both are true:

- the client has finished the relevant state-0 room init
- you intentionally want to promote the client into state-1 self/world handling

## 3. Workflow C: strongest-inference Hansol/Plaza transition draft

This path is only partially closed. The draft below is the best current inference, not a fully proven recipe.

### Binary facts to honor

- readiness latch lives at `gm+0x31C71`
- hansol flag lives at `gm+0x31C72`
- room code `0x0B` loads `hansol.wmb` only if readiness latch is set
- room code `0x6E` runs Hansol scene init
- Hansol stage 0 emits local `C->S 0x0064`

### Strongest-inference workflow draft

1. From room mode `2`, client triggers outdoor transition logic.
2. Server or legitimate packet path must ensure:
   - readiness latch path has completed
   - hansol flag path has been set
3. Client enters hansol load path.
4. Hansol stage machine begins.
5. Stage 0 emits `C->S 0x0064`.
6. Only after that should the server consider authoritative state-1 self/world responses.

### What is still missing

- exact packet-only method that naturally sets `gm+0x31C72`
- exact server response contract for the post-Hansol local `C->S 0x0064`

## 4. Packet classes by certainty

### High-confidence required for initial progress

- `0x0000`
- `0x0003`
- `0x0007`

### High-confidence required for stable bootstrap fidelity

- `0x0005`
- `0x000A`
- `0x000B`

### High-confidence dangerous if mistimed

- `0x0002`
- `0x0064`

### High-confidence important, but mostly for outdoor/later flow

- `0x0004`
- `0x0065..0x0071`

### Highest-priority unresolved gameplay verb

- `C->S 0x000C`

## 5. Draft server decision table

| Client packet | Server action | Confidence |
| --- | --- | --- |
| `0x0000` | send `0x0000` login blob | high |
| `0x0016` | keep heartbeat alive; optional true `0x0004` calibration | medium |
| first `0x0007` | if room bootstrap not yet completed, send `0x0007 + 0x0005 + 0x000A + 0x000B` once | high |
| repeated `0x0007` | ignore | high |
| `0x0001` | ignore, do not echo | high |
| `0x000C` | log, decode, do not blind-echo | high |
| post-Hansol `0x0064` | likely state-1 self/world response point, but contract still incomplete | medium-low |

## 6. Practical implementation guidance

If the immediate goal is "packet-only normal entry plus maximum safety", the server should be built in layers.

Layer 1:

- login blob
- heartbeat
- `0x0003/0x0007/0x0005/0x000A/0x000B`

Layer 2:

- strict `0x0004` calibration
- outdoor readiness

Layer 3:

- `0x000C` response contract
- state-1 actor/world sync

That ordering matches the binary better than trying to force `0x0064` or `0x0002` early.
