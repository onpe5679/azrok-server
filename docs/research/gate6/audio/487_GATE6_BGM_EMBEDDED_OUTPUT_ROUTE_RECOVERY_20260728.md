# 487 Gate 6 embedded BGM output-route recovery (2026-07-28)

## Direct result

- **VERIFIED (served asset):** the active private HTTPS origin returns the
  current `index_d3d9web_pathouse.html`, including the BGM Web Audio fallback,
  and returns `PetHouse.mp3` as `audio/mpeg` with a nonzero `1,363,708` byte
  length.
- **VERIFIED (static):** the page's classic inline JavaScript parses after the
  update (`classic scripts parsed: 1`).
- **VERIFIED (new recovery route):** both pre-launch and running controls now
  expose `BGM 호환 재생`.  Its activating click stops the Web Audio source,
  recreates the original same-origin MP3 media element, resets it to zero, and
  calls `HTMLMediaElement.play()` without waiting for fetch/decode.  It records
  `webBgmFallbackTransport=media-element`; errors are retained in the existing
  status dataset.

## Why this change

The prior loopback evidence in 483 proves that one sampled browser BGM route
reached the Windows default endpoint.  The user still reports no audible BGM
in the active embedded-browser session, so that evidence cannot establish the
active session's downstream route.  The new control provides an independent,
gesture-bound native-media route rather than inferring that the Web Audio
destination is audible in every embedded surface.

## Boundary

- **NOT VERIFIED:** physical audibility in the user's currently open tab.  The
  user must reload that tab once and choose `BGM 호환 재생`; a successful state
  is not substituted for speaker/headphone confirmation.
- Wine GStreamer MP3 remains separately broken at the Unix-call boundary; this
  is a same-origin original-asset containment route only.
