# Client roster and receive-buffer limits (2026-07-17)

This note records a direct static audit of three client-side safety contracts
and the corresponding server/control-panel changes.  The inspected executable
was the unmodified `Azrok_original.exe`, MD5
`eac34b226ff54bcd2621a2c2178af577`, imported into a temporary Ghidra 12.0.4
headless project.  The analysis did not patch the executable or write live
client memory.

## 1. `S2C 0x0065` is an all-actor reset, not a remote-only flush

`HandleS2C_0065_FlushRemoteActors @ 0x00615B20` delegates to
`FUN_0050D5D0`.  The latter performs these operations in order:

1. Calls `FUN_00526F10(gm + 0x35C20)` unconditionally for the fixed actor
   state used by the local/self actor.
2. Walks the remote-actor list at `gm + 0x4A723` and calls the same teardown
   routine for every entry.
3. Clears the remote list.

`FUN_00526F10` removes the entities at actor offsets `+0x99` and `+0x31C`
and clears the corresponding pointers and UI/state fields.  Therefore the
operational meaning is **fixed self/full actor state first, remote roster
second**.  It is unsafe to auto-send this packet after the authoritative self
actor is live.

The binary does not require a following `0x0066`, so the label
"remote roster flush followed by repopulate" is not established by this
handler.  Likewise, an original-server placement before self creation remains
a hypothesis until a trace proves it.  The supported server path continues to
use peer-only `0x0066` upsert, `0x0068` position, and targeted `0x0067` leave.

## 2. Remote actor pool: 100 visible peers per client

`RemoteActorPool_AllocUnusedSlot @ 0x0050D690` scans indices `0..99`.  Each
slot is `0x347` bytes at `gm + 0x35F67 + index * 0x347`; the in-use byte is at
slot `+0x8F`.  When all 100 are used, the allocator returns null.

`RemoteActor_EnsureFrom0066Record @ 0x0050D790` checks that return value and
returns without constructing an actor when it is null.  The `S2C 0x0066`
handler at `0x00615B50` advances through its 26-byte records and performs the
follow-up only for a non-null actor.  The 101st remote is therefore skipped
without an immediate crash.

The physical visual ceiling of one client is:

```text
1 local/self actor + at most 100 remote actors = 101 visible players
```

The server now enforces the 100-remote cap per recipient, retains already
visible actor IDs before filling free slots, suppresses movement relays for
actors that recipient could not render, and uses targeted `0x0067` to free a
slot on departure.  It never uses `0x0065` for this lifecycle.

## 3. Receive reassembly buffer: 8192 bytes total, 8188-byte payload

The constructor `FUN_0061BE80` places the receive buffer at peer
`+0x2050`, the cursor at `+0x4050`, and remaining length at `+0x4054`.
The inline byte buffer is therefore exactly `0x2000` (8192) bytes.

`FUN_0061C0E0` first copies the four-byte packet header, trusts the header's
16-bit declared payload length, and then copies payload bytes at
`peer + 0x2050 + cursor`.  There is no comparison against the 8192-byte
allocation before the copy.  Consequently:

```text
maximum safe declared payload = 8192 - 4 = 8188 bytes
8189 bytes overwrites receive metadata
floor(8188 / 26) = 314 complete actor records
315 * 26 = 8190 bytes, which is unsafe
```

The 100-slot actor pool is the earlier practical roster limit, but the
8188-byte payload boundary applies centrally to every outbound opcode.  The
server packet builder now rejects larger payloads explicitly, and manual GUI
injection returns that error instead of causing an HTTP 500.

## 4. Control-panel visibility

The server snapshot and GUI expose:

- connected and Plaza client counts;
- per-client room peers, actually admitted remote actors, and cap overflow;
- 100 remote slots / 101 visible players including self;
- 8192-byte receive buffer / 8188-byte safe payload;
- 26-byte actor records, 314 by buffer arithmetic, 100 effective by pool;
- the corrected `S2C 0x0065` all-actor-reset warning.

These are monitoring values and safety enforcement only.  They do not modify
the original binary or bypass the client's state machine.

## 5. Isolated verification

The following checks passed against the current server module:

- an 8188-byte payload builds a packet of exactly 8192 bytes;
- an 8189-byte payload raises the explicit size error;
- 101 real peers produce 100 `S2C 0x0066` upserts and 100 `0x0068`
  positions for one recipient, with no `0x0065`;
- movement from the unadmitted 101st peer is not relayed to that recipient;
- departure of an admitted actor emits one targeted `0x0067` and releases
  that visible slot;
- `azrok_server.py`, `azrok_control.py`, and `azrok_control_page.py` compile.

