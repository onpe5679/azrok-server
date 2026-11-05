# 494 Gate 6 in-app-browser BGM WASAPI recheck (2026-07-28)

## VERIFIED

- The retained in-app-browser game tab reported the original
  `PetHouse.mp3` on `media-element` transport with `paused=false`,
  `muted=false`, `readyState=4`, no error, and a progressing playback clock.
- While that exact tab was playing, an eight-second capture from the current
  default Windows playback endpoint produced
  `artifacts/audio/bgm_iab_media_recheck_20260728.wav`: 767,960 nonzero
  samples of 768,000, mean absolute amplitude `0.184938`.
- A 10 ms rectified-envelope alignment against the locally served original
  `PetHouse.mp3` found correlation `0.978613` at a source offset of
  `64.14 s`.  This directly proves that the current in-app-browser BGM route
  reaches the current default playback endpoint; it is not merely a media
  element state assertion.

## Boundary

- This does not prove that the user is monitoring that same endpoint, that a
  physical speaker/headphone is powered or selected, or that the active
  ambient tab is the retained test tab.  If sound is still not heard despite
  this evidence, the remaining issue is output-device/monitoring selection
  outside the game media pipeline rather than a silent BGM decode/play path.
