> **ARCHIVED (2026-07-17).** 이 문서는 대체됨 — 현재 확정 사실은 ../INDEX.md 참조.

# Two-client PatHouse roster: wire emission versus client state (2026-07-17)

## What was reproduced

After a clean restart, two real Azrok clients connected to the same server
(`9207`) and both completed the character-state bootstrap (`C->S 0x0005` /
`0x0007`). The server grouped them internally as `PatHouse (local)` only
after the full `0x0007` packet; this key is internal and is never sent on the
wire.

The server then emitted a direction-correct roster to both recipients:

```text
S->C 0x0065 (empty flush)
S->C 0x0066 (26-byte actor record, real entity id)
S->C 0x0068 (24-byte actor position, real entity id)
```

Capture: `captures/packets_20260717_103943.txt`.
The final counts were `S->C 0x0065=3`, `0x0066=2`, and `0x0068=2` (the extra
flush is the single-client bootstrap rebuild). The control panel showed two
connected players, entity IDs 2 and 3, both `PatHouse (local)`.

## Client-side result

The primary client showed no second avatar. The low-temperature x32dbg
observer on PID 134448 recorded zero hits at the state-1 handlers and actor
lifecycle boundaries (`0x00615B20`, `0x00615B50`, `0x00615D50`, and the
associated ensure/finalize/look-up sites). The contemporaneous watch values
were phase `2`, logic state `0`, self actor ID `0`, scene opcode `100`.

This separates two facts that must not be conflated:

1. Server roster serialization and TCP emission are proven with real entity
   metadata; no speculative ACK or client-memory write was used.
2. The PatHouse client is not dispatching these state-1 roster opcodes in its
   current bootstrap state, so wire delivery alone does not create a remote
   actor.

The correct next target is the authoritative self-actor/state-1 prerequisite,
not another 0x0066 field-map guess. The roster payload and server grouping
remain available for the next fresh run.

Evidence: `artifacts/dynamic-analysis/PID134448_TWO_CLIENT_ROSTER_TRACE_20260717.md`,
`artifacts/dynamic-analysis/x32dbg_roster_pid134448_20260717_104151.jsonl`,
and screenshot `artifacts/screens/roster_primary_after_secondary.bmp`.
