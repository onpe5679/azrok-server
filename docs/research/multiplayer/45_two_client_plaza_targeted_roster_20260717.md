# Two-client 0064-only Plaza roster with entity-targeted sends (2026-07-17)

> **SUPERSEDED SAFETY NOTE (2026-07-17):** The wire capture below is useful,
> but its proactive empty S->C `0x0065` is unsafe in active Plaza. Doc 51 and
> x32dbg prove it tears down the self actor and causes the minimap AV at
> `0x005F3AF4`. The supported relay now emits only peer `0x0066+0x0068`
> upserts; no automatic `0x0065` is sent.

This run is a protocol-only interoperability observation.  No executable or
runtime memory patch was used.  The launcher used `AZROK_PLAZA_REPLY_MODE=0064`
and the legacy `0x0019` memory shortcut stayed disabled.

## Run and boundary

- Capture: `captures/packets_20260717_122202.txt`
- Primary and reused secondary were connected to the same listener `127.0.0.1:9207`.
- Both clients completed the real `C->S 0x0005` / `C->S 0x0007` PatHouse bootstrap.
- The control API sent the already observed `S->C 0x000D[00]` independently to
  entity 2 and entity 3 using the new optional `entity_id` target.  This is an
  operator-selected transition prelude, not a synthesized client response.

The capture records, in order:

1. Entity 2: manual `S->C 0x000D[00]`, five natural `C->S 0x0016[01]` /
   `S->C 0x0004[01]` calibration exchanges, then natural `C->S 0x0064[01]`.
2. Entity 2: authoritative `S->C 0x0064` (27-byte payload), with no `S->C
   0x006E` ready commit.
3. Entity 3: the same manual `0x000D[00]` prelude and natural five-sample
   calibration, followed by `C->S 0x0064[01]` and authoritative `S->C 0x0064`.
4. On each `C->S 0x0064`, the server assigned the direction-verified Plaza
   grouping (`wire kind 0x1B`, label `plaza (0064-only)`) and rebuilt the
   recipient roster.  The capture therefore contains both directions of:

   ```text
   S->C 0x0065  empty roster flush
   S->C 0x0066  actor record (entity 3 to entity 2; entity 2 to entity 3)
   S->C 0x0068  actor position record
   ```

The actor records are built from the two real connected client metadata rows;
the server did not claim a client that was not connected.  The relevant wire
payloads include entity IDs `0x02` and `0x03`, both type `0x02`, and name slot
`Player`.

## Result and limits

This is direct wire evidence that two independent clients can reach the
supported `0x0064`-only Plaza boundary and that the server emits the verified
direction-specific roster protocol to both peers.  The clients exited during
the end of the automated run before a screenshot could be taken, so a visible
second-avatar render is still a separate UI verification item.  No claim is
made here that the state-1 client dispatch gate has been proven from this run;
the direct `+0x163D8/+0x163E4` watch must be read while a client remains alive.

The new control-path details are documented in the server source:

- `azrok_server.py`: `inject(..., entity_id=...)`, `PLAZA_ROOM_KIND`, and the
  C2S `0x0064` Plaza roster boundary.
- `azrok_control.py`: `/api/send` accepts optional `entity_id`.

## Follow-up simultaneous run

Capture `captures/packets_20260717_125019.txt` reproduced the same boundary
with both clients kept alive until both requests were issued:

- Entity 2 and entity 3 were both `PatHouse (local)` before the transition.
- Two manual `S->C 0x000D[00]` packets were issued back-to-back.
- Both clients emitted the natural five-sample `0x0016/0x0004` calibration,
  then each sent `C->S 0x0064[01]` and received the authoritative 27-byte
  `S->C 0x0064` with no `0x006E`.
- The server emitted both directions of `S->C 0x0065`, `0x0066`, and `0x0068`
  again, with real entity ids 2 and 3.

This run closed after the two Plaza boundaries, so a visible-avatar screenshot
and a live owner watch were still not captured.  It does, however, rule out
the earlier single-peer crash as a universal `0x000D` failure: the same
packet is reproducible when both peers are present and transitioned together.
