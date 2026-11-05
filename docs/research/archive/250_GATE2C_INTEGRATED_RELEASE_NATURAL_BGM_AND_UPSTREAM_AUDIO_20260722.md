> **SUPERSEDED by 254 for browser performance measurement.** The BGM loop and pacing evidence remains valid; the `73.509 FPS` claim confused 120 host command batches with 120 D3D9 Presents.

# Gate 2C: integrated release natural BGM loop and upstream audio pacing

Date: 2026-07-22

## Result

- **VERIFIED (dynamic + static): the BGM restart failure was not a BoxedWine message-pump or condition-variable wake failure.** The prior `audiogate6` trace observed `EC_COMPLETE -> PostMessageW success -> Acknex private message 0x1528 -> event code 1 with loop=1 -> SetPositions(0) -> Pause/Run S_OK -> GStreamer EOS/flush waiter return`. Static re-audit confirms that `EC_COMPLETE` uses Quartz `SetEvent + PostMessageW`, not `PostThreadMessageW`.
- **VERIFIED (package):** the active `bgmloop3` root contains the fixed 579,720-byte `winegstreamer.dll.so`, SHA-256 `8793B5D7CDD503E05AF429950E8AD99DCFE898006F2D1B39DD6B8B770E3F9E20`.
- **VERIFIED (original asset, release runtime):** a 100-second loopback capture of the unmodified `PetHouse.mp3` crossed its natural loop boundary. The nonzero-PCM envelope has a periodic fit correlation of 0.923438 against the original, reached the first restart at wall time 59.132 seconds for this capture's starting phase, and contained another 39.868 seconds of second-cycle PCM.
- **VERIFIED (upstream audio pacing A/B):** applying upstream BoxedWine commit `682d56002f4a0db5f7431dc890286e0060e6a386` reduced exact-zero output from 33.951% to 2.732%. Runs of at least 20 ms fell from 821 to 5, and their total duration fell from 29.705 seconds to 0.383 seconds.
- **VERIFIED (browser visual/performance):** the upstream-audio build reused one in-app browser tab, rendered the accepted PatHouse carpet/walls/character without fatal/OOM, and measured 1,320 Presents in 17.957 seconds: **73.509 FPS**.

## Wake-path verdict

The EC_COMPLETE path is:

1. DirectSound renderer `complete_eos()` calls `IMediaEventSink::Notify(EC_COMPLETE)`.
2. Quartz `queue_media_event()` sets `media_event_handle` and posts the configured private window message.
3. Wine server marks the posted-message queue and signals the waiting thread's wait object.
4. Acknex receives message `0x1528`, drains event code 1, observes `loop=1`, and seeks to zero.
5. Quartz Pause/Run and GStreamer EOS/flush waiters all return successfully.

The former stop occurred after these five steps, when Wine 11's mpg123 transform retained two old samples across seek and exhausted the three-buffer allocator. The official Wine seek-flush backport documented in 249 is therefore the root loop fix. No speculative BoxedWine wake workaround was added.

Two latent BoxedWine races remain **NOT VERIFIED as active defects**: unlocked `parentCount` reads in `source/util/synchronization.cpp`, and unlocked `system_futex[128]` slot scans in `source/kernel/kthread.cpp`. They should only be changed after a new trace proves a missed parent-condition or futex wake.

## Natural-loop evidence

Original asset:

- `Data/Sound/PetHouse.mp3`
- ffprobe duration: 85.206313 seconds
- SHA-256: `DD1234D6831992F8DFD9A46FDF898FB31FD310FBBBCAC4512CEB8AEADA4BD3E0`

Accepted upstream-audio capture:

- `artifacts/runtime/20260722_callaudio2_upstream48ms_pathouse100s.wav`
- 48 kHz, stereo, 100.000 seconds
- SHA-256: `97466B7258B8507104C9244BAF254C02E08168373B71C0D98608784943AB0859`
- Exact-zero output: 2.732333 seconds
- At least 20 ms zero runs: 5, totaling 0.383375 seconds
- Longest zero run: 292.438 ms; the natural EOS/seek boundary is included in this figure
- Periodic nonzero-PCM envelope fit: 0.923438
- Second-cycle PCM after the observed boundary: 39.868 seconds

Rejected 96 ms pacing control:

- `artifacts/runtime/20260722_callaudio1_pathouse_cleanconsoleoff100s.wav`
- SHA-256: `9C3B5C4985FC84F126DCAE5ED2BE7FB99458DC7E9E765A792EE0532669B22423`
- Exact-zero output: 33.950833 seconds
- At least 20 ms zero runs: 821, totaling 29.704667 seconds
- Longest zero run: 255.875 ms

The comparison used the same browser, app ZIP, original BGM, `bgmloop3` root, 44.1 kHz guest audio setting, and no console textarea. The runtime audio pacing change is the controlled variable.

## Upstream change applied

The current BoxedWine tree already contained the Azrok-specific 44.1 kHz cap and frequency-scaled OSS fragment count. The following parts of official commit `682d560` were restored without replacing those project-specific changes:

- `include/kdspaudio_math.h`
  - `getRequestedSdlPeriodFrames()`
  - `getAlignedDurationBytes()`
  - `getOutputSpaceAvailable()`
- `platform/sdl/kdspaudio.cpp`
  - shared requested SDL period helper
  - Emscripten silence target reduced from 96 ms to 48 ms
- `source/kernel/devs/devdsp.cpp`
  - upstream GETOSPACE helper semantics
- `source/test/devs/testDspAudio.cpp`
  - upstream queue-duration and output-space math coverage

## Integrated release artifacts

- `tools/boxedwine_local/assets_d3d9web/boxedwine.callaudio2.html`
  - SHA-256 `06C25979F970B9BAADCA35D3C0DB7D3FD2CFFCC9FBE5A82C927538A440145325`
- `tools/boxedwine_local/assets_d3d9web/boxedwine.callaudio2.js`
  - SHA-256 `0DEACF17EE9A37F57455252F7EEC7B4A59670254864B20542433966240D234E0`
- `tools/boxedwine_local/assets_d3d9web/boxedwine.callaudio2.wasm`
  - SHA-256 `C2A4170FBD08CB6BEAE0B66F687919BBB37D562FC599E39C481F5F7D307BA168`

Build properties:

- 1 GiB initial memory
- pthread pool 32, `PROXY_TO_PTHREAD=1`
- runtime Stackifier JIT and telemetry enabled
- audio gesture-ready path enabled
- diagnostic `BOXEDWINE_D3D9WEB_AUDIO_TRACE` disabled

## Remaining sound gates

- **NOT VERIFIED:** long simultaneous SFX+BGM mixing under active gameplay.
- **NOT VERIFIED:** BGM transitions across Plaza, OX, and cooking.
- **NOT VERIFIED:** mobile-browser audio pacing and background/foreground recovery.
