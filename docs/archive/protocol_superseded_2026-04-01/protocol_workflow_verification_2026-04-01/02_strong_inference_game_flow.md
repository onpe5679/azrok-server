# Azrok Strong-Inference Game Flow

Date: 2026-04-01
Goal: strongest defensible gameplay-flow model from current evidence

## 1. Top-level game phases

### Phase A: launcher and connection setup

Best-supported path:

1. launcher or injected WDL variables provide `IP:PORT`, username, authkey
2. client connects normally
3. `CClientPeer::OnConnect` sets the dispatch/send gate
4. client emits `C->S 0x0000`

This phase is already well supported by:

- [22_launcher_and_connection_architecture.md](<home>/Documents/<project-dir>/Azrok_Plaza/docs/research/22_launcher_and_connection_architecture.md)
- binary connection-chain work already reflected in local docs

### Phase B: login sparse-cache and initial mode selection

Strongest inference:

1. server returns `S->C 0x0000` sparse-cache blob
2. `lobby_mode` chooses the first logical local branch
3. client enters lobby or pet pre-room state

This phase uses:

- `HandleS2C_0000_LoadLobbySparseCache`
- `HandleS2C_0000_SelectLobbyEntryScene`

### Phase C: room-entry arming

Strongest inference:

1. server sends `S->C 0x0003` with space-root path
2. server sends `S->C 0x0007` full setup blob
3. server follows with `S->C 0x0005`, `0x000A`, `0x000B`
4. state-0 common handler enqueues the next room code

For PatHouse-style flow, this is the critical bootstrap.

### Phase D: room loading and room init

Strongest inference:

1. `GameManager_DispatchRoomCode` eventually reaches room code `0`
2. client loads `room.wmb`
3. room code `100` is then pushed
4. `GameManager_ExecuteRoomInit(100)` runs
5. scene mode becomes `2`

This is the first stable "room is up" state.

### Phase E: stable in-room loop

What the live log supports:

- ongoing `C->S 0x0016` heartbeat
- server `S->C 0x0016` heartbeat ack
- no required `0x0017`, `0x0008`, or `0x0064` in the currently reproduced minimal room flow
- repeated `C->S 0x000C` as the first real post-entry gameplay candidate

### Phase F: extended world-sync / state-1

Strongest inference:

- this phase begins only after `S->C 0x0064` or another state-1 boundary is safely introduced
- it covers:
  - authoritative self placement
  - remote actor roster
  - actor motion/state/text

Packets that belong here:

- `0x0064`
- `0x0065`
- `0x0066`
- `0x0067`
- `0x0068`
- `0x0069`
- `0x006A`
- `0x006B`
- `0x006C`
- `0x006D`
- `0x006E`
- `0x006F`
- `0x0070`
- `0x0071`

## 2. Strongest inference for PatHouse gameplay flow

### Minimal currently observed-playable flow

```text
connect
-> C->S 0x0000
-> heartbeat loop begins
-> S->C 0x0000 sparse cache
-> S->C 0x0003 path
-> S->C 0x0007 setup blob
-> S->C 0x0005 post-load state
-> S->C 0x000A stat registry
-> S->C 0x000B xp curve
-> client enters room.wmb / room-init flow
-> stable room
-> repeated C->S 0x000C begins
```

What is intentionally absent from this minimal currently observed-playable flow:

- `S->C 0x0002`
- `S->C 0x0064`
- required `C->S 0x0017`
- required `C->S 0x0008`

### Stronger binary-faithful target flow

```text
connect
-> C->S 0x0000
-> S->C 0x0000 sparse cache
-> S->C 0x0004(sample_kind=1, timestamp) x5
-> fifth sample mutates to 0xFF inside client
-> readiness latch set
-> S->C 0x0003
-> S->C 0x0007
-> S->C 0x0005
-> S->C 0x000A
-> S->C 0x000B
-> room.wmb
-> room init 100
-> stable room
```

This second lane is more binary-faithful, but the live log does not prove that all of it is strictly required for PatHouse first playability.

## 3. Strongest inference for "normal gameplay next"

Current evidence says the next likely gameplay verb is not `0x0017`.

It is:

- `C->S 0x000C`

Reason:

- repeated in the only currently reproduced live playable session
- appears only after the room is stable
- not answered by the current server
- no other post-entry client gameplay opcode repeats in the same session

Strong inference:

- `0x000C` is likely a self/actor slot/value update, interaction state, or local action report that the real server would either acknowledge or reflect back as `S->C 0x000C`/state updates

## 4. Strongest inference for Hansol / Plaza transition

What is strongly supported:

- `Plaza_TransitionFromRoom @ 0x00568770` enqueues room code `0x6E`
- the same function sets the Hansol flag (`gm+0x31C72 = 1`)
- it also resets the `0x0004` calibration state
- `GameManager_DispatchRoomCode case 0x0B` requires `gm+0x31C71 != 0` to load `hansol.wmb`

What is not yet closed:

- a fully packet-only way for the server to trigger the same Hansol flag path without any process-memory intervention

So the correct status is:

- outdoor / Hansol flow is partially modeled, not fully closed

## 5. Practical reading of the evidence

1. There are two distinct truths in the workspace right now:
   - the current local Python server can make PatHouse playable
   - the current local Python server is not yet fully packet-faithful
2. The minimum playable flow is narrower than older docs suggested.
3. The next realistic protocol frontier is post-entry interaction, centered on `C->S 0x000C`.
4. State-1 packets should be brought in later and deliberately, not mixed into the initial room bootstrap.
