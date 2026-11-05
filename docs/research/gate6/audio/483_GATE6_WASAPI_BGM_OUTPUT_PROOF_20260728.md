# 483 Gate 6 WASAPI BGM output proof (2026-07-28)

## Direct result

- **VERIFIED (Windows WASAPI loopback):** With the current private browser
  tab running, an eight-second capture from the default playback endpoint
  `Zen Quadro Synergy Core USB Audio Driver Playback 1/2` contained nonzero
  output in 767,959 of 768,000 samples. The mixed-mono RMS was `0.227328`.
- **VERIFIED (asset correlation):** Its rectified-envelope correlation against
  the original served `PetHouse.mp3` was `0.921266`, at a reference offset of
  27.435 seconds. The original asset is therefore present in the hardware
  output stream, not merely accepted by a browser play request.
- **VERIFIED (capture artifact):**
  `artifacts/audio/bgm_current_output_probe_20260728.wav` is the preserved
  48 kHz stereo loopback evidence. It was captured by
  `tools/capture_loopback.py` without modifying the game or server.

## Boundary

This proves the BGM reaches the Windows default playback endpoint for the
current tab. It does not identify a downstream hardware-monitoring or physical
speaker/headphone routing issue, nor does it repair native Wine GStreamer MP3
decoding (which remains broken at the Unix-call boundary documented in 463).

