# 495 Gate 6 current in-app desktop 50 FPS regression (2026-07-28)

## VERIFIED

- The retained, visibly rendered in-app-browser PatHouse session used the
  private current route (`guesttexrecycle4`, `run_azrok_seh.bat`,
  `bgmloop3-dsound80ms1`, grouped replay cache, `lean=1`).  It displayed the
  real 1024x768 game canvas and had active BGM endpoint output at the time of
  this sample.
- Its per-page direct Present counters increased from 66,000 to 67,320 while
  their accumulated native elapsed time increased from 1,546,072.775 ms to
  1,578,782.620 ms.  The resulting 30-second direct-Present rate was
  **40.3548 FPS**.
- The live HUD concurrently reported 38.6 then 41.0 FPS and remained in
  `slow` state.  This is a genuine current in-app-browser Gate 6 failure;
  the prior fast control result cannot be used to claim user-path 50 FPS.

## Boundary

- This result does not invalidate #493's Chrome narrow-viewport result.  It
  establishes that the retained desktop in-app path has a separate execution
  bottleneck and must be optimized/re-profiled before desktop 50 FPS can be
  accepted.
