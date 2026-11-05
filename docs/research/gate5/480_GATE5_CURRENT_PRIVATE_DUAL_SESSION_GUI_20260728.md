# Gate 5: current private dual-session GUI admission

Date: 2026-07-28 KST

## VERIFIED

- The current browser session opened exactly two game tabs.  The primary used
  account/name `player`/`Azrok1`; the second used the named peer launcher and
  reached account/name `peer111`/`Player`.  This is account-state separation,
  not a cloned browser identity.
- Both original-client tabs completed character selection and their tutorial
  path, rendered PatHouse locally, and continued the `0x0016` heartbeat.
- The shared local GUI (`127.0.0.1:9300/api/state`) reported `Clients=2`,
  `ConnectedClients=2`, and transition `2 clients · Plaza 0 / PatHouse 0 ·
  heartbeat 정상`; both per-player records were connected.  The second tab had
  its web BGM fallback disabled solely to avoid mixing two tracks during the
  concurrency check; the primary BGM continued separately.

## NOT VERIFIED

- Current-run natural outside-door entry into Plaza from both browser tabs.
- Current-run reciprocal remote actor rendering and movement relay
  (`0x0066` upsert / `0x0068` position / targeted `0x0067` leave).  Two
  healthy PatHouse heartbeats are not a substitute for that multiplayer proof.
