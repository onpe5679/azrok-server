# Gate 6 web BGM re-arm control (2026-07-28)

## Result

- **VERIFIED (private browser runtime):** while the fallback was active, the private page reported `paused=false`, `muted=false`, `readyState=4`, and `currentTime=49.563604` for the original `PetHouse.mp3` URL. The original MP3 asset is therefore decoded and advancing in the browser media pipeline.
- **VERIFIED (asset analysis):** `PetHouse.mp3` has non-silent decoded content (`mean_volume=-13.3 dB`, `max_volume=0.0 dB`) in the extracted original asset.
- **VERIFIED (implementation):** the page now exposes `BGM 다시 재생` both before launch and in the running-client controls. Its click handler is a real user-gesture recovery path: it clears mute, sets fallback volume to `1`, re-arms the manager, and calls the existing `HTMLAudioElement.play()` path during that click.

## Boundary

- **NOT VERIFIED:** speaker-level audibility on the user's already-loaded tab. A page loaded before this change has to reload once to receive the running-client recovery control; the private HTML endpoint is served with `Cache-Control: no-store`.
- **NOT VERIFIED:** natural in-game BGM transition coverage or native Wine Quartz/GStreamer BGM output; those boundaries remain as recorded in 465/463.
