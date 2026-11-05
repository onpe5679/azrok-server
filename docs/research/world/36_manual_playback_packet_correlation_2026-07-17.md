# Manual playback packet correlation (2026-07-17)

This note records the first human-played Gym session and separates packet
evidence from an earlier interpretation.  The original client and resources
were not modified.

## Observed packet counts

Capture: `captures/packets_20260717_081659.txt`

| Direction/opcode | Count | Wire meaning established by payload/control flow |
|---|---:|---|
| C→S `0x0066` | 108 | movement report: kind + from `(x,y)` + to `(x,y)` + client movement fields |
| C→S `0x0067` | 12 | stop/direction report: kind + `(x,y)` + mode + angle |
| C→S `0x0065` | 1 | local-room membership report `<kind,direction,x,y>` |
| C→S `0x006C` | 3 | local E/community-target toggle report |

The `0x0066` coordinate chain is internally consistent: one packet's arrival
coordinates become the next packet's origin, and the first origin matches the
server-supplied spawn pose.  This proves that the player moved normally in the
manual session.

## The single `0x0065` is not a dumbbell request

The only `0x0065` is packet `#157`:

```text
08 15 15 02 00 00 85 05 00 00
```

It is emitted at Gym entry as the room report (`kind=8`, direction `0x15`,
`x=0x215`, `y=0x585`).  The capture then continues with ordinary heartbeats;
there is no second C→S `0x0065` at the dumbbell click boundary.  Its payload
matches the native `FUN_005AB760` room-report builder and not a Gym reward
structure.  The server therefore must not invent an ACK for this packet.

The prior description of this frame as “the dumbbell click” was a direction
and timing mislabel.  Gym content selection remains the local data-driven
popup path (`0x73`, IDs `0x41/0x42/0x43`) documented in research notes 32 and
34.  A real server-side content contract should be added only after a fresh
single-action capture shows a new C→S sender or an authoritative state change.

## Server implementation consequence

`azrok_server.py` now:

1. records the decoded `0x0065` room membership per connection;
2. relays verified movement as direction-correct S→C `0x0068` position records
   only when another client is in the same room;
3. rebuilds affected rosters with S→C `0x0065` flush + `0x0066` actor + `0x0068`
   position records on room entry/change;
4. leaves `0x0067` and `0x006C` un-echoed until their direction-specific
   peer-state contracts are captured.

This preserves the working single-client path while making the next
two-client experiment observable.  Empty inventory, quest, and stat displays
remain a separate initial-state (`S→C 0x0007/0x000A/0x000B`) data task; the
manual session's empty UI is evidence of missing data, not proof that a Gym
ACK is required.

## Input/observation note

The manual session proves the game accepts real input and reaches Gym/NPC
content.  Low-integrity automation can still fail to deliver input to the
elevated legacy window; that tooling limitation must not be promoted to a
gameplay diagnosis.  For dynamic traces, attach x32dbg after a clean launch,
capture the actual popup/transition sender, and detach before comparing a
second manual run.
