# Azrok Protocol Audit - Corrections And Gaps

Date: 2026-04-01
Purpose: corrections to prior assumptions in `docs/research` and current `azrok_server.py`

## 1. Corrections to prior protocol interpretation

### Correction A: `S->C 0x0004` is not simply `0x00 + timestamp`

Prior assumption:
- existing status notes describe `0x0004` as `\x00 + u32 timestamp`

Binary evidence:
- `DispatchState0Specific_S2C` @ `0x0059DD20` only processes `0x0004` when `payload[0] == 1`
- `HandleS2C_0004_CalibrationSample` @ `0x0059DE50` mutates the fifth sample to `0xFF`
- `DispatchState0Common_S2C` @ `0x0050CBC0` only latches readiness when it sees `0xFF`

Revised interpretation:
- packet-faithful calibration should use `payload[0] = 0x01`
- `0xFF` is an internal milestone reached on the fifth sample
- `0xFF` is also used directly in outdoor/Hansol transition logic

### Correction B: `S->C 0x0064` does more than place the player

Prior assumption:
- `0x0064` was mainly tracked as a self-actor spawn packet

Binary evidence:
- `DispatchInbound_ByClientMode` @ `0x00594310` forces `dispatch_state = 1` before handing the packet to `HandleS2C_0064_ApplyAuthoritativeSelf`

Revised interpretation:
- `0x0064` is a state transition boundary as well as an actor-placement packet
- sending it too early can break state-0 post-load flow

### Correction C: `0x000A` wire ids are narrower than the earlier category view

Prior assumption:
- broader id families in prior research implied more ids were present on wire

Binary evidence:
- `HandleS2C_000A_StatRegistry` @ `0x0059ECA0`
- id tables read from:
  - `0x006DFB80`
  - `0x006DFBD8`
  - `0x006DFBF0`
  - `0x006DFC04`
  - `0x006DFC10`
  - `0x006DFC90`
  - `0x006DFC94`

Revised interpretation:
- the wire payload carries specific subsets, not all logical ids in each domain family

### Correction D: `0x0005` is processed twice in the overall receive path

Binary evidence:
- `DispatchInbound_ByClientMode` calls `HandleS2C_0005_PostLoadState` before state-mode dispatch
- state-0 common dispatch then routes `opcode 5` into `HandleS2C_0005_CommonWrapper`

Revised interpretation:
- `0x0005` is not a simple one-handler packet
- post-load state propagation and scene-specific wrapper behavior both matter

## 2. Mismatches in current `azrok_server.py`

### Mismatch A: calibration packets are built with `0x00`

File evidence:
- `azrok_server.py:2467` builds `struct.pack('<BI', 0x00, ts)`

Why it matters:
- the packet-faithful path in the binary expects state-0 specific dispatch to see byte `1`, not `0`

### Mismatch B: current notes still describe `0x0004` as `0x00 + timestamp`

File evidence:
- `docs/research/00_current_status.md:86`

Why it matters:
- this is now disproven by the actual dispatch order and handler logic

### Mismatch C: `0x0064` comments understate the dispatch-state side effect

File evidence:
- `azrok_server.py:2174-2206`
- `azrok_server.py:2460-2462`

What is missing:
- the server comments note that `0x0064` changes dispatch state, but the binary proof is stronger:
  - it is changed before the packet is handed into the state-1 handler

### Mismatch D: `0x000A` comments are conceptually right on sizes but not on actual id subsets

File evidence:
- `azrok_server.py:2336-2382`

What is missing:
- the grouped counts are correct
- the actual logical ids per group should be documented with the concrete binary arrays above

## 3. Newly narrowed protocol gaps

### Gap A: current live capture shows only one real post-entry client verb so far

Current `packets_log.txt` session observed only these C->S opcodes:

- `0x0000`
- `0x0016`
- `0x0007`
- `0x000C`

This matters because it narrows the "normal play next" gap sharply:

- in the currently reproduced PatHouse flow, the only repeatedly observed post-entry gameplay candidate is `C->S 0x000C`
- therefore `0x000C` is the highest-priority missing server contract, not a side note

Captured `0x000C` payload examples:

```text
0c0f12181ee14e00140000
0c0f12191ee14e00140000
030c0f141a1e4e00140000
```

Operational conclusion:

- do not blind-echo `0x000C`
- recover its send-side builder or semantic field order before claiming packet-only "normal gameplay"

### Gap B: full `C->S 0x0064` wire layout is still not fully lifted

What is known:
- `SendC2S_0064_LocalBootstrapStatus` @ `0x006130B0` clearly gathers:
  - two local status bytes
  - a 13-byte name
  - four domain slot bytes
  - bootstrap flags

What is still missing:
- the final serialized order on the wire is still partially hidden behind helper thunks

Operational conclusion:
- the server should accept and log `C->S 0x0064`, but it does not need to parse every field yet for single-client PatHouse play

### Gap C: `C->S 0x0017` remains under-lifted

What is known:
- it appears after later loading/bootstrap progress
- it is likely part of post-scene readiness or state-finalization

What is not yet proven:
- the exact binary function that serializes or strictly requires it

Operational conclusion:
- for now it should be accepted and answered conservatively, not used as the primary bootstrap trigger

### Gap D: `0x0009` has a real special case

Binary evidence:
- `DispatchInbound_ByClientMode` special-cases `opcode 9` when `payload[5] == 0x0F`
- handlers:
  - `FUN_0059EB20`
  - `FUN_0050CF30`

Operational conclusion:
- `0x0009` is not part of the core playable PatHouse path, but it is a real protocol branch and should not be treated as pure noise

## 4. Practical server priorities from this audit

Highest priority:
1. Make `0x0004` packet-faithful.
2. Keep `0x0064` disabled during early bootstrap.
3. Keep `0x0002` out of initial login flow.
4. Preserve the established `0x0003 + 0x0007 + 0x0005 + 0x000A + 0x000B` room bootstrap bundle.
5. Prepare for legitimate later use of state-1 packets for multi-actor synchronization.

Next priority:
1. Lift the exact serialized layout of `C->S 0x0064`.
2. Lift the exact producer/consumer path for `C->S 0x0017`.
3. Confirm whether outdoor/Hansol can be made fully packet-faithful without direct process-memory flag writes.
