# 518 Gate 6 live state-churn negative result (2026-07-28)

## VERIFIED

- A fresh private diagnostic browser page with `stateChurnProbe=1` reached
  13,440 page-visible native `COMMAND.PRESENT` samples.  Its current
  120-Present probe snapshot was:

  | command family | commands | immediately same-valued commands |
  | --- | ---: | ---: |
  | render state | 11,280 | 0 |
  | texture stage state | 14,880 | 0 |
  | sampler state | 2,400 | 0 |
  | texture binding | 14,880 | 0 |
  | stream binding | 1,320 | 0 |

- The page was explicitly launched with `nosound=1`; therefore this run makes
  no BGM-output claim and cannot be used as a user-pointer or audio test.

## CONCLUSION

- The proposed exact-consecutive host-side state-skip optimization has zero
  observed work in this real 120-Present sample.  It is rejected; do not add a
  skip cache on this evidence.

## NOT VERIFIED

- This is a diagnostic workload sample, not a 30-second visible 50-FPS
  acceptance measurement.  A different rendering boundary must be measured
  before claiming a desktop improvement.
