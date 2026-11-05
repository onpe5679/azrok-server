# Gate 6 — Wine GStreamer Unix-call access violation (2026-07-28)

## Current finding

- **VERIFIED (dynamic):** `PetHouse.mp3` opens successfully, but Quartz fails every tested splitter class before BGM PCM reaches the browser audio sink.
- **VERIFIED (dynamic):** the temporary `winegstreamer.dll.so` diagnostic reports `unix_wg_parser_create` status `0xc0000005` (access violation). Wine's public parser factory converts that nonzero status into a null parser, and Quartz subsequently reports `0x8007000e`. Therefore the latter must not be interpreted as a real allocator exhaustion result.
- **VERIFIED (static):** the 32-bit Wine dispatcher invokes Unix callbacks through `call *(handle + code * 4)` after obtaining its thread syscall frame from `fs:0x218`. The parser callback is entry index 1. Temporary callbacks inserted at the beginning of `wg_parser_create()` did not yield an inner-parser trace during the failing browser route, so the fault boundary is at or before dispatch/table entry, not presently proven to be in MP3 parsing, GStreamer allocation, or the game asset.
- **VERIFIED (comparison):** a fresh root cache key and a rebuilt matching `winegstreamer.dll.so`/`winegstreamer.so` pair still reproduce zero BGM PCM. Cache staleness and the previously retained Unix module alone are ruled out.

## User-facing containment

- **VERIFIED (package):** `tools/extract_web_bgm_fallback.py` extracts the unmodified `./Data/Sound/PetHouse.mp3` from the current game package. The output SHA-256 is `DD1234D6831992F8DFD9A46FDF898FB31FD310FBBBCAC4512CEB8AEADA4BD3E0` and the private web server returns it as `audio/mpeg`.
- **VERIFIED (private-browser runtime):** the original PetHouse MP3 fallback initially remained `armed`: its 60-Present wait deferred `HTMLAudioElement.play()` beyond the click's user-activation window. The fallback now calls `play()` directly from the first launch gesture. On the private HTTPS page the resulting DOM state became `webBgmFallback=playing`; the transient earlier `NotAllowedError` is cleared after a successful retry. This is a containment route for the current silent native graph; `webBgmFallback=0` disables it and `nosound` suppresses it. It does not replace the native Wine diagnosis or establish music transitions outside PetHouse, and still requires an audible user confirmation.

## Next direct proof

1. Capture the dispatcher/table-pointer diagnostic before the first parser call without allowing runtime log churn to evict it.
2. If the table entry is invalid, compare the root `ntdll.dll.so` Unix dispatcher ABI and BoxedWine thread-frame layout; if valid, trap the callback instruction and record the exact fault address.
3. Keep native BGM disabled as a success claim until nonzero browser PCM and an audible user check are both collected.
