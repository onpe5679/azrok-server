# Gate 5 clean sequential private-session admission (2026-07-28)

## Method

- Removed two old loopback test tabs and verified the shared core GUI reached `clients=0` before the new run.
- Kept all network exposure private: HTTPS assets and token-authenticated WSS on `<lan-ip>`, with the game core only on `127.0.0.1`.
- Started `player` first, then started `peer111` after the first client reached its character state. Both launch clicks were real page gestures and therefore armed the web BGM fallback.

## Direct evidence

- **VERIFIED (GUI/core):** the core reports `clients=2`, with distinct bound identities `#44 player/Azrok1` and `#45 peer111/Player`; the GUI transition label reports two clients with normal heartbeat.
- **VERIFIED (two rendered browser sessions):** the `peer111` selection was clicked through the native rendered character UI and reached a PatHouse 3D scene. The already-running `player` tab concurrently rendered its own distinct PatHouse 3D scene.
- **VERIFIED (music continuity):** both freshly launched tabs had a BGM media element with `paused=false` and `readyState=4` during guest initialization; `peer111` continued playback through character selection and PatHouse entry.
- **VERIFIED (server GUI boundary):** this run is independent of the Codex control GUI: the browser clients communicate through the private WSS bridge to one loopback core, while the GUI reads only that core's state API.
- **VERIFIED (natural Plaza probe):** a visible PatHouse doorway click was sent through the browser input path. It emitted no `0x0019`; the player's recent C2S record remained heartbeat-only, so no transition was inferred or fabricated.

## Boundary

- **NOT VERIFIED:** natural entry of both clients into Plaza, remote actor roster admission, reciprocal actor rendering, movement relay, and targeted leave. Both current core records remain in the pre-room/unknown state and report zero Plaza clients.
- **NOT VERIFIED:** physical speaker audibility. This run proves browser media playback state, not physical audio output.
