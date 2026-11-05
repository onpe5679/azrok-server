# Recovered Opcode Details

Extracted from superseded archive docs (protocol_audit_2026-04-01, protocol_gap_closure_2026-04-01).
Date recovered: 2026-04-01

This file consolidates unique opcode details not present in other current research docs.

2026-07-17 live correction: the Hansol/Plaza recipe below now runs far enough
to emit and answer `C->S 0x0064`, but `entry_kind=0x0A` renders the OX quiz
space, not Plaza. The `S->C 0x0064` date crash and corrected layout are recorded
in `docs/research/24_0064_datefix_and_ox_entry_2026-07-17.md`.

---

## S->C Opcodes

### S->C 0x0004 — Calibration Sample

Handler: `HandleS2C_0004_CalibrationSample` @ `0x0059DE50`

**Verified structure:**
- `+0x00` `u8 sample_kind`
- `+0x01` `u32 timestamp_ms`

**Semantics:**
- `sample_kind == 0x01` is the live sample path. `DispatchState0Specific_S2C` @ `0x0059DD20` only processes `0x0004` when `payload[0] == 1`.
- After five samples, the handler mutates byte `0` to `0xFF`.
- `DispatchState0Common_S2C` @ `0x0050CBC0` only latches readiness when it sees `0xFF`.
- `0xFF` is also used directly in outdoor/Hansol transition logic.

**Verified test results:**
- `payload[0] = 0x01`: works (binary-correct). This is the packet-faithful path.
- `payload[0] = 0x00`: also works in practice (client accepts it), but does not follow the binary-proven dispatch path.

**Prior assumption corrected:** Earlier notes described 0x0004 as `\x00 + u32 timestamp`. Binary evidence disproves this. `azrok_server.py:2467` still builds `struct.pack('<BI', 0x00, ts)` which should be updated to `0x01`.

**Server contract:** Use `payload[0] = 0x01` for packet-faithful calibration readiness latching.

---

### S->C 0x0005 — Post-Load State (dual processing)

Handlers:
- `HandleS2C_0005_PostLoadState` @ `0x0059EBD0`
- `HandleS2C_0005_CommonWrapper` @ `0x0050CFF0`

**Verified structure:**
- `+0x00` `u8 status`
- `+0x01` `u8 subtype`
- `+0x02` `u32 state_value`

**Observed subtype handling:** `0x00`, `0x12`, `0x13`

**Dual processing detail:** `0x0005` is not a simple one-handler packet. `DispatchInbound_ByClientMode` calls `HandleS2C_0005_PostLoadState` before the mode-specific/common dispatchers. Then, in state-0, the same packet can still hit `HandleS2C_0005_CommonWrapper`. Both post-load state propagation and scene-specific wrapper behavior matter.

---

### S->C 0x0006 — Reset Local Clock and Seed

Handler: `HandleS2C_0006_ResetLocalClockAndSeed` @ `0x0059E1F0`

**Verified structure:**
- `+0x00` `u8 opcode_substatus`
- `+0x01` `u8 header_or_selector`

**When `payload[0] == 0`:**
- Resets local timing and seed paths
- Reapplies local archetype seed
- Emits `C->S 0x0007` through `FUN_005A4770`

**Server contract:** If the server sends `0x0006`, it must be ready to receive a new `C->S 0x0007`.

**Verified test results:**
- S->C 0x0006 triggers C->S 0x0007: CONFIRMED.
- Crashes if sent before room loading completes. Must be sent AFTER the game is in a stable room state. Unsuitable for initial login.
- S->C 0x0006 + S->C 0x0007 in the same packet: crashes (0xC0000005) because a loading transition is in progress when the reseed runs.

---

### S->C 0x000A — Grouped Stat Registry

Handler: `HandleS2C_000A_StatRegistry` @ `0x0059ECA0`

**Verified total size:** `0x96` bytes = 75 `u16` values

**Verified wire groups and ids:**

