# Packet Flow

## Transport Format

TCP framing is:

- `u16 payload_size`
- `u16 opcode`
- `payload[payload_size]`

The transport layer accumulates the byte stream in `CClientPeer`, then pushes
decoded packets into a ring buffer. The main logic thread dequeues from that
buffer and dispatches the packet through the runtime vtable path.

## Runtime Inbound Path

Confirmed path:

1. `CClientPeer` stream parser receives TCP bytes.
2. Packet is enqueued into the ring buffer.
3. `0x593E40` dequeues `[opcode, payload_ptr, payload_size]`.
4. Dispatch goes through the final runtime object, not the early JSDB stub.
5. Runtime handler is `CLogicManager::0x594310`.

This corrected the earlier assumption that `0x5927D0` was the final live
handler. `0x5927D0` is real, but only for an earlier vtable stage.

## Observed Client Sequence

Typical current run:

1. Client connects.
2. Client sends `0x0000` hello.
3. Heartbeat `0x0016` begins.
4. Client sends `0x0004` character creation.
5. Server sends `0x0002` and `0x0003("Data\\Space\\...")`.
6. Client sends `0x0007` setup request.
7. Server sends `0x0007`, `0x0005`, `0x0010`, `0x0011`.
8. Client sends `0x0001`.
9. Client sends `0x0017`.
10. Server sends a state-1 bootstrap sequence.
11. Client either crashes or remains in heartbeat-only loading.

## Current Important Observation

The first `0x0017` is the transition point where state-1 behavior begins to
matter. Everything before that is now relatively stable.

## Load Progress Interpretation

There are two distinct states that can look similar visually:

- hard fault before `0x0064` completes
- partial loading progress where the bar moves but the final close path never
  completes

The latest investigation indicates that a "half-filled" loading bar means the
game likely advanced deeper into the scene-init path, but not far enough to
finish the loading popup close path.
