# 507 Gate 5 current private dual-PetHouse session (2026-07-28)

## VERIFIED

- The retained private `player` browser tab stayed running while exactly one
  additional in-app browser tab launched the original
  `run_azrok_peer111.bat` guest.  The two tabs use distinct original guest
  accounts, `player` and `peer111`; no synthetic game packet was sent.
- Startup was sequential: the primary had already reached its live PetHouse
  scene before the peer launch, avoiding the known shared-IDBFS cold-bootstrap
  collision.  Total game tabs were two.
- The peer passed original character selection and cutscene into a visible
  3D PetHouse workload.  Its settled 120-Present command shape was 18,480
  DrawUP calls (154/frame) at a 32.9-FPS HUD.  The retained primary
  simultaneously showed 19,080 DrawUP calls (159/frame), 36.4 FPS, and the
  original `PetHouse.mp3` track.
- The loopback GUI API at port 9300 concurrently reported one core at port
  9200 with `clients=2`, `connected_clients=2`, and two connected identities:
  entity 96 `player/Azrok1` and entity 97 `peer111/Player`.  Both had normal
  `0x0016` heartbeat as their last opcode and nonzero receive/transmit counts.
- The TCP listener inspection remains private-only: core/GUI on loopback and
  browser frontends only on RFC1918 and Tailscale addresses, with no wildcard
  or public bind.
- After the simultaneous evidence was captured, the peer tab was closed while
  retaining the primary tab.  The same GUI then returned to
  `clients=1`/`connected_clients=1` with only `player`, so the concurrency test
  did not leave a second game process or client load in the work session.

## NOT VERIFIED

- This current run reports `plaza_clients=0`, `peer_count=0`, and
  `visible_remote_actor_count=0` for both players.  It proves two original
  clients share one private core and GUI while rendering PetHouse, but does
  not prove the current natural Plaza entry, reciprocal `0x0066` actor upsert,
  `0x0068` movement relay, or `0x0067` targeted leave.
