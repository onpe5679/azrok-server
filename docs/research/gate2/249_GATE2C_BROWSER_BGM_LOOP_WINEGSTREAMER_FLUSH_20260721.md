# Gate 2C: browser BGM loop and winegstreamer seek flush

> **FOLLOW-UP:** the original 85.206-second PatHouse asset's natural release-runtime loop is VERIFIED by 250.

Date: 2026-07-21

## Result

- **VERIFIED (dynamic): BoxedWine message wake is not the fault.** Quartz queued `EC_COMPLETE`, `PostMessageW` returned success, Acknex received its private window message `0x1528`, and the game-side media loop consumed event code `1` with `loop=1`.
- **VERIFIED (dynamic): BoxedWine condition-variable wake is not the fault.** The blocked Wine GStreamer worker returned from both EOS/flush wake points, `eos` changed back to zero, and `wg_parser_stream_get_buffer()` returned success after seek.
- **VERIFIED (dynamic): Quartz restart is not the fault.** `IMediaSeeking::SetPositions(0)` entered with graph state 2; Pause and Run both returned `S_OK`, DirectSound ran BeginFlush/EndFlush and restarted its render thread.
- **VERIFIED (static + dynamic):** after the first post-seek compressed MP3 sample, the next transform input blocked at `winegstreamer.dll.so`'s `IMemAllocator::GetBuffer`. The MP3 input allocator intentionally has three buffers because mpg123 may retain the previous two samples. Wine 11.0 did not flush those retained transform samples during seek, so the first new sample consumed the third buffer and the next allocation waited indefinitely.
- **VERIFIED (upstream):** Wine commit `63d79461bff860d6a7f18f59a73cedab7720d9c6`, `winegstreamer: Flush wg_transform buffers on seek in quartz_transform.c`, fixes this exact omission by flushing the transform, flushing the sample queue, and forwarding `BeginFlush` downstream.
- **VERIFIED (implementation/build):** the official 18-line change was backported without increasing allocator buffer count. Wine 11.0's 32-bit `winegstreamer.dll.so` rebuilt successfully with GStreamer enabled. The stripped replacement is 579,720 bytes and SHA-256 `8793B5D7CDD503E05AF429950E8AD99DCFE898006F2D1B39DD6B8B770E3F9E20`.
- **VERIFIED (browser):** in a single reused in-app browser tab, selection BGM reached `EC_COMPLETE`, sought to zero, returned Pause/Run `S_OK`, and resumed nonzero PCM (`3092`, `4083`, `2151` nonzero samples in successive reports). The previous indefinite second-buffer stall did not recur.
- **VERIFIED (browser, PatHouse workaround):** a separate test app preserved the `Data/Sound/PetHouse.mp3` path but substituted the 512,194-byte, 16.688-second `intro.mp3` payload. The PatHouse graph reached `GRAPH_COMPLETE_MATCH`, sought from running state, returned Pause/Run `S_OK`, and resumed nonzero PCM (`3873`, `4078`, `3147`). This directly verifies the PatHouse loop path without waiting for the original 85.206-second track.
- **VERIFIED (browser, real asset):** the normal app opened the original `PetHouse.mp3` and emitted nonzero PCM. The original 85.206-second track was not kept running to a natural second EOS because the shortened-path test already exercised the same graph and loop code.

## Why this is not a BoxedWine wake bug

The full observed chain before the fix was:

1. Quartz renderer completed and queued `EC_COMPLETE`.
2. `PostMessageW` succeeded and Acknex processed message `0x1528`.
3. Acknex read event code 1 and called `SetPositions(0)` because `loop=1`.
4. Quartz Pause/Run and DirectSound flush/restart succeeded.
5. Wine GStreamer waiters woke and the parser supplied post-seek compressed data.
6. The transform consumed one new sample and then blocked inside its own three-buffer allocator.

Steps 1 through 5 directly exclude the two proposed BoxedWine wake mechanisms. Step 6 is allocator starvation caused by stale transform-held samples, exactly matching the official Wine fix.

## Backport

Modified source:

`artifacts/wine11_source/wine-11.0/dlls/winegstreamer/quartz_transform.c`

The new sink `BeginFlush` callback performs:

```c
hr = wg_transform_flush(filter->transform);
wg_sample_queue_flush(filter->sample_queue, true);
if (filter->source.pin.peer)
    IPin_BeginFlush(filter->source.pin.peer);
```

The callback is installed as `sink_ops.sink_begin_flush`. No game binary, Acknex logic, media-loop flag, or packet path was modified.

## Artifacts

- Normal fixed root: `tools/boxedwine_local/fs/TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3.zip`
  - SHA-256 `D2A1D276D163343CDFBD347F7EB3DDCC8C14D909EA74FEB5D19749D1DA88CFFA`
- Stripped Wine module: `artifacts/runtime/bgmloop3_official_flush/winegstreamer.dll.so`
  - SHA-256 `8793B5D7CDD503E05AF429950E8AD99DCFE898006F2D1B39DD6B8B770E3F9E20`
- Short-loop validation app only: `tools/boxedwine_local/apps/Azrok_D3D9Web_pathouse_audio_loopshort2.zip`
  - SHA-256 `AD4D1761421C1FD89890CCDBFA5B24D82EBBA16499B3C758152A4D7D582CF72D`
  - `intro.mp3` and substituted `PetHouse.mp3` both SHA-256 `6E5C36100D522ADF5F341738554D0C8F839801A0C3A4AE2EE4DB5A3EBD2A343F`
- Trace runtime:
  - `boxedwine.audiogate6.wasm` SHA-256 `9F2107D167B98567FB73A955DC73BD0B60701D39BE342573B25246A312C112E4`
  - `boxedwine.audiogate6.js` SHA-256 `08BCA7F5FB9E3EAF9225F0D6C4E6222479E4C64A125B85400D1D251A2926C5BE`

## Remaining audio gates

- **VERIFIED by 250:** uninterrupted natural looping of the original 85.206-second PatHouse asset without the diagnostic trace overhead.
- **NOT VERIFIED:** long-duration SFX+BGM mixing and memory stability in the release JIT runtime.
- **NOT VERIFIED:** BGM behavior across Plaza/OX/cooking transitions.
