# Azrok Consolidated Packet Contracts And Server Workflow

This document merges packet layouts, server behavior rules, and workflow drafts into one deduplicated contract.

## 1. High-value `S->C` packet contracts

### `S->C 0x0000`

- Real `0x183`-byte login/lobby sparse-cache blob.
- Key fields:
  - `+0x00` `u8 result_code`
  - `+0x01` `u8 lobby_mode`
  - `+0x56` `u8 sparse_count`
  - `+0x57` sparse keys
  - `+0xBB` sparse values

### `S->C 0x0003`

- `+0x00` `u8 mode_or_flag`
- `+0x01` NUL-terminated path/state string

### `S->C 0x0004`

- `+0x00` `u8 sample_kind`
- `+0x01` `u32 timestamp_ms`

Packet-faithful use:

- Use `sample_kind = 0x01`
- Repeat 5 times if you want the true readiness path

### `S->C 0x0005`

- `+0x00` `u8 status`
- `+0x01` `u8 subtype`
- `+0x02` `u32 state_value`

### `S->C 0x0006`

Reset local clock and seed.

Verified structure:

- `+0x00` `u8 opcode_substatus`
- `+0x01` `u8 header_or_selector`

Verified behavior:

- when `payload[0] == 0`, the client resets local timing/seed paths
- then emits a fresh `C->S 0x0007`

Server rule:

- if the server intentionally uses `S->C 0x0006`, it must be prepared for client `C->S 0x0007` afterward

### `S->C 0x0007`

Touched size: `0x1D8`

Important verified points:

- carries bootstrap selectors, stat words, runtime rows, and local-effect bytes
- `+0x125` is live local-effect data, not filler
- empty/no-op style slots should be modeled with `0xFF`, not casual `0x00`

### `S->C 0x000A`

Grouped stat registry, total `0x96` bytes.

Important correction:

- wire groups are narrower than older broad category interpretations

Verified wire groups:

- group 0, 22 values:
  - ids `1,2,4,5,7,8,10,11,13,14,16,17,19,20,22,23,25,26,28,29,31,32`
- group 1, 6 values:
  - ids `2002,2003,2005,2006,2008,2009`
- group 2, 5 values:
  - ids `2501,2502,2504,2505,2507`
- group 3, 32 values:
  - ids `1001..1032`
- group 4, 3 values:
  - ids `1500,1501,1502`
- group 5, 1 value:
  - id `3000`
- group 6, 6 values:
  - ids `4000..4005`

### `S->C 0x000B`

- 31 `u16` values
- total 62 bytes

### `S->C 0x0064`

Authoritative self placement, but also a dispatcher state boundary.

Rule:

- Do not send it during early state-0 bootstrap.

### `S->C 0x0065`

- remote actor flush
- empty payload

### `S->C 0x0066`

- remote actor batch spawn
- record size `0x1A`
- verified fields include:
  - `+0x00` `u8 record_kind`
  - `+0x01` `u32 actor_id`
  - `+0x18` `u8 pair_left`
  - `+0x19` `u8 pair_right`

### `S->C 0x0067`

- remote actor removal path
- later state-1 actor-management packet, not part of minimum PatHouse bootstrap

### `S->C 0x0068`

- remote actor state batch
- record size `0x18`
- verified fields:
  - `+0x00` `u32 actor_id`
  - `+0x04` `u32 arg_04`
  - `+0x08` `u32 arg_08`
  - `+0x0C` `u32 arg_0C`
  - `+0x10` `u32 arg_10`
  - `+0x14` `u32 state_gate`

### `S->C 0x0069`

- actor action state
- 4 dwords:
  - `actor_id`
  - `arg_04`
  - `arg_08`
  - `action_gate_or_control`

### `S->C 0x006A`

- actor text payload
- verified touched layout:
  - `+0x00` `u8 text_kind`
  - `+0x01` `u8 text_mode`
  - `+0x02` `u32 actor_id`
  - `+0x06` primary string
  - `+0x15` secondary string

### `S->C 0x006B`, `0x006C`, `0x006D`

- `0x006B` updates self-only state byte `field33A`
- `0x006C` updates remote actor bytes `field336` and `field33A`
- `0x006D` advances actor field332 from `2` to `3` and pushes scene code `0x31`

### `S->C 0x006E`

- ready commit / ready-mode packet
- verified layout:
  - `+0x00` `u8 mode_selector`
  - `+0x01` `u8 ready_gate`
- when `ready_gate == 0`, it commits ready state and sets local ready flag at `+0x129B`

### `S->C 0x006F`

- selector pair update
- verified layout:
  - `+0x00` `u8 selector_index`
  - `+0x01` `u8 selector_value`

### `S->C 0x0070`

- latched dual-form packet
- short form when latch is clear
- full form carries a word at `+0x02` and dwords at `+0x04` and `+0x08`

### `S->C 0x0071`

- local FE/UI synth path
- only acts when `payload[0] == 0`

These later-state packets belong to state-1 world/actor sync, not the minimum PatHouse bootstrap.

## 2. High-value `C->S` packet contracts

### `C->S 0x0000`

