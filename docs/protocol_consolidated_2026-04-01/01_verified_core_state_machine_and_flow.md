# Azrok Consolidated Protocol Core

Date: 2026-04-01
Scope: merged and de-duplicated protocol conclusions from the following superseded folders:

- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\protocol_audit_2026-04-01`
- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\protocol_master_reverify_2026-04-01`
- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\protocol_reverify_2026-04-01`
- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\protocol_workflow_verification_2026-04-01`
- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\protocol_gap_closure_2026-04-01`

This consolidated set prefers the newest binary-backed conclusion when earlier folders disagree.

## 1. Core inbound dispatcher facts

Primary dispatcher:

- `DispatchInbound_ByClientMode @ 0x00594310`

Verified behavior:

- Logs every inbound packet first.
- Special-cases `S->C 0x0005` before state dispatch.
- Special-cases `S->C 0x0064` by forcing `dispatch_state = 1` before normal handling.
- If `dispatch_state == 0`, calls:
  - `DispatchState0Specific_S2C @ 0x0059DD20`
  - then `DispatchState0Common_S2C @ 0x0050CBC0`
- If `dispatch_state == 1`, calls:
  - `DispatchState1_S2C @ 0x00613740`

Most important consequence:

- `S->C 0x0064` is not just self placement.
- It is a hard state boundary.
- Sending it early can suppress still-needed state-0 work.

## 2. Verified state-0 bootstrap axis

### `S->C 0x0000`

`HandleS2C_0000_LoadLobbySparseCache @ 0x0059E070` and related handlers prove that `0x0000` is a real `0x183`-byte login/lobby blob, not a tiny hello reply.

Verified fields:

- `+0x00` `result_code`
- `+0x01` `lobby_mode`
- `+0x56` `sparse_count`
- keys start at `+0x57`
- values start at `+0xBB`

Scene split:

- `result_code == 0 && lobby_mode == 0` -> lobby shell
- `result_code == 0 && lobby_mode != 0` -> pet shell

### `S->C 0x0003 + 0x0007`

This pair is the real room-entry arm.

- `0x0003` stores `payload[0]` into `gm+0x31C63` and forwards `payload+1` as the path/state string.
- `0x0007` imports the setup blob and continues the room/bootstrap sequence.

Important corrected conclusion:

- The effective default PatHouse path is not "send `0x0007` and then room code `0`".
- Re-verification moved the stronger conclusion to room init path `100` for PatHouse entry.

### `S->C 0x0005 + 0x000A + 0x000B`

These are part of the real bootstrap bundle, not optional decoration.

- `0x0005` is processed twice overall: once before state dispatch, then again in state-0 common handling.
- `0x000A` is the grouped stat registry.
- `0x000B` is the XP curve block.

PatHouse stage note:

- `PatHouse_RoomInit @ 0x00531640` runs staged room initialization, checks failure via `FUN_00528B30()`, and closes the loading screen at the end.
- This supports the stronger conclusion that PatHouse can finish stabilizing entirely inside the state-0 side before the server should force state-1 promotion.

## 3. Dangerous or easily misread packets

### `S->C 0x0002`

This remains a hard negative during early bootstrap.

- State-0 common handling writes `gm+0x31946 = 0`.
- `GameManager_PerFrameUpdate @ 0x00509200` only dispatches queued room codes while that gate is nonzero.
- `HandleS2C_0002_TransitionPrimary @ 0x0059D150` also causes the client to emit `C->S 0x0007`.

Rule:

- Do not use `S->C 0x0002` in the initial PatHouse bootstrap.

### `S->C 0x0004`

This was one of the biggest corrected interpretations.

Packet-faithful behavior:

- `DispatchState0Specific_S2C` only feeds `0x0004` into `HandleS2C_0004_CalibrationSample @ 0x0059DE50` when `payload[0] == 0x01`.
- The handler accumulates 5 samples.
- On the 5th sample it mutates the same receive buffer to `0xFF`.
- State-0 common handling then sees `0xFF` and latches readiness.

Correct interpretation:

- Packet-faithful calibration is `0x0004(sample_kind=0x01, timestamp)` repeated 5 times.
- The older `0x00 + timestamp` interpretation is superseded.

But current live-play implication:

- The presently reproduced PatHouse flow is not hard-gated on reproducing this path perfectly.
- `0x0004` matters more for readiness-sensitive later paths such as Hansol/Plaza.

## 4. Minimum currently playable PatHouse flow

This is the strongest de-duplicated minimum flow that remains consistent across binary re-verification and the current live packet log.

1. `C->S 0x0000`
2. `S->C 0x0000`
3. `S->C 0x0003`
4. `S->C 0x0007`
5. `S->C 0x0005`
6. `S->C 0x000A`
7. `S->C 0x000B`
8. tolerate repeated `C->S 0x0016`
9. tolerate repeated `C->S 0x0007`

Early exclusions:

- no early `S->C 0x0002`
- no early `S->C 0x0064`

## 5. Current live-session facts

Current live capture:

- [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt)

Observed `C->S` opcodes in the currently reproduced session:

- `0x0000`
- `0x0016`
- `0x0007`
- `0x000C`

Not observed in that session:

- `0x0001`
- `0x0004`
- `0x0008`
- `0x0017`
- `0x0019`
- `0x0064`

Strong implication:

- The minimum currently playable flow should not require `0x0001`, `0x0008`, or `0x0017`.
- The only repeatedly observed post-entry gameplay candidate in the current live run is `C->S 0x000C`.

Observed high-level sequence from the current live run:

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
... later C->S 0x000C appears with no immediate S->C partner ...
```

This is why the consolidated minimum flow explicitly separates:

- currently observed-playable flow
- binary-faithful target flow

## 6. Later-state and Hansol/Plaza position

Verified facts:

- Hansol/Plaza is a later staged path.
- It depends on readiness latch `gm+0x31C71`.
- It also depends on Hansol flag `gm+0x31C72`.
- `Hansol_SceneStageHandler @ 0x00614370` stage 0 emits client `C->S 0x0064`.

Current strongest safe interpretation:

- PatHouse can stabilize fully before state-1 promotion.
- Hansol/Plaza packet-only workflow is narrowed but not yet fully closed.
- State-1 family `0x0064..0x0071` belongs to later progression, not the minimum bootstrap.
- `0x0009` also has a real side branch when `payload[5] == 0x0F`, but it is not part of the confirmed PatHouse core path and should be treated as a real branch, not pure noise.
