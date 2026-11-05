# Gate 6 BGM launch-gesture regression repair (2026-07-28)

## Finding

- **VERIFIED (source):** the web BGM fallback constructed and armed the original `PetHouse.mp3` media element, but `startAzrok()` did not invoke its `begin()` function. The launch click therefore started only the guest; the user had to separately press `BGM 다시 재생` for any browser media play request.
- **VERIFIED (repair):** `startAzrok()` now invokes `rearmAzrokWebBgm()` synchronously within the real launch click, before its asynchronous JIT/guest preparation. This retains the browser user activation required by `HTMLMediaElement.play()`.

## Runtime evidence

- **VERIFIED (private HTTPS fresh page):** clicking `오디오 활성화 후 Azrok 실행` produced the fallback state `playing`, `paused=false`, `muted=false`, `readyState=4`, and no playback error for original `PetHouse.mp3`.
- **VERIFIED (continuity):** five seconds later the media element remained unpaused and unmuted with its playback time advanced; browser console had no warning or error entries.

## Boundary

- **NOT VERIFIED:** speaker-level audibility on the user's already-open physical device. That tab must reload because the private server deliberately sends `Cache-Control: no-store`, then launch through the updated single click.
- **NOT VERIFIED:** native Wine Quartz/GStreamer BGM remains broken; this is the same-origin original-MP3 browser containment path, not a claim that guest PCM decoding was repaired.
