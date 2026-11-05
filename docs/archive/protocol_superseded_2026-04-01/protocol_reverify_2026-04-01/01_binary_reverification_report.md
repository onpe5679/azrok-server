# Azrok Binary Reverification Report

Date: 2026-04-01
Target: `Azrok.exe` in Ghidra
Scope: login -> lobby/pet -> PatHouse/room -> Hansol/Plaza transitions, dispatch boundaries, and hard packet gates

## 1. Dispatcher structure is now re-verified

Primary inbound dispatcher:

- `DispatchInbound_ByClientMode @ 0x00594310`

Verified behavior:

- Logs every inbound packet first.
- Special-cases `opcode 0x0005` before mode dispatch by calling `HandleS2C_0005_PostLoadState`.
- Special-cases `opcode 0x0064` before mode dispatch by calling `FUN_00594100(1)`, which writes `dispatch_state = 1`.
- If `dispatch_state == 0`:
  - `DispatchState0Specific_S2C @ 0x0059DD20`
  - then `DispatchState0Common_S2C @ 0x0050CBC0`
- If `dispatch_state == 1`:
  - `DispatchState1_S2C @ 0x00613740`

Correction:

- `S->C 0x0064` is not just a self-placement packet.
- It is also a hard dispatch-boundary packet.
- Sending `0x0064` too early suppresses remaining state-0 handling.

## 2. Login bootstrap is a real scene-selection stage, not a tiny hello reply

Relevant handlers:

- `HandleS2C_0000_LoadLobbySparseCache @ 0x0059E070`
- `HandleS2C_0000_SelectLobbyEntryScene @ 0x0050D0E0`
- `Lobby_CopyBootstrapBlob_0183 @ 0x0050D1C0`

Binary facts:

- login blob copy size is exactly `0x183 bytes`
- `payload[0] = result_code`
- `payload[1] = lobby_mode`
- `payload[0x56] = sparse_count`
- sparse keys start at `+0x57`
- sparse values start at `+0xBB`

Scene split:

- `result_code == 0 && lobby_mode == 0` -> enqueue `0x6C` -> `lobby.wmb` -> scene mode `1`
- `result_code == 0 && lobby_mode != 0` -> enqueue `0x6B` -> `pet.wmb` -> scene mode `0`

Strongest inference:

- Login first lands in a lightweight login/lobby shell.
- PatHouse is a later state-0 bootstrap stage, not the direct effect of `0x0000` alone.

## 3. `0x0003 + 0x0007` is the actual room bootstrap arm

Relevant handlers:

- `HandleS2C_0003_StoreSpacePath @ 0x0050D200`
- `HandleS2C_0007_LoadSetupBlob @ 0x0059E330`
- `HandleS2C_0007_EmitPostSetupStateRequest @ 0x0050D290`
- `GameManager_EnqueueDefaultRoom @ 0x0050B090`

Verified behavior:

- `0x0003` stores `payload[0]` into `gm+0x31C63` and forwards `payload+1` as the path/state string.
- `0x0007` specific handler imports setup state.
- `0x0007` common handler does **not** enqueue room code `0`.
- Default path is `GameManager_EnqueueDefaultRoom()`, which disassembly proves pushes room code `100`.

Important correction:

- Earlier notes that implied `0x0007` default path leads to room code `0` and then `room.wmb` are too loose.
- The direct default enqueue from the `0x0007` common path is `100`.

What room code `100` does:

- `GameManager_DispatchRoomCode @ 0x0050A0F0`
- case `100` -> `GameManager_ExecuteRoomInit(100)` -> `PatHouse_RoomInit @ 0x00531640` -> scene mode `2`

Strongest inference:

- packet-driven PatHouse bring-up is:
  - login shell (`0x6B` or `0x6C`)
  - then `0x0003 + 0x0007`
  - then default room enqueue `100`
  - then `PatHouse_RoomInit`
  - then scene mode `2`

## 4. `0x0002` remains a hard negative during early bootstrap

Relevant logic:

- `DispatchState0Common_S2C case 2 @ 0x0050CBC0`
- `HandleS2C_0002_TransitionPrimary @ 0x0059D150`
- `GameManager_PerFrameUpdate @ 0x00509200`

Binary facts:

- `0x0002` common handler writes `gm+0x31946 = 0`
- `GameManager_PerFrameUpdate` only dispatches queued room codes while `gm+0x31946 != 0`
- `HandleS2C_0002_TransitionPrimary` also emits client-side `C->S 0x0007`

Conclusion:

- `0x0002` is not required for early PatHouse progress.
- In early login it is actively harmful.

## 5. `0x0004` is split into two different meanings

Relevant logic:

- `DispatchState0Specific_S2C @ 0x0059DD20`
- `HandleS2C_0004_CalibrationSample @ 0x0059DE50`
- `DispatchState0Common_S2C case 4 @ 0x0050CBC0`

Verified behavior:

- specific dispatcher only processes `0x0004` when `payload[0] == 0x01`
- it accumulates 5 samples
- on the 5th sample it mutates the same receive buffer to `0xFF`
- common dispatcher sees `0xFF` and sets `gm+0x31C71 = 1`

Correction:

- packet-faithful calibration is `0x01 + timestamp`, not `0x00 + timestamp`

But the current live packet log shows:

- six `S->C 0x0004` packets with `payload[0] == 0x00`
- the client still proceeds to `0x0003/0x0007/0x0005/0x000A/0x000B`

Therefore:

- `0x0004` is **not a hard gate for initial PatHouse progress**
- `0x0004` is much more relevant to Hansol/Plaza-style readiness paths

## 6. PatHouse room init and state-1 are distinct stages

`PatHouse_RoomInit @ 0x00531640`:

- runs 6 staged init steps
- checks failure via `FUN_00528B30()`
- closes loading screen at the end

This matters because:

- PatHouse can complete entirely inside state-0
- state-1 promotion should not be forced by the server during this stage

## 7. Hansol/Plaza path is partially verified, not fully closed

Relevant functions:

- `Plaza_TransitionFromRoom @ 0x00568770`
- `GameManager_SetHansolFlag @ 0x00528490`
- `GameManager_DispatchRoomCode case 0x0B / 0x6E`
- `Hansol_SceneStageHandler @ 0x00614370`

Verified facts:

- `Plaza_TransitionFromRoom` sets room code `0x6E`
- it sets `gm+0x31C72 = 1`
- it resets the calibration accumulator by calling `HandleS2C_0004_CalibrationSample(this, NULL)`
- room code `0x0B` loads `hansol.wmb` only if `gm+0x31C71 != 0`, then pushes `0x6E`
- room code `0x6E` runs `Hansol_SceneStageHandler`
- `Hansol_SceneStageHandler` stage 0 calls `SendC2S_0064_LocalBootstrapStatus`

Strongest safe interpretation:

- Hansol/Plaza transition depends on both:
  - readiness latch `gm+0x31C71`
  - hansol flag `gm+0x31C72`
- the exact packet-only sequence that naturally produces both is still not fully closed
- but the binary clearly shows that Hansol init is a later staged flow, not just "send `0x0064` and hope"

## 8. Hard gates vs support packets

### Hard gates for initial PatHouse progress

- `S->C 0x0000`
- `S->C 0x0003`
- `S->C 0x0007`
- no early `S->C 0x0002`
- no early `S->C 0x0064`

### Strong support packets for stable non-broken bootstrap

- `S->C 0x0005`
- `S->C 0x000A`
- `S->C 0x000B`

### Not proven as hard gate for first PatHouse progress

- `S->C 0x0004`

### Strongly relevant for Hansol/Plaza and later gameplay

- `S->C 0x0004` true calibration path
- state-1 family `0x0064..0x0071`

## 9. Re-verified strongest-inference game flow

```text
connect
  -> C->S 0x0000
  -> S->C 0x0000 (0x183 login blob)
  -> state-0 scene shell: pet.wmb or lobby.wmb
  -> S->C 0x0003 (space root)
  -> S->C 0x0007 (setup import)
  -> default room enqueue = 100
  -> PatHouse_RoomInit
  -> scene mode 2
  -> later, only when appropriate, state-1 packets
```

For Hansol/Plaza:

```text
room mode 2
  -> outdoor transition helper(s)
  -> readiness latch + hansol flag needed
  -> hansol.wmb load path / room code 0x6E init
  -> stage 0 sends local C->S 0x0064
  -> later state-1 actor/world synchronization
```

This second flow is strongly indicated, but not fully closed as a packet-only recipe yet.
