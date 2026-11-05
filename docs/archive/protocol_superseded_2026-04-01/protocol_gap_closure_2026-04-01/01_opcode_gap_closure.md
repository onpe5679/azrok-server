# Opcode Gap Closure

This pass used direct Ghidra HTTP endpoints, not `run_script_inline`.

## Verified `C->S 0x000C`

- Proven sender: `FUN_0059b0b0 @ 0x0059B0B0`.
- Proven wire form: virtual send call `(**(code **)(*this + 8))(0x0c, local_70, 0x0b)`, so the client really emits `opcode 0x000C`, `len 11`.
- Proven guard: `FUN_0059cce0 @ 0x0059CCE0` compares a cached local snapshot against a 9-byte stride table and returns nonzero only when the state changed.
- Proven payload builder: `FUN_0059c790 @ 0x0059C790` walks enabled entries in the same 9-byte stride table and writes `entry_value - base_value` bytes into the outbound buffer.
- Strong inference: `C->S 0x000C` is a compact changed-selection / changed-slot snapshot, not a periodic heartbeat and not the same struct as inbound `S->C 0x000C`.
- Proven callsites recovered so far:
  - `FUN_005ba900 @ 0x005BA900`
  - `FUN_005bc970 @ 0x005BC970`
- Strong inference on timing: `FUN_005bc970` sends `0x000C` immediately before local selection/effect application (`DomainCode_EmitLocalEffect` and follow-up local apply calls), so this is best modeled as a selection-confirm/update packet.
- Important nuance: the concrete wire sender function is recovered, but the final high-level named subsystem owner above these recovered caller paths is still not fully named.

### Why `C->S 0x000C` is not wire-symmetric

- Proven inbound consumer: `HandleS2C_000C_ApplyActorSlotValue @ 0x006165B0`.
- Proven inbound `S->C 0x000C` layout: `u32 actor_id`, `u8 clear_flag`, `u8 slot_index`, `u8 slot_value`.
- Proven mismatch with live outbound traffic:
  - [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L382)
  - [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L410)
  - [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L438)
- Those outbound 11-byte payloads do not fit the proven inbound actor-slot struct, so blind echo remains wrong.

### Best current server contract for `0x000C`

- Accept and log the 11-byte payload as a client-side delta/snapshot.
- No immediate reply is proven necessary from current runtime captures.
- Do not immediately mirror the same bytes back as `S->C 0x000C`.
- Once the byte-to-slot map is fully decoded, translate the client snapshot into authoritative `S->C 0x000C(actor_id, clear_flag, slot_index, slot_value)` updates, with adjacent `0x0068/0x0069` actor-state packets only if world presentation also changes.

## Verified `C->S 0x0017`

- Proven sender: `FUN_0059dcd0 @ 0x0059DCD0`.
- Proven serialization: `<BBI>` packed as `kind, stat_id, value`, then sent by `thunk_FUN_0059d760(0x17, &local_10, 6)`.
- Proven live sample: `07 01 00 00 00 00` in [live_run.stdout.log](<home>/Documents/<project-dir>/Azrok_Plaza/artifacts/ui-probes/live_run.stdout.log#L192).
- Strong inference: this is a late readiness/status transition packet, not part of the minimum PatHouse bootstrap.

### Best current server contract for `0x0017`

- Accept and log it.
- Do not use first `0x0017` as a trigger for early `S->C 0x0064`.
- If the server answers at all, answer with already-safe late-stage readiness/state packets only after scene/bootstrap state is valid.

## Verified `C->S 0x0064`

- Proven producer path: `Hansol_SceneStageHandler @ 0x00614370` stage 0 -> `SendC2S_0064_LocalBootstrapStatus @ 0x006130B0`.
- Proven wire send helper: `FUN_005ab710 @ 0x005AB710`.
- Proven wire form: exactly 1 byte, sent as `thunk_FUN_005ab6a0(0x64, local_9, 1)`.
- Proven conclusion: the larger local bootstrap preparation inside `SendC2S_0064_LocalBootstrapStatus` is not the wire payload.
- Proven direction split: inbound `S->C 0x0064` is a different contract that flips dispatch state before normal state-1 handling.

### Best current server contract for `0x0064`

- Treat it as a 1-byte bootstrap/progress flag report.
- Never raw-echo it as `S->C 0x0064`.
- Only send authoritative `S->C 0x0064` after state-0 bootstrap is complete and the self actor can safely exist.
