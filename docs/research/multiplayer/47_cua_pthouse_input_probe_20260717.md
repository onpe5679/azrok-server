# CUA PatHouse input probe (2026-07-17)

This note records a real-window input check after the dispatch-owner observer
was corrected.  The game was restarted cleanly through the approved elevated
task; two clients reached the PatHouse bootstrap and the server/control panel
were relaunched on ports 9207/9300 without opening a browser.

## Observed

- The first client entered PatHouse and displayed the normal tutorial NPC/text.
- The second client also entered PatHouse; the server capture contains its
  natural `C->S 0x0007` bootstrap and calibration `0x0016` samples.
- Computer-use clicks on the visible door, floor, tutorial NPC and dialogue
  region were accepted by the game: the top tutorial sentence changed several
  times and the dialogue overlay was dismissed.
- No `C->S 0x0066`, `0x0067`, `0x0065`, or `0x0019` appeared in this fresh
  capture.  The character remained in the local room.  This is a negative
  result for this newly selected/tutorial-gated character state, not proof
  that the client input path is broken; the user's earlier manual session
  already produced Gym entry and one `0x0065` packet.  That single sample is
  now recorded conservatively: its gym-kind byte is strong evidence of room
  association, but it is not yet proven to be a dumbbell click or a door/
  arrival report.  No synthetic ACK is implemented.

Evidence: `captures/packets_20260717_131150.txt` (two-client input probe) and
`captures/packets_20260717_131751.txt` (fresh single-client restart with the
corrected owner watch).  The latter still contains only bootstrap, heartbeat,
and zone packets; no movement/content opcode was emitted.

## Runtime owner watch

The live read-only watch now finds the embedded CLogic object directly:

```text
gm                  = 0x00163280
logic_controller    = 0x0017B820 (gm + 0x185A0)
owner vptr          = 0x006A618C (CLogicManager)
dispatch_mode       = 0
dispatch_gate       = 0x00163280
gate candidate      = gm = 0x00163280
gate matches gm     = true
ip-buffer candidate = gm+0x31822 = 0x00194AA2
gate matches buffer = false (expected; buffer is a separate argument)
```

The live gate equals the outer GameManager pointer, matching the corrected
instruction-level argument order at `FUN_00594130`.  The separate
network-buffer candidate `gm+0x31822 = 0x00194AA2` is exposed only as a
connection-string diagnostic; a mismatch with it is expected and is not a
failure.  The pre-promotion `CLogicJSDB` vtable (`0x006A6154`) and promoted
`CLogicManager` vtable (`0x006A618C`) are both scanned.

No process memory or executable bytes were modified by this probe.
