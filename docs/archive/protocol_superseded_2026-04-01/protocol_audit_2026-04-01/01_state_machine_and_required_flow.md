# Azrok Protocol Audit - State Machine And Required Flow

Date: 2026-04-01
Target binary: `Azrok.exe` in Ghidra (`Azrok_analyzed.exe` project path)
Scope: inbound S2C dispatch, room/bootstrap state transitions, and the minimum server responses needed for packet-only gameplay

## 1. Core inbound dispatcher behavior

Primary dispatcher:
- `DispatchInbound_ByClientMode` @ `0x00594310`

Observed behavior:
- Logs every inbound packet first.
- Special-cases `opcode 0x0005` before mode dispatch by calling `HandleS2C_0005_PostLoadState`.
- Special-cases `opcode 0x0064` before mode dispatch by forcing `dispatch_state = 1` via `FUN_00594100`.
- When `dispatch_state == 0`, it calls:
  - `DispatchState0Specific_S2C` @ `0x0059DD20`
  - then `DispatchState0Common_S2C` @ `0x0050CBC0`
- When `dispatch_state == 1`, it calls `DispatchState1_S2C` @ `0x00613740`.

Important consequence:
- `S->C 0x0064` is not just an actor placement packet. The moment it arrives, the client flips from state-0 dispatch to state-1 dispatch.
- Sending `0x0064` too early can suppress still-needed state-0 processing.

## 2. Login and room bootstrap state machine

### 2.1 `S->C 0x0000` login bootstrap blob

Relevant handlers:
- `HandleS2C_0000_LoadLobbySparseCache` @ `0x0059E070`
- `HandleS2C_0000_SelectLobbyEntryScene` @ `0x0050D0E0`
- `Lobby_CopyBootstrapBlob_0183` @ `0x0050D1C0`

What the binary proves:
- The login blob copied into local storage is exactly `0x183` bytes.
- `payload[0]` is `result_code`.
- `payload[1]` is `lobby_mode`.
- `payload[0x56]` is `sparse_count`.
- Sparse keys start at `+0x57`.
- Sparse values start at `+0xBB`.
- The sparse cache table stores up to 50 `(u16 key, u32 value)` entries.

State split:
- `result_code == 0` and `lobby_mode == 0` -> enqueue room code `0x6C`
- `result_code == 0` and `lobby_mode != 0` -> enqueue room code `0x6B`

Room meaning:
- `0x6B` -> `pet.wmb`, then scene mode becomes `0`
- `0x6C` -> `lobby.wmb`, then scene mode becomes `1`

This confirms that the login response is not a tiny hello stub. It is a persistent lobby bootstrap cache blob.

### 2.2 `S->C 0x0003` and `S->C 0x0007` are the real room-entry arm

Relevant handlers:
- `HandleS2C_0003_StoreSpacePath` @ `0x0050D200`
- `HandleS2C_0007_LoadSetupBlob` @ `0x0059E330`
- `HandleS2C_0007_EmitPostSetupStateRequest` @ `0x0050D290`

What each does:
- `0x0003` stores `payload[0]` into `gm+0x31C63`, then forwards `payload+1` to two path/state consumers.
- `0x0007` imports the full setup blob, selectors, banks, stat words, runtime rows, and local effect codes.
- `0x0007` common handler then calls the vtable slot at `+0x28`, which is the enqueue/transition hook used to continue loading.

Server implication:
- For PatHouse-style bring-up, `0x0003 + 0x0007 + 0x0005 + 0x000A + 0x000B` is the decisive state-0 bootstrap bundle.
- `0x0002` is not inherently required for this path.

### 2.3 `S->C 0x0002` is dangerous during initial login

Relevant handler:
- `HandleS2C_0002_TransitionPrimary` @ `0x0059D150`
- `DispatchState0Common_S2C` case `2` @ `0x0050CBC0`

Binary facts:
- The common handler for `0x0002` writes `gm+0x31946 = 0`.
- `GameManager_PerFrameUpdate` @ `0x00509200` only dispatches room codes while `gm+0x31946 != 0`.
- `HandleS2C_0002_TransitionPrimary` also emits a client outbound `0x0007` through `FUN_005A4770(..., 7, ...)`.

