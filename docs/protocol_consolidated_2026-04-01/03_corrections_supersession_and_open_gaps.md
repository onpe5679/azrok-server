# Azrok Consolidated Corrections, Supersession, And Open Gaps

## 1. Supersession summary

This consolidated folder supersedes the overlapping material in:

- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\protocol_audit_2026-04-01`
- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\protocol_master_reverify_2026-04-01`
- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\protocol_reverify_2026-04-01`
- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\protocol_workflow_verification_2026-04-01`
- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\protocol_gap_closure_2026-04-01`

Why this merge was needed:

- the same conclusions were spread across audit, re-verification, workflow, and gap-closure passes
- a few older interpretations were later corrected
- one folder contains mojibake-style heading corruption, so keeping it as the main reference is not ideal

## 2. Final corrected interpretations

### `S->C 0x0004`

Final corrected reading:

- not `0x00 + timestamp`
- packet-faithful path is `0x01 + timestamp`, repeated 5 times
- the fifth sample becomes `0xFF` internally and latches readiness

### `S->C 0x0064`

Final corrected reading:

- not just self placement
- also a hard dispatch-state boundary
- dangerous if sent before state-0 work is complete

### `S->C 0x0005`

Final corrected reading:

- has two layers of meaning in the receive path
- first pre-dispatch processing, then state-0 common handling

### `S->C 0x0007`

Final corrected reading:

- real setup/blob import stage
- part of the decisive bootstrap axis
- stronger corrected interpretation puts PatHouse bring-up on the default room-init path associated with room code `100`

### `S->C 0x000A`

Final corrected reading:

- grouped sizes were already roughly understood
- actual on-wire id subsets are narrower than older broad category notes implied
- earlier audit identified the concrete backing id arrays at:
  - `0x006DFB80`
  - `0x006DFBD8`
  - `0x006DFBF0`
  - `0x006DFC04`
  - `0x006DFC10`
  - `0x006DFC90`
  - `0x006DFC94`

### `C->S 0x000C`

Final corrected reading:

- no longer just "mysterious late packet"
- wire sender, dirty-check gate, payload builder, and two caller paths are now recovered
- still not fully byte-decoded, but it is clearly not wire-symmetric with inbound `S->C 0x000C`

## 3. Additional contradictions that were present in the archived set

### Older minimum-flow notes vs current live run

Older notes and draft workflows sometimes treated `C->S 0x0001`, `0x0008`, and `0x0017` as part of the minimal practical flow.

Current consolidated position:

- the current live reproduced session does not support that as a minimum requirement
- those packets belong in extended or later candidate workflows, not in the minimum currently playable PatHouse contract

### Current emulator heuristics vs binary-faithful target

Two important heuristic leftovers from archived notes remain worth remembering:

- current local server behavior around `S->C 0x0004` was historically built with `0x00` rather than packet-faithful `0x01`
- current local server behavior also historically re-sent the `0x0007 + 0x0005 + 0x000A + 0x000B` bundle after the first client `0x0007`

These are useful for explaining why a locally playable run and a binary-faithful run are not always the same thing.

### `docs/research` note supersession

The archived audit also corrected an older note in:

- [00_current_status.md](<home>/Documents/<project-dir>/Azrok_Plaza/docs/research/00_current_status.md)

Most important superseded point there:

- `S->C 0x0004` should no longer be described as `0x00 + timestamp`

## 4. What is now closed

- minimum currently playable PatHouse bootstrap axis
- danger of early `S->C 0x0002`
- danger of early `S->C 0x0064`
- packet-faithful interpretation of `S->C 0x0004`
- `C->S 0x0017` sender and wire layout
- `C->S 0x0064` sender and 1-byte wire layout
- `C->S 0x000C` sender, send length, dirty-check gate, and two recovered caller paths
- `0x0009` is confirmed to be a real protocol branch rather than ignorable noise

## 5. What is still not fully closed

### Exact byte-to-meaning map for all 11 bytes of `C->S 0x000C`

This is now the main remaining server-contract blocker.

What is already known:

- it is not a heartbeat
- it is not a mirror of inbound `S->C 0x000C`
- it is likely a compact selection/domain/equipment delta snapshot

What is still missing:

- the exact authoritative server-side meaning of each emitted byte position/value

### Final user-facing naming of the recovered `0x000C` subsystem

Recovered functions strongly suggest a selection/domain/equipment subsystem, but the final human-readable subsystem name is still inferred rather than fully named.

### Fully packet-faithful Hansol/Plaza recipe

Strongly narrowed facts exist:

- readiness latch `gm+0x31C71` matters
- Hansol flag `gm+0x31C72` matters
- client `C->S 0x0064` belongs to that later path

Still not fully closed:

- the exact natural packet-only sequence that reproduces the whole transition cleanly without process-memory shortcuts

### `0x0009`

Not part of the minimum PatHouse flow, but still not semantically lifted enough to assign a stable server-side contract beyond "real branch, not noise".

## 6. Best next validation pass

1. Capture exact player actions that trigger each observed `C->S 0x000C`.
2. Correlate actions with:
   - [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L382)
   - [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L410)
   - [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L438)
3. Build the byte-position translation table from `C->S 0x000C` into authoritative server-side slot/equipment meaning.
4. Only after that, finalize whether the authoritative reply should be:
   - one or more `S->C 0x000C` slot updates
   - or `S->C 0x000C` plus `0x0068/0x0069` actor-state refreshes
5. After the `0x000C` byte map is closed, return to full packet-faithful Hansol/Plaza validation.

6. Re-capture a longer live session to see whether `0x0017`, `0x0008`, or `0x0064` appear under real interaction once the session moves past the current minimal room flow.

## 7. Confidence summary

High confidence:

- minimum currently playable PatHouse flow
- `S->C 0x0002` as an early hard negative
- `S->C 0x0064` as a state boundary
- `C->S 0x0017` sender/layout
- `C->S 0x0064` sender/layout
- `C->S 0x000C` sender/length/non-symmetry

Medium confidence:

- `C->S 0x000C` as a selection/domain/equipment delta snapshot
- later authoritative response should be translated rather than mirrored

Low confidence:

- full 11-byte semantic map for every `C->S 0x000C` byte
- fully packet-faithful Hansol/Plaza transition recipe
