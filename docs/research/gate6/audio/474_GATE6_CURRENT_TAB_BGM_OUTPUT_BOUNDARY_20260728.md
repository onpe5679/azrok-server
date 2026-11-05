# Gate 6 current-tab BGM playback and output boundary (2026-07-28)

## Direct evidence

- **VERIFIED (active private HTTPS tab):** after the repaired launch gesture, the page owns one BGM media element for original `intro.mp3`. It reports `paused=false`, `muted=false`, `defaultMuted=false`, `loop=true`, `readyState=4`, and its current time advanced from 15.06 seconds to 21.79 seconds while inspected.
- **VERIFIED (visible recovery control):** the running page's `BGM 다시 재생` button was activated. The same element remained unpaused and unmuted at 6.18 seconds, then advanced to 16.08 seconds without ending.
- **VERIFIED (current two-session PatHouse run):** both independently connected `player` and `peer111` browser sessions selected original `PetHouse.mp3`, each with `paused=false`, `muted=false`, `readyState=4`, and `loop=true`. Five seconds later their playback times advanced independently (36.27→49.94 and 46.86→60.53) without ending.
- **VERIFIED (asset decode):** the served original assets are non-silent: `intro.mp3` measured -13.6 dB mean / 0.0 dB maximum, and `PetHouse.mp3` measured -13.3 dB mean / 0.0 dB maximum with FFmpeg `volumedetect`.
- **VERIFIED (host launch flags):** the local browser and host processes have neither `--mute-audio` nor an audio-disable/output-none launch flag.

## Boundary

- **NOT VERIFIED:** physical speaker audibility. Browser DOM playback and decoded-audio measurements do not prove that a selected speaker, Windows volume mixer route, or physical output device is audible.
- **NOT VERIFIED:** native Wine Quartz/GStreamer BGM. This evidence concerns the same-origin original-MP3 browser fallback only.

## User-visible recovery

Reload the private page once, click `오디오 활성화 후 Azrok 실행`, then use the visible `BGM 다시 재생` button if the tab had been restored from an older load. The button re-arms the same original BGM element inside a real browser gesture.