Server implication:
- If `0x0002` is sent during early login, the room-dispatch gate is cleared and normal bootstrap can stall.
- The server should avoid `0x0002` during initial PatHouse login.
- If the server intentionally uses `0x0002` later for room transitions, it must understand that it also triggers a client `C->S 0x0007`.

## 3. The `0x0004` calibration path was previously under-specified

Relevant functions:
- `DispatchState0Specific_S2C` @ `0x0059DD20`
- `HandleS2C_0004_CalibrationSample` @ `0x0059DE50`
- `DispatchState0Common_S2C` case `4` @ `0x0050CBC0`
- `Plaza_TransitionFromRoom` @ `0x00568770`

Exact behavior:
- In state-0 specific dispatch, `opcode 0x0004` is processed only if `payload[0] == 1`.
- `HandleS2C_0004_CalibrationSample` accumulates 5 samples.
- On the fifth sample, it mutates the same receive buffer so that `payload[0] = 0xFF`.
- Because specific dispatch runs before common dispatch, the common handler then sees `0xFF` and sets `gm+0x31C71 = 1`.

This gives a precise packet-faithful sequence:
1. Send five `S->C 0x0004` packets with `payload[0] = 0x01` and a timestamp at `+1`.
2. The fifth one causes the client to rewrite the buffer to `0xFF`.
3. The common handler uses that rewritten byte to latch readiness.

Outdoor/Hansol note:
- `Plaza_TransitionFromRoom` resets the calibration state by calling `HandleS2C_0004_CalibrationSample(this, NULL)`.
- It also sets room code `0x6E` and `gm+0x31C72 = 1`.
- That means Hansol transition is tied to the same calibration machinery, not a wholly separate path.

## 4. Room-code dispatcher proof

Relevant function:
- `GameManager_DispatchRoomCode` @ `0x0050A0F0`

Important room codes:
- `100` -> loads PatHouse initialization, then scene mode `2`
- `0x6B` -> pet scene init, then mode `0`
- `0x6C` -> lobby scene init, then mode `1`
- `0x6E` -> Hansol scene init, then mode `4`

Critical case:
- Room code `0x0B` loads `hansol.wmb` only if `gm+0x31C71 != 0`

Server implication:
- The outdoor transition depends on the readiness latch at `gm+0x31C71`.
- A packet-only server must either:
  - drive the true `0x0004` calibration path correctly, or
  - reproduce the same latch effect by some other already-verified path.

## 5. Minimum packet-only playable contract

### PatHouse login

Required:
1. Accept `C->S 0x0000`.
2. Send `S->C 0x0000` with a valid `0x183`-byte lobby blob.
3. Drive calibration with `S->C 0x0004`.
4. Send `S->C 0x0003`.
5. Send `S->C 0x0007`.
6. Send `S->C 0x0005`.
7. Send `S->C 0x000A`.
8. Send `S->C 0x000B`.
9. Ignore repeated `C->S 0x0007`.
10. Do not echo `C->S 0x0001`.
11. Do not send `S->C 0x0064` before post-load state-0 work is done.

### Hansol / Plaza transition

Required or strongly indicated:
1. Preserve or restore readiness latch (`gm+0x31C71`).
2. Set Hansol flag (`gm+0x31C72`) through the legitimate transition path.
3. Use `0x0003` to update path/state.
4. Expect a client `C->S 0x0007` after transition-style triggers.
5. Use `0x0064` only after scene bring-up is complete enough for state-1 actor placement.

## 6. Still-open but narrowed questions

- `C->S 0x0017` is still observed as a follow-up candidate for later readiness or actor-finalization behavior, but the binary evidence here only proves that early `0x0064` is dangerous.
- `0x0009` has special dispatch handling when `payload[5] == 0x0F`, but it is not part of the confirmed PatHouse playable path.
- Multi-actor gameplay requires state-1 opcodes, especially `0x0065`, `0x0066`, `0x0068`, `0x0069`, and `0x006A`.
