# 505 Gate 6 in-app Web Audio current-output confirmation (2026-07-28)

## VERIFIED

- The currently retained in-app browser tab was returned to the accepted
  `Azrok_D3D9Web_pathouse_guesttexrecycle4` package and launched by its visible
  audio-activation control.
- Its initial native-media fallback was healthy (`paused=false`, `muted=false`,
  `readyState=4`, advancing clock).  The visible `BGM Web Audio 재생` control
  was then activated as a second, effects-compatible route.
- After the guest selected its natural title-map music, page state reported
  `webBgmFallback=playing`, `webBgmFallbackTrack=intro.mp3`, and
  `webBgmFallbackTransport=webaudio`.
- An eight-second WASAPI loopback recording from the current default playback
  endpoint, `artifacts/audio/bgm_iab_webaudio_current_20260728.wav`, has
  767,947 nonzero samples out of 768,000 and mean absolute amplitude
  `0.142907`.
- A 10 ms rectified-envelope comparison with the unmodified locally served
  `assets_d3d9web/audio/intro.mp3` reaches correlation `0.9689998` at a
  13.52-second source offset.  This proves that the current Web Audio BGM route
  emits the requested original music to the current default Windows playback
  endpoint.

## Boundary

- This endpoint proof does not establish physical audibility at the user's
  speakers/headphones.  With both the native-media and Web Audio routes now
  reaching the same default endpoint, a remaining silent experience requires
  checking the Zen Quadro playback-monitor path, downstream device selection,
  or hardware volume outside the game/page pipeline.
