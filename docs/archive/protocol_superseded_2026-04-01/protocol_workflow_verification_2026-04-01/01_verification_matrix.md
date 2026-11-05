# Azrok Verification Matrix

Date: 2026-04-01
Scope: binary re-verification, local docs cross-check, live packet-log cross-check

## 1. What the binary definitely supports

### Inbound dispatcher shape

`DispatchInbound_ByClientMode @ 0x00594310`

Verified behavior:

- logs every inbound packet first
- special-cases `0x0005` before mode dispatch
- special-cases `0x0064` by forcing `dispatch_state = 1` before the state-1 handler
- if `dispatch_state == 0`, calls:
  - `DispatchState0Specific_S2C @ 0x0059DD20`
  - then `DispatchState0Common_S2C @ 0x0050CBC0`
- if `dispatch_state == 1`, calls `DispatchState1_S2C @ 0x00613740`

Implication:

- `S->C 0x0064` is a state boundary, not just a self-spawn packet
- `S->C 0x0005` has two layers of meaning because it is processed before mode dispatch and again inside state-0 common

### Login / bootstrap packets

Binary-supported facts:

- `S->C 0x0000` is a real `0x183`-byte login/lobby sparse-cache blob
- `S->C 0x0003` stores `payload[0]` into `gm+0x31C63` and forwards `payload+1` as a path/state string
- `S->C 0x0007` imports the setup blob and its common handler enqueues the next room/state request
- `S->C 0x000A` and `S->C 0x000B` are the real grouped stat registry / XP curve packets

### Dangerous packets

Binary-supported facts:

- `S->C 0x0002` makes `DispatchState0Common_S2C` write `gm+0x31946 = 0`
- `GameManager_PerFrameUpdate @ 0x00509200` only dispatches room codes while `gm+0x31946 != 0`
- `HandleS2C_0002_TransitionPrimary @ 0x0059D150` also causes a client outbound `0x0007` through `FUN_005A4770`

Implication:

- `0x0002` is never a harmless filler

### `0x0004` readiness path

Binary-supported facts:

- `DispatchState0Specific_S2C @ 0x0059DD20` only feeds `0x0004` into `HandleS2C_0004_CalibrationSample @ 0x0059DE50` when `payload[0] == 0x01`
- that handler accumulates 5 samples
- on the fifth sample it mutates the same receive buffer to `payload[0] = 0xFF`
- `DispatchState0Common_S2C` only performs the readiness-latch action when it sees `0xFF`

Implication:

- a packet-faithful readiness path is `0x0004(sample_kind=1, timestamp)` repeated 5 times
- the older `0x00 + timestamp` interpretation is not supported by the binary

### Room-code flow

`GameManager_DispatchRoomCode @ 0x0050A0F0`

Verified cases:

- code `8` -> `lobby.wmb` -> later mode `1`
- code `9` -> `pet.wmb` -> later mode `0`
- code `0` -> `room.wmb` -> later pushes code `100`
- code `100` -> room init, later mode `2`
- code `0x0B` -> `hansol.wmb` only if `gm+0x31C71 != 0`
- code `0x6E` -> Hansol init, later mode `4`

Implication:

- PatHouse-style playable flow is a state-0 bootstrap into room code `0`, then `100`
- Hansol / Plaza flow depends on the readiness machinery, not a separate isolated branch

## 2. What the current live packet log supports

Current live capture: [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt)

Observed `C->S` opcodes in this session:

- `0x0000` x1
- `0x0016` x40
- `0x0007` x3
- `0x000C` x3

Not observed in this session:

- `0x0001`
- `0x0004`
- `0x0008`
- `0x0017`
- `0x0019`
- `0x0064`

Observed high-level sequence:

```text
C->S 0x0000
C->S 0x0016 heartbeat
S->C 0x0016
S->C 0x0004
S->C 0x0000
... repeated heartbeats ...
S->C 0x0003
S->C 0x0007
S->C 0x0005
S->C 0x000A
S->C 0x000B
C->S 0x0007
S->C 0x0007
S->C 0x0005
S->C 0x000A
S->C 0x000B
... later repeated C->S 0x0007 ignored ...
... later C->S 0x000C appears with no S->C response ...
```

Important implication:

- the currently reproduced playable flow does **not** require `0x0001`, `0x0008`, or `0x0017`
- the only repeatedly observed post-entry gameplay candidate in the current live session is `C->S 0x000C`

## 3. Contradictions that remain

### Contradiction A: old docs vs binary on `0x0004`

Conflict:

- [00_current_status.md](<home>/Documents/<project-dir>/Azrok_Plaza/docs/research/00_current_status.md) still describes `S->C 0x0004` as ``0x00 + u32 timestamp``
- binary dispatch requires `payload[0] == 0x01` for the sample path

Resolution:

- treat the old `0x00` interpretation as disproven
- keep `0x0004` in the packet-faithful workflow only as the `0x01 x5` path

### Contradiction B: old docs vs current live log on required C->S follow-ups

Conflict:

- older docs mention `C->S 0x0001`, `0x0008`, `0x0017`
- current live log does not show them

Resolution:

- do not put `0x0001`, `0x0008`, `0x0017` into the minimum required workflow
- keep them in the extended candidate workflow only

### Contradiction C: current local server vs binary-faithful contract

Conflict:

- current server still emits `S->C 0x0004` with byte `0x00`
- current server also re-sends the full `0x0007 + 0x0005 + 0x000A + 0x000B` bundle once after the first client `0x0007`

Resolution:

- separate "currently observed-playable workflow" from "binary-faithful target workflow"
- do not assume the present Python server behavior is the same thing as protocol-faithful behavior

## 4. Strongest verification conclusions

1. The binary strongly supports `0x0000 -> 0x0003 -> 0x0007 -> 0x0005 -> 0x000A -> 0x000B` as the real state-0 room bootstrap axis.
2. The binary strongly rejects `0x0002` as a harmless login packet.
3. The binary strongly supports `0x0004(sample_kind=1) x5` as the real readiness path, but the current playable local run appears to succeed without needing that path faithfully reproduced.
4. The current live session narrows the next missing server contract to `C->S 0x000C`, not `0x0017`.
5. `S->C 0x0064` belongs in a later state-1 workflow, not in the minimum bootstrap workflow.
