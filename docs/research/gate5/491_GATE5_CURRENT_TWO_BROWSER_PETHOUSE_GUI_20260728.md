# 491 Gate 5 current two-browser PatHouse and GUI run (2026-07-28)

## Direct result

- **VERIFIED (bootstrap ordering):** launching the two browser guests at the
  same time left the peer at Wine window creation.  Closing only that stalled
  peer and launching it after the primary had reached its live socket restored
  normal progress.  This repeats the one-origin IDBFS serialization boundary
  from 469; simultaneous bootstrap is not treated as a multiplayer success.
- **VERIFIED (two independent browser sessions):** the first browser rendered
  the original PatHouse 3D scene as `player`, while the sequential `peer111`
  browser reached its original character-selection screen, selected the
  existing `Player` record through the visible canvas UI, loaded the world,
  and rendered its own PatHouse 3D scene.  No game packet was fabricated.
- **VERIFIED (shared private core + GUI):** the loopback core GUI reported
  `Clients=2`, `ConnectedClients=2`, `Plaza=0`, and transition
  `2 clients · Plaza 0 / PatHouse 0 · heartbeat 정상`.  Entities `65` and
  `66` simultaneously exchanged normal `0x0016` heartbeat packets.
- **VERIFIED (real state stream):** after the peer's visible selection, its
  natural server stream included canonical `0x0007` restore, `0x0005`,
  `0x000A`, `0x000B`, and client `0x0017`/`0x0008`, followed by heartbeats.
  The primary had the same class of natural stream.  This is more than two
  independent render-only pages.
- **VERIFIED (sound containment):** both session status datasets reported
  `webBgmFallback=playing`, `transport=media-element`; each was started by its
  own visible launch click.

## Boundary

- **NOT VERIFIED:** natural exit through `dm_door_0003_057`, Plaza admission,
  `0x0066` roster upsert, `0x0068` movement relay, reciprocal remote rendering,
  and targeted `0x0067` leave.  Current `Plaza=0` and no actor roster means the
  two PatHouse sessions do not yet prove those multiplayer functions.
- **NOT VERIFIED:** current GUI names remained blank even though the peer's
  rendered character-selection UI identified `Player`; GUI identity binding
  needs its own protocol/UI correlation before it can be claimed.
