# State-1 targeted departure lifecycle with S2C 0x0067 (2026-07-17)

This note completes the minimum two-client Plaza actor lifecycle without any
binary patch or client-memory write:

```text
join     -> peer S2C 0x0066 actor upsert + S2C 0x0068 position
movement -> C2S 0x0066 translated to peer S2C 0x0068
leave    -> peer S2C 0x0067 <departed actor id>
```

S2C `0x0065` is never part of this live lifecycle because it destroys the
fixed self actor as documented in note 51.

## 1. Static contract

Ghidra resolves the state-1 handler as:

```text
HandleS2C_0067_RemoveRemoteActor @ 0x00615D00
  -> auxiliary target/mirror cleanup by actor id
  -> FUN_0050D910(actor_id)
     -> FUN_0050E6C0
        -> scan base+0x4A723 remote actor list
        -> compare actor+0x2F8 id
     -> unlink and teardown the matching remote actor
```

The handler reads exactly one DWORD from payload start, performs no payload
length check, and has no repeated-record loop. The canonical wire contract is
therefore exactly four bytes, little-endian `<I actor_id>`, one actor per
packet. A shorter packet is unsafe and extra bytes are ignored.

The fixed self slot at base+0x35C20 is not searched, but the auxiliary cleanup
has no explicit self guard. The server consequently enforces:

```text
departed_entity_id != recipient_entity_id
```

## 2. Server implementation

`azrok_server.py` now snapshots old-room peers before changing or deleting the
departing client's metadata. `_notify_room_departure` emits one S2C `0x0067`
only when:

- the old room is the state-1 Plaza room;
- the recipient is another still-connected member of that room;
- the departed id is positive and differs from the recipient id.

Local mode-0 rooms and the departing source receive nothing. C2S `0x0065`
room changes call the same old-room removal path before the source membership
is updated. Disconnect cleanup calls it before removing `client_meta`.

The elevated scheduled helper gained a narrowly validated one-shot close
request for runtime tests. It accepts one PID only after verifying that the
process path is this workspace's `Azrok.exe`; it does not stop the shared
server or the other client.

## 3. Isolated contract test

An in-memory server harness with three fake connections verified:

- departing Plaza entity 2 produced exactly one packet to Plaza entity 3;
- packet header was opcode `0x0067`, payload length 4;
- payload decoded to actor id 2;
- a mode-0 local-room departure produced no packet.

`python -m py_compile azrok_server.py tools/read_dispatch_watches.py` also
passed.

## 4. Live two-client proof

Evidence capture: `captures/packets_20260717_143355.txt`.

Two real clients reached the same `0064-only` outdoor Plaza and received the
normal peer `0x0066 + 0x0068` upserts. A diagnostic S2C `0x0068`, marked
`origin=manual`, separated the overlapping peer models for the removal visual
check; it did not create a fake actor and used the real connected entity id 3.

Before disconnect, the surviving window visibly rendered both `Azrok1` and
`Guest`. The elevated helper then closed only the second real process. The
server recorded:

```text
seq 289  14:45:12.793  S2C 0x0067  len=4  origin=relay
payload: 03 00 00 00
```

There was exactly one S2C `0x0067` in the capture. The `Azrok1` remote model
disappeared while the surviving `Guest` self model remained. Twelve seconds
later the client was still responding, the server still had one connected
player, and four additional C2S/S2C `0x0016` heartbeat packets had completed.

This proves targeted peer removal, self preservation, and post-departure
session survival in the real client.

## 5. Test-input note

Frida `17.15.5` and `frida-tools 14.10.4` were installed for the existing
`tools/azrok_frida_input.py` test harness. Attach to the elevated 32-bit client
worked without another UAC prompt. A Plaza click produced real movement relay
records, but its coordinate path also drove the actor outside the ordinary
visible region, so automated content exploration still needs room-specific
safe click targets. This runtime input instrumentation is a test harness; it
is not part of the zero-patch gameplay/server requirement.
