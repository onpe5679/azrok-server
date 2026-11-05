# Gate 6 Web BGM gesture playback verification (2026-07-28)

## Result

- **VERIFIED (private HTTPS runtime):** the original `PetHouse.mp3` browser containment now invokes `HTMLAudioElement.play()` at the first launch gesture instead of waiting for a guest Present count. The prior gating left the fallback in `armed` and could lose browser user activation.
- **VERIFIED (private HTTPS runtime):** after the corrected launch, the DOM exposed `webBgmFallback=playing`, `paused=false`, `muted=false`, `volume=0.65`, and `readyState=4`. `currentTime` advanced to `2.034437` seconds during the two-second observation, directly proving the browser decoded and advanced the original MP3 rather than merely accepting a play request.
- **VERIFIED (package/static):** the active fallback asset is the unmodified archive member `Data/Sound/PetHouse.mp3`, SHA-256 `DD1234D6831992F8DFD9A46FDF898FB31FD310FBBBCAC4512CEB8AEADA4BD3E0`.

## Boundary

This proves the current PetHouse music containment path within the private service. It does **not** prove an audible human check, native Wine MP3 playback, or automatic BGM transitions for all maps/minigames. Those remain separate Gate 6 requirements.
