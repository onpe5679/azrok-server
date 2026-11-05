# 484 Gate 6 Direct Present capture bridge repair (2026-07-28)

## Finding

- **VERIFIED (dynamic/page state):** The running PatHouse page received native
  `D3D9 COMMAND.PRESENT` samples through `__d3d9WebFpsSample`; the page HUD
  accumulated `7,320` then `16,080` presents. The old 30-second control
  incorrectly required the optional page-global `D3D9WebDebug.presents`, which
  is worker-private in the current runtime and therefore caused an immediate
  invalid result despite active direct Present samples.
- **VERIFIED (source repair):**
  `captureVisiblePresent30s()` now measures the existing per-page cumulative
  `__d3d9WebFpsSample` bridge and labels a valid result
  `direct-D3D9WebFpsSample`. It keeps the visible-page, 1024x768, positive
  Present delta, and 30-second wall-time contracts.
- **VERIFIED (startup timing):** Direct samples may arrive after the control
  appears. The control now waits up to 60 seconds for its first sample before
  starting the 30-second interval rather than declaring an early click a
  performance failure.

## Status

- **NOT VERIFIED:** a valid current 30-second Direct Present number, and thus
  the required sustained 50 FPS gate. The prior result was a capture-admission
  failure, not an FPS result and must not be used as one.

