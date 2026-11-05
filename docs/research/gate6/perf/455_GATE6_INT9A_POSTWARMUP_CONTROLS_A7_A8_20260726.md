# 455 - INT9A repaired post-warmup controls A7/A8

> Status: **VERIFIED observations; candidate comparison remains NOT VERIFIED.**

Fresh A7 and fresh A8 retry both used the repaired 453 temporal contract: exact
clean detached fingerprint, first rate probe after the official 15-second
warmup, contiguous later probes and contiguous official 30-second interval.
All page, visibility, primary-window, anti-throttling, memory, working-set and
priority gates passed.

| leg | FPS | accepted rate-probe pair |
| --- | ---: | --- |
| A7 | 42.5187 | 40.7899 / 40.1217 |
| A8 retry | 39.1235 | 38.1602 / 39.2851 |

The two controls differ by about 8.0%, outside the 3% decision band. The
repaired gate successfully removes the early high-rate transition from each
official interval, but has not established cross-process control stability.
No B leg is authorized. The A8 pre-restart stale page was intentionally
discarded; only the fresh retry is a sample.