| Group | Count | Wire offset | Stat IDs |
|-------|-------|-------------|----------|
| 0 | 22 | `+0x00` | 1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17, 19, 20, 22, 23, 25, 26, 28, 29, 31, 32 |
| 1 | 6 | `+0x2C` | 2002, 2003, 2005, 2006, 2008, 2009 |
| 2 | 5 | `+0x38` | 2501, 2502, 2504, 2505, 2507 |
| 3 | 32 | `+0x42` | 1001..1032 |
| 4 | 3 | `+0x82` | 1500, 1501, 1502 |
| 5 | 1 | `+0x88` | 3000 |
| 6 | 6 | `+0x8A` | 4000..4005 |

**Note:** The on-wire `0x000A` groups are narrower than the broader domain/category ranges seen elsewhere in the binary. The wire payload carries specific subsets, not all logical ids in each domain family. Id tables read from `0x006DFB80`, `0x006DFBD8`, `0x006DFBF0`, `0x006DFC04`, `0x006DFC10`, `0x006DFC90`, `0x006DFC94`.

---

### S->C 0x0068 — Remote Actor State Batch

Handler: `HandleS2C_0068_BatchActorState` @ `0x00615D50`

**Record size:** `0x18` bytes = 6 dwords per record

**Verified fields:**
- `+0x00` `u32 actor_id`
- `+0x04` `u32 arg_04`
- `+0x08` `u32 arg_08`
- `+0x0C` `u32 arg_0C`
- `+0x10` `u32 arg_10`
- `+0x14` `u32 state_gate`

**Semantics:**
- `state_gate == 0` -> short coord/update path
- `state_gate != 0` -> full record application path

---

### S->C 0x0069 — Actor Action State

Handler: `HandleS2C_0069_ApplyActorActionState` @ `0x00615E70`

**Layout:** four dwords

**Verified fields:**
- `+0x00` `u32 actor_id`
- `+0x04` `u32 arg_04`
- `+0x08` `u32 arg_08`
- `+0x0C` `u32 action_gate_or_control`

---

### S->C 0x006F — Set Selector Pair

Handler: `HandleS2C_006F_SetSelectorPair` @ `0x00616B20`

**Layout:**
- `+0x00` `u8 selector_index`
- `+0x01` `u8 selector_value`

---

### S->C 0x0070 — Latched Dual Form

Handler: `HandleS2C_0070_HandleLatchedDualForm` @ `0x00616860`

**Dual form:**
- Short form when latch is clear: byte `1` plus word at `+2`
- Full form otherwise: byte `0`, word at `+2`, dwords at `+4` and `+8`

---

### S->C 0x0071 — Synthesize Local FE

Handler: `HandleS2C_0071_SynthesizeLocalFE` @ `0x00616510`

**Semantics:**
- Only acts when `payload[0] == 0`
- Synthesizes a local FE/UI text/effect path

---

## C->S Opcodes

### C->S 0x000C — Changed-Selection / Changed-Slot Snapshot

**Proven sender:** `FUN_0059b0b0` @ `0x0059B0B0`

**Wire form:** `(**(code **)(*this + 8))(0x0c, local_70, 0x0b)` — opcode `0x000C`, length `11`.

**Dirty-check gate:** `FUN_0059cce0` @ `0x0059CCE0` compares a cached local snapshot against a 9-byte stride table and returns nonzero only when state changed. The packet is only sent when the state has changed (not periodic).

**Payload builder:** `FUN_0059c790` @ `0x0059C790` walks enabled entries in the 9-byte stride table and writes `entry_value - base_value` bytes into the outbound buffer.

**Interpretation:** A compact changed-selection / changed-slot snapshot — not a periodic heartbeat and not the same struct as inbound `S->C 0x000C`.

**Recovered caller paths:**
- `FUN_005ba900` @ `0x005BA900` — looks like a reset/finalize path that sends the latest snapshot before clearing several local states.
- `FUN_005bc970` @ `0x005BC970` — looks like a UI selection/confirm path with menu-like codes `0x104..0x107`, scroll handling, gating, local effect emission, and local apply/finalize work. Sends `0x000C` immediately before local selection/effect application (`DomainCode_EmitLocalEffect` and follow-up local apply calls). Best modeled as a selection-confirm/update packet.
- Both belong to the same domain/equipment/selection subsystem, but their final user-facing labels are still unnamed.

