# 511 Gate 6 BGM level false regression (2026-07-28)

## VERIFIED

- The active in-app tab's original `PetHouse.mp3` was decoded and emitted to
  the default Windows playback endpoint.  The five-second capture matched the
  source envelope at `r=0.654495` near the expected 49.15-second source
  position, so this was not a missing-music decode or routing failure.
- A temporary Web Audio gain of 8 raised endpoint RMS from `0.005338` to
  `0.114708`, confirming that the page-side gain path works.  It was removed
  from the default immediately because it bypassed the user's intentionally
  reduced browser volume and was uncomfortably loud.
- The user confirmed the reduced browser volume was intentional.  The runtime
  default has therefore been restored to unity BGM gain and the original
  media-first route.  The retained `bgmGain` query is bounded to `0.1..12` and
  defaults to `1` only for explicit endpoint diagnosis.

## Boundary

- This resolves the reported current-session loudness regression; it is not
  evidence that a physical output-device problem exists on another device.