- login hello / transport start

### `C->S 0x0001`

- transition/disconnect-style ack candidate from older runs and notes
- not required in the current reproduced minimal PatHouse flow
- safest contract remains: accept if seen, do not blindly echo

### `C->S 0x0004`

- character-creation style client packet in older notes/runtime handling
- not part of the current reproduced minimal PatHouse flow

### `C->S 0x0007`

- proven client follow-up after some transition-style handlers
- server should tolerate repeats and not restart bootstrap blindly each time

### `C->S 0x0008`

- client state-sync style packet in older notes/runtime handling
- not part of the current reproduced minimal PatHouse flow

### `C->S 0x0016`

- heartbeat
- tolerate and answer conservatively

### `C->S 0x000C`

Newest consolidated conclusion:

- proven sender: `FUN_0059b0b0 @ 0x0059B0B0`
- proven wire form: `opcode 0x000C`, `len 11`
- proven dirty-check gate: `FUN_0059cce0 @ 0x0059CCE0`
- proven payload builder: `FUN_0059c790 @ 0x0059C790`
- recovered higher-level call paths include:
  - `FUN_005ba900 @ 0x005BA900`
  - `FUN_005bc970 @ 0x005BC970`

Best interpretation:

- compact changed-selection / changed-slot snapshot
- not the same structure as inbound `S->C 0x000C`
- not safe to raw-echo

Best current server contract:

- accept it
- log payload and timing
- no immediate reply is proven necessary
- later, when byte mapping is fully decoded, translate it into authoritative `S->C 0x000C` updates and adjacent actor-state sync only if needed

Live evidence:

- [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L382)
- [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L410)
- [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L438)

### `C->S 0x0017`

- proven sender: `FUN_0059dcd0 @ 0x0059DCD0`
- proven serialization: `<BBI>`
- stable observed payload example: `07 01 00 00 00 00`

Best current server contract:

- accept and log it
- treat it as a later readiness/status transition packet
- do not use first `0x0017` to force early `S->C 0x0064`

Reference:

- [live_run.stdout.log](<home>/Documents/<project-dir>/Azrok_Plaza/artifacts/ui-probes/live_run.stdout.log#L192)

### `C->S 0x0064`

- proven producer path: `Hansol_SceneStageHandler -> SendC2S_0064_LocalBootstrapStatus`
- proven wire form: 1 byte only

Best current server contract:

- treat as bootstrap/progress flag
- never raw-echo as `S->C 0x0064`

### `C->S 0x0019`

- outdoor transition request candidate from older server/runtime handling
- relevant to later Hansol/Plaza work, not the minimum PatHouse flow

## 3. Minimum server workflow

### Phase A: connection and state-0 bootstrap

1. accept `C->S 0x0000`
2. send `S->C 0x0000`
3. send `S->C 0x0003`
4. send `S->C 0x0007`
5. send `S->C 0x0005`
6. send `S->C 0x000A`
7. send `S->C 0x000B`
8. keep tolerating `C->S 0x0016`
9. keep tolerating repeated `C->S 0x0007`

### Phase B: stable in-room operation

- accept `C->S 0x000C`
- do not blind-echo it
- accept `C->S 0x0017` if it appears later
- do not force state-1 early

### Phase C: later state-1 or Hansol path

Only after bootstrap is truly stable should the server consider:

- authoritative `S->C 0x0064`
- `S->C 0x0065/0x0066/0x0067/0x0068/0x0069/0x006A`
- `S->C 0x006B/0x006C/0x006D`
- `S->C 0x006E`
- `S->C 0x006F/0x0070/0x0071`

## 4. Hard exclusions and safety rules

- Do not send early `S->C 0x0002`.
- Do not send early `S->C 0x0064`.
- Do not blindly echo `C->S 0x0001`.
- Do not confuse client `0x0064` with server `0x0064`.
- Do not treat `C->S 0x000C` as wire-symmetric with inbound `S->C 0x000C`.
- If you use `S->C 0x0002` or `S->C 0x0006` in other flows, expect client `C->S 0x0007` afterward.

## 5. Known side branches that are real but not part of the minimum flow

### `S->C / receive path 0x0009`

- this packet has a real special branch when `payload[5] == 0x0F`
- related handlers noted in earlier audit:
  - `FUN_0059EB20`
  - `FUN_0050CF30`

Interpretation:

- `0x0009` is not core to the confirmed PatHouse bootstrap
- but it should not be dismissed as random noise

## 6. Current emulator heuristics that remain heuristic

These handlers are still best treated as provisional logic, not final protocol truth:

- [azrok_server.py](<home>/Documents/<project-dir>/Azrok_Plaza/azrok_server.py#L2546)
- [azrok_server.py](<home>/Documents/<project-dir>/Azrok_Plaza/azrok_server.py#L2624)

Most important merged corrections:

- `0x0017` is now binary-proven as a real late `<BBI>` client send.
- `0x0064` client-send handling is only correct if treated as a 1-byte progress/status packet and never echoed.
- `0x000C` should be treated as an inbound delta/snapshot contract, not a mirror request.