**Asymmetry with inbound S->C 0x000C:**
- Inbound consumer: `HandleS2C_000C_ApplyActorSlotValue` @ `0x006165B0`
- Inbound layout: `u32 actor_id`, `u8 clear_flag`, `u8 slot_index`, `u8 slot_value`
- Outbound 11-byte payloads do not fit the inbound actor-slot struct. Blind echo is wrong.

**Captured payload examples from packets_log.txt:**
```
0c0f12181ee14e00140000  (line 382)
0c0f12191ee14e00140000  (line 410)
030c0f141a1e4e00140000  (line 438)
```

**Server contract:**
- Accept and log the 11-byte payload as a client-side delta/snapshot.
- No immediate reply is proven necessary from current runtime captures.
- Do not immediately mirror the same bytes back as `S->C 0x000C`.
- Once the byte-to-slot map is fully decoded, translate the client snapshot into authoritative `S->C 0x000C(actor_id, clear_flag, slot_index, slot_value)` updates, with adjacent `0x0068/0x0069` actor-state packets only if world presentation also changes.

**Remaining unknown:** The exact semantic map from each emitted delta byte to server-authoritative slot/domain/equipment meaning is not yet fully named. This is the main blocker before a byte-perfect server reply contract can be declared.

---

### C->S 0x0017 — Late Readiness / Status Transition

**Proven sender:** `FUN_0059dcd0` @ `0x0059DCD0`

**Proven serialization:** `<BBI>` packed as `kind, stat_id, value`, then sent by `thunk_FUN_0059d760(0x17, &local_10, 6)`. Wire length: **6 bytes**.

**Proven live sample:** `07 01 00 00 00 00` (from `artifacts/ui-probes/live_run.stdout.log` line 192).

**Interpretation:** A late readiness/status transition packet. Not part of the minimum PatHouse bootstrap.

**Server contract:**
- Accept and log it.
- Do not use first `0x0017` as a trigger for early `S->C 0x0064`.
- If the server answers at all, answer with already-safe late-stage readiness/state packets only after scene/bootstrap state is valid.

---

### C->S 0x0064 — Local Bootstrap Status Report

**Proven producer path:** `Hansol_SceneStageHandler` @ `0x00614370` stage 0 -> `SendC2S_0064_LocalBootstrapStatus` @ `0x006130B0`

**Proven wire send helper:** `FUN_005ab710` @ `0x005AB710`

**Wire form:** Exactly **1 byte**, sent as `thunk_FUN_005ab6a0(0x64, local_9, 1)`. The larger local bootstrap preparation inside `SendC2S_0064_LocalBootstrapStatus` is internal, not the wire payload.

**Direction split:** Inbound `S->C 0x0064` is a different contract (flips dispatch state before normal state-1 handling). Do not confuse the two.

**Server contract:**
- Treat it as a 1-byte bootstrap/progress flag report.
- Never raw-echo it as `S->C 0x0064`.
- Only send authoritative `S->C 0x0064` after state-0 bootstrap is complete and the self actor can safely exist.

---

---

### S->C 0x0009 — Selection Acknowledgment / Result (VERIFIED)

**Direction:** S->C only. Never observed as C->S. No PatHouse equivalent required.

**Verified structure:**
- `+0x04` `u8 result` — 0 = success
- `+0x05` `u8 sub_type` — 0x0F = selection

**Semantics:**
- Success path: clears pending selection state + triggers UI refresh
- Error path: displays MessageBox "AckResult 응답 오류"

---

### C->S 0x000C Complete Byte Map (VERIFIED)

**Wire length:** 11 bytes (variable-length list of relative item indices)

