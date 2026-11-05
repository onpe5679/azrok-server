# 489 Gate 6 BGM native-media primary restore (2026-07-28)

## Direct result

- **VERIFIED (route comparison):** after the explicit `BGM 호환 재생` action,
  the recreated original `PetHouse.mp3` element was unpaused, unmuted, at full
  volume, ready state 4, and advanced to 2.964 seconds.  An eight-second
  WASAPI loopback from the default playback device contained 767,761 nonzero
  samples of 768,000 and had a 0.951115 rectified-envelope correlation with
  the original MP3 at a 16.91-second source offset.  This establishes actual
  hardware-endpoint output for the HTML-media route.
- **VERIFIED (regression repair):** the source had treated Web Audio as the
  primary route based on an earlier embedded-media inference, despite the
  directly verified native-media output route.  `begin()` now starts the
  same-origin `HTMLMediaElement` first during the activating gesture and uses
  Web Audio only if that play request fails.
- **VERIFIED (fresh private page):** the served <lan-ip> page is
  byte-identical to the modified source.  After a clean reload and launch,
  it reported `webBgmFallback=playing`, `transport=media-element`,
  `paused=false`, `muted=false`, `volume=1`, `readyState=4`, and
  `currentTime=3.932394`.
- **VERIFIED (fallback retained):** `BGM Web Audio 재생` remains visible
  before and during a run, and explicitly selects the prior Web Audio route
  if a browser rejects media-element playback.

## Boundary

The browser containment BGM default is now the output route with current
loopback proof.  Native Wine Quartz/GStreamer MP3 remains independently
broken at the Unix-call boundary.  The final remaining user-facing check is
audibility in the user's reloaded active in-app-browser tab; its old loaded
document cannot receive the changed primary route until it reloads.
