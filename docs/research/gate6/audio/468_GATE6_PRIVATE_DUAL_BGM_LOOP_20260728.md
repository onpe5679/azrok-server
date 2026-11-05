# Gate 6 private dual-session BGM loop (2026-07-28)

## Result

- **VERIFIED (fresh private browser sessions):** two new authenticated HTTPS/WSS browser sessions were opened against the restricted `<lan-ip>` service. Both were launched by the visible `오디오 활성화 후 Azrok 실행` user-gesture control.
- **VERIFIED (browser media state):** after launch each independent fallback element reported `paused=false`, `muted=false`, `readyState=4`, and advancing time. Both exposed the post-launch `BGM 다시 재생` control in the running-client controls.
- **VERIFIED (loop behavior):** after the primary session had advanced beyond the original PetHouse MP3 duration, its fallback element remained `paused=false`, `ended=false`, and had wrapped to `currentTime=0.661477`. The other session continued at `currentTime=52.501025`. This is direct private-browser loop evidence for the non-silent original MP3 asset, not an SFX-only observation.

## Boundary

- **NOT VERIFIED:** speaker-level audibility in the user's pre-existing tab; browser media-state and decode/loop evidence cannot substitute for that physical-output observation.
- **NOT VERIFIED:** automatic map-driven switch among all 15 tracks remains pending a natural guest `FS.open` transition.
- **NOT VERIFIED:** the native Wine Quartz/GStreamer MP3 path remains broken as documented in 461/463; this result covers the browser containment route only.
