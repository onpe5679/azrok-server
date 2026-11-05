# 502 Gate 6 host upBatch visible negative result (2026-07-28)

## VERIFIED

- After the runtime cache was separated, `upBatch=1` with `upRing` removed
  reached the original 1024x768 character selection, the native loading
  screen, and the visible PatHouse scene. No synthetic frame or packet was
  used.
- In that visible PatHouse scene BGM was unpaused, unmuted, ready state 4,
  and advancing. The HUD measured `FPS 39.8`.
- Therefore the first black-output report in 501 was cache-contaminated, not
  an upBatch compatibility proof; 501 is archived and superseded.

## Conclusion

`upBatch` is compatible with this path but does not establish the required
50 FPS floor. It is not adopted as the performance fix. A debug-console-free
direct 30-second comparison remains required before making a precise
percentage claim.
