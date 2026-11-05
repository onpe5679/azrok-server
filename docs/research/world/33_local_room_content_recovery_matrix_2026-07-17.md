# Local-room content recovery matrix (2026-07-17)

This note turns the room hypothesis into a testable implementation boundary.
The normal sub-rooms are selected by the client-side loader; the server is not
the selector for these local scenes.  The server becomes relevant again for
shared-room membership and remote actors.

## Loader map

| Local index | WMB | Post-load code | Room | First content boundary |
|---:|---|---:|---|---|
| 0 | `playroom.wmb` | `0x65` | playroom | popup/content dispatch |
| 1 | `library_1.wmb` | `0x6A` | library | popup/content dispatch |
| 2 | `gym.wmb` | `0x66` | gym | popup id `0x41/0x42/0x43`, content key `0x73` |
| 3 | `magic.wmb` | `0x67` | magic | popup/content dispatch |
| 4 | `cook.wmb` | `0x68` | kitchen | popup/content dispatch |
| 5 | `shop.wmb` | `0x69` | shop | popup/content dispatch |

`FUN_00530FE0(local_index)` queues the local loader/post-load pair and
`GameManager_DispatchRoomCode @ 0x0050A0F0` performs the corresponding
`level_load`.  `FUN_006122C0(2)` is the confirmed Gym path.

## Gym boundary now proven

The native popup registry has:

- `0x41` = Push-up (`팔굽혀펴기`)
- `0x42` = Dumbbell (`아령`)
- `0x43` = Rope skipping (`줄넘기`)

All three use content/category key `0x73`.  There is no native
`switch(button_id)` for these values; `FUN_005E6960` matches the world
object's `(content key, CP949 action label)` against the 58-entry registry and
then presents the generic popup button.  The native continuation is a script
or content bridge into `FUN_006122C0(2)`, not a server ACK path.

The live Gym packet `C->S 0x0065` (`08 15 15 02 00 00 85 05 00 00`) is the
room-change report emitted after that local transition.  It is not the
dumbbell result and must not be echoed as `S->C 0x0065`.

## Current dynamic boundary

The attached x32dbg observer was run without binary patches or synthetic
packets.  In the current Gym scene, keyboard/mouse attempts did not reach
`ButtonQueue_Push`, `FUN_006122C0`, `C->S 0x0066`, or `C->S 0x0065`; the observer
log therefore contains only its attach/breakpoint/running records.  This is a
real input/content-world boundary, not evidence that Gym needs a server ACK.

The same observer remains useful for the next clean session.  Add/keep these
breakpoints when exercising a visible popup action:

```text
FUN_0051B1F0  popup hit-test return (expect 0x42 for Dumbbell)
FUN_005E6960  content-key/label match (expect 0x73 + 아령)
FUN_006122C0  local room/content continuation (expect index 2)
FUN_005AB760  C->S 0x0065 room report
```

One important negative result is now recorded so it is not mistaken for a
missing server response: the `FUN_00535660` keyboard branch that maps `B` to
the `0xBB/0xBC` local action is guarded by the room-code `100/0x6E` path.  The
active Gym scene reports `0x66`, where that branch intentionally does nothing.
Therefore a clean Gym reproduction must first reach the visible popup's own
button callback; sending `B` globally is not a valid substitute and no
synthetic `0x0065`/`0x0066` packet should be used to force it.

## Recovery order for every local room

1. Enter the room through the visible door and record `scene_opcode` and
   `logic_state` after the loading screen closes.
2. Trigger one visible object/NPC action.  Record the popup registry match and
   the local continuation before inspecting network traffic.
3. Only if a real non-self actor or persistent stat/item update is observed,
   add a server contract.  Do not synthesize a reply for an action that the
   client completes locally.
4. After local rooms are individually playable, enable the multi-client relay
   for room reports and movement.  `azrok_server.py` now tracks per-connection
   room membership and, only when a peer is present, rebuilds each affected
   recipient's roster with the verified S->C `0x0065` flush, `0x0066` actor
   record, and `0x0068` position record.  C->S movement is translated into the
   same `0x0068` position record.  This also removes ghosts when a player
   changes rooms instead of flushing another room's roster blindly.

This keeps the single-client no-patch path unchanged while making the second
client test observable and reversible.