**Proven sender:** `FUN_0059B0B0` @ `0x0059B0B0`, gated by dirty-check `FUN_0059CCE0` @ `0x0059CCE0`

**Equipment slot domains:**
| Slot | Base Item ID | Range |
|------|-------------|-------|
| Head | 10000 | 10000–10009 |
| Face | 20000 | 20000–20006 |
| Back | 30000 | 30000–30003 |
| Pet  | 40000 | 40000–40007 |

**Byte encoding:** each byte = `(absolute_item_id - base_item_id) & 0xFF`

**Asymmetry with S->C 0x000C:**
- C->S = bulk snapshot 11 bytes (all slots in one packet)
- S->C = individual slot update 7 bytes (`actor_id`, `clear_flag`, `slot_index`, `slot_value`)

**Two caller paths:**
- `FUN_005BA900` @ `0x005BA900` — close equipment screen (reset/finalize path)
- `FUN_005BC970` @ `0x005BC970` — equip item confirm; menu codes 0x104–0x107

---

### Evolution 3 Disconnect Root Cause (VERIFIED)

**Root cause:** Double-bundle — server sent proactive S->C 0x0007, then C->S 0x0007 arrived and server responded again.

**Crash sequence:** Second S->C 0x0007 during room init → `HandleS2C_0007_EmitPostSetupStateRequest` re-entered → crash (0xC0000005)

**Fix:** Set `zone_request_count=1` after proactive bundle send. Subsequent C->S 0x0007 arrivals are then ignored (count already non-zero).

---

### Hansol/Plaza Complete Transition Recipe (VERIFIED via decompilation)

**Trigger sequence:**
1. S->C 0x000D `[0x00]` → client calls `Plaza_TransitionFromRoom` → sets `gm+0x31c72=1` + starts calibration
2. Client sends C->S 0x0016 `[0x01]` ×5 (calibration requests)
3. S->C 0x0004 samples ×4 + S->C 0x0004 `[0xFF]` → sets `gm+0x31c71=1`
4. `GameManager_DispatchRoomCode` code 11 → `level_load("hansol.wmb")`
5. Hansol Stage 0: C->S 0x0064 → server must respond immediately with S->C 0x0064
6. S->C 0x0064 creates self entity + calls `GameManager_CloseLoadingScreen`
7. S->C 0x006E `[mode, 0x00]` commits ready mode

**Key field notes:**
- `gm+0x31c72` is set by client (via 0x000D handler), NOT by server directly
- `gm+0x31c71` is set by calibration completion (0x0004 with `payload[0]=0xFF`)
- `FUN_00528b30` after each stage = gate `(gm+0x31946)` liveness check

---

## Remaining Unknowns (as of 2026-04-01)

- **Exact byte meaning inside `C->S 0x000C`:** The payload builder is known but the semantic map from each delta byte to server-authoritative slot/domain/equipment meaning is not fully named. This is the highest-priority remaining blocker for byte-perfect server reply.
- **`C->S 0x000C` caller subsystem names:** `FUN_005ba900` and `FUN_005bc970` belong to the domain/equipment/selection subsystem but final user-facing labels are unnamed. Next step: instrument real play to correlate user actions with the three observed payload families.
- **Full `C->S 0x0064` wire layout:** `SendC2S_0064_LocalBootstrapStatus` gathers two local status bytes, a 13-byte name, four domain slot bytes, and bootstrap flags, but the final serialized order is partially hidden behind helper thunks.

## Confidence Summary

| Opcode | Confidence | Notes |
|--------|------------|-------|
| C->S 0x0017 | High | Sender and wire layout recovered |
| C->S 0x0064 | High | Sender and 1-byte wire layout recovered |
| C->S 0x000C | High (send), Medium (semantics) | Send length, dirty-check, non-symmetry proven; slot map not yet decoded |
| S->C 0x0006 timing | High | Must not send before stable room state; crashes confirmed |
| S->C 0x000A id subsets | High | Concrete binary arrays recovered per group |
| S->C 0x0005 dual processing | High | Both handler paths proven in dispatch order |
