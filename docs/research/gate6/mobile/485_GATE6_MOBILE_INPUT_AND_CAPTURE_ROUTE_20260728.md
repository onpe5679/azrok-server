# 485 Gate 6 mobile input and capture route (2026-07-28)

## Implemented boundary

- **VERIFIED (source):** The canvas keeps its 1024x768 internal game surface
  but already scales to the available CSS width. `mobileCapture=1` now admits
  that positive 4:3 scaled display as a *separate* Direct Present sample. The
  normal desktop capture remains exact 1024x768 and is not weakened.
- **VERIFIED (source):** `touch-action: none` is applied to the game canvas.
  A primary touch pointer now produces the same bounded synthetic mouse
  down/up/move sequence used by the SDL bridge, while native mouse handling
  retains its duplicate-event protection.
- **VERIFIED (browser setup):** a fresh private game page was opened at an
  explicit 390x844 viewport and reached `FFP runtime ready`. It has not yet
  completed a game launch or a 30-second mobile Present sample.
- **VERIFIED (static regression):** `tools.test_d3d9web_page_contract` passes
  three checks for classic-script syntax, desktop/mobile measurement separation,
  and bounded primary-touch mouse conversion.

## Status

- **NOT VERIFIED:** 50 FPS at 390x844, touchscreen gameplay, and sound on a
  real phone-class device. The mobile capture source is deliberately labelled
  `direct-D3D9WebFpsSample-mobile` so it cannot be confused with the desktop
  1024x768 Gate 6 acceptance series.
