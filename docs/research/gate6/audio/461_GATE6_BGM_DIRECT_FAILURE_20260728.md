# Gate 6: browser BGM direct graph failure

Date: 2026-07-28 KST

> **SUPERSEDES the BGM PCM conclusion in 460.** This document changes only
> the BGM result. The private-binding and single-core findings in 460 remain
> separately evidenced.

## Direct trace result

- **VERIFIED (browser + guest trace):** The current route launched
  `Azrok_D3D9Web_pathouse_audio_trace1` with `run_azrok_audio_graph.bat`,
  runtime `boxedwine.audiogate6`, root
  `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1`, and
  `audioFreq=44100`.
- **VERIFIED (guest trace):** `Data/Sound/PetHouse.mp3` was opened successfully
  (`D3D9WEB_AUDIO_FILE_OPENAT ... result=98`). The asset mount and file lookup
  are therefore not the immediate failure.
- **VERIFIED (guest trace):** Wine Quartz failed to create both
  `MPEG-I Stream Splitter` and `GStreamer splitter filter` with
  `0x8007000e`.
- **VERIFIED (guest trace):** Subsequent
  `D3D9WEB_AUDIO_DSP_WRITE` reports had `nonzero=0` and zero sample heads.
  The browser has no BGM PCM to play on this route.

## Status

- **NOT VERIFIED:** a release route that audibly plays BGM in the browser.
- **NEXT DIRECT TEST:** compare the exact historical
  `...korean4-bgmloop3` root against the current `...bgmloop3-dsound80ms1`
  variant using the same graph guest and frequency. This isolates the runtime
  root before changing registrations or audio code.
