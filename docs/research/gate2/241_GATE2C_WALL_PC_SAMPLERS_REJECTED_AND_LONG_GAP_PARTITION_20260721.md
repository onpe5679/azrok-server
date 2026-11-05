# 241 — Gate 2c wall-PC samplers rejected; long-gap partition

Date: 2026-07-21

## Result

- **VERIFIED (browser/render):** one-tab automatic PatHouse runs reached the real 1024×768 scene. Carpet mipmaps, walls, table/chair, character, Korean UI, and culling matched the accepted reference. No gameplay input was used.
- **REJECTED (dedicated worker wall-PC):** five 120-Present windows produced only 132–180 samples/s. The p95 wake gap was in the 10–20 ms bucket and 26.92–40.76% of samples exceeded 10 ms. Sampled proxy residency exceeded the exact proxy timer by 11.11–21.77 percentage points. Module/page shares and the apparent 84.22 FPS are invalid.
- **REJECTED (outer `cpu->run` safe point):** randomized polling outside `cpu->run()` still left 41–58 ms gaps, so one endpoint represented many missed time targets.
- **REJECTED (whole-wall opcode safe point):** moving the low-frequency poll to `START_OP` reduced ordinary gaps but still produced repeated 8–16 ms gaps on the selection screen and 40–48 ms gaps in PatHouse. Windows had missed thresholds and invalid renewal rates.

## Direct evidence

### Dedicated worker

Five captured windows:

- total ticks: 213 / 184 / 312 / 217 / 189
- sample rate: 156.56 / 132.35 / 180.03 / 159.00 / 140.82 Hz
- `>10 ms` gaps: 32.39 / 40.76 / 26.92 / 31.79 / 38.09%
- sampled proxy: 37.55 / 44.02 / 33.01 / 35.02 / 34.92%
- exact proxy: 21.77 / 22.25 / 21.90 / 22.51 / 21.32%

The worker timer was starved and systematically oversampled proxy residency. **No CPU percentage is derived from these rows.**

### Opcode safe point and gap brackets

The profiler used a randomized 2,048–4,095-opcode countdown and a randomized 1,000–2,023 us active-time target. Long intervals were stored only as `previous poll EIP -> current poll EIP` brackets.

- Selection repeatedly included relocated `acknex.dll` brackets such as `7F544205 -> 7F3775BB`, normally about 8–16 ms.
- PatHouse produced more than 200 distinct brackets/window (fixed table overflow) with top gaps about 40–48 ms across varying Acknex and Wine builtin endpoints.
- The diversity means neither endpoint is proven to be the blocking function. The evidence is consistent with browser-worker descheduling and/or long internal helpers, but does not distinguish them.

The current Acknex preferred image base is `0x10000000`; the browser run relocated it near `0x7F370000`. Thus the `0x7F37..0x7F54` pages are Acknex pages, not a BoxedWine host function.

## Corrected short-interval partition

The next diagnostic partitions every proxy-excluded poll interval exactly once:

1. `eligible_short` for intervals `<=250 us`;
2. `unattributed_long_gap` for intervals `>250 us`;
3. exact D3D proxy time;
4. profiler/report overhead and residual.

Only `eligible_short` advances the randomized sampling clock. Long gaps are never backfilled or attributed to the following EIP. The resulting module histogram is named **conditional module residency over eligible short-poll intervals**, not total guest CPU share.

### Five-window PatHouse result

The same one-tab, no-input PatHouse session produced five 120-Present windows (600 Presents, 6.995717 s aggregate wall time). Time-weighted descriptive accounting was:

- eligible Acknex intervals: **34.897% wall**
- eligible guest `d3d9.dll` intervals: **1.561% wall**
- eligible other/Wine intervals: **20.792% wall**
- exact host proxy time: **22.213% wall**
- unattributed `>250 us` gaps: **16.466% wall**
- aggregate eligible coverage of observed non-proxy time: **77.662%**
- 200–300 us cutoff band: **5.276% of non-proxy time**
- profiler estimate: **4.608% wall**, overlapping the categories above and therefore not additive or subtractable

Accounting residual was zero and every window was `accounting_valid=1`. This is **VERIFIED descriptive partial accounting** only. Every window was `ranking_valid=0`: eligible coverage missed the 80% gate, the cutoff band exceeded the 1% gate, and two windows exceeded the 5% profiler-overhead gate.

If all unattributed time is adversarially assigned to one module at a time, the non-statistical allocation ranges are Acknex 34.897–51.363%, guest d3d9 1.561–18.027%, and other/Wine 20.792–37.258% of wall time. These upper bounds cannot hold simultaneously. Acknex versus other/Wine therefore remains unordered; only guest d3d9 remains below both under this allocation model. The 85.77 aggregate instrumented FPS is not a release-performance result.

## Acceptance still required for module ranking

- accounting residual <=1%; exact 120 Presents; no exception/cache/drop
- eligible fraction >=80% before using the histogram for optimization ranking
- 200/250/300 us cutoff sensitivity and cutoff-band duration <=1%
- 512–1,023 versus 2,048–4,095 opcode-stride invariance
- block/window-level confidence intervals, not iid binomial confidence alone
- matched profiler OFF/ON slowdown 95% CI upper bound <5%

Status: **VERIFIED accounting / REJECTED ranking.** The histogram is retained only as conditional module residency over eligible short-poll intervals. It must not be reported as total guest CPU share or used to select AOT/JIT targets.
