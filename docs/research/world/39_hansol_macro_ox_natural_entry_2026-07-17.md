# Clean 0x000D macro result: natural OX entry — 2026-07-17

This is a controlled follow-up to the same-server two-client run. The
secondary client was in PatHouse(local), the primary readiness fields were
valid (`phase=2`, `scene=100`, transition vtables 4/4, clean pan-create
fingerprint), and the existing elevated x32dbg session was attached to the
secondary with low-temperature room/transition breakpoints before the test.

## Packet chain

The control panel sent exactly one documented `S→C 0x000D` packet (`origin =
macro`). The secondary then produced the natural calibration sequence:

```text
S→C 0x000D payload=00                 # macro, one packet
C→S 0x0016 payload=01 × 5             # transition calibration requests
S→C 0x0004 payload=01 + timestamp × 5
C→S 0x0064 payload=01                 # client stage-0 report
S→C 0x0064 payload=27B, entry_kind=0x0A
```

The relevant lines are in
`captures/packets_20260717_095850.txt` around the manual/macro `0x000D`
record and the later C→S/S→C `0x0064` pair. No speculative `0x006E` or
memory-write shortcut was used.

## Visible result

The secondary displayed the OX quiz scene (`OX지존` title, quiz map and local
player), not Plaza. This is a successful, reproducible alternate-space entry,
not a Plaza failure. It confirms the current `0x000D → calibration → 0x0064`
chain is wired to the OX/Hansol route under the present reply mode.

The x32dbg observer also saw the generic transition resolver become very hot
under the macro (97 hits in roughly 25 seconds). No further macro or input was
sent; the observer was allowed to time out/detach so the client stayed
responsive. Raw trace and the observer result are kept under
`artifacts/dynamic-analysis/x32dbg_room_pid131748_20260717_100905.jsonl` and
the corresponding `.ready` marker.

## Consequence for the roadmap

Do not label this chain as the Plaza route. Keep it as the validated OX
entry/regression baseline. Plaza still requires the separate local/server
room-code path; next experiments must arm the observer before the Plaza door
action and capture the first C→S room report rather than reusing this macro.
The focused trace also resolved the internal boundary: `0x000D` entered
`FUN_00568770` direct-to-Plaza, enqueued scene `0x6E` through `0x0050A7F0`,
ran cleanup, reset calibration at `0x0059DE50`, and reached the natural
`C→S 0x0064 payload=01`. It did not reach `0x005AB760/0x006122C0` or a
C→S `0x0065` sender. The resolver at `0x00611CD0` then became a hot polling
site (285 hits), so it was removed from future room profiles. The secondary
was left unresponsive after the observer detached; it is being recovered by
a full clean stop/relaunch rather than further input or macro injection.
