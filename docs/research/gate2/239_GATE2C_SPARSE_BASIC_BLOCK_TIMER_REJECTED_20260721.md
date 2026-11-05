# 239 — Gate 2c sparse basic-block wall timer rejected (2026-07-21)

## Result

- **VERIFIED browser/runtime:** Both sparse-profiler variants reached the real PatHouse scene in one tab, with the reference carpet, walls, table, chair, character, Korean UI, and mipmapped textures intact. No input was used.
- **REJECTED measurement:** Timing individual `cpu->run()` basic blocks is not a valid wall-time estimator in this browser runtime, even when only 1/4096 runs are timed.

## Variant A — inclusive synchronous proxy

The first build timed the complete selected `cpu->run()`, including synchronous D3D9Web proxy waits.

- Last 10 PatHouse windows: 22.50–24.22 FPS.
- 12,515–13,560 selected runs/window.
- Timestamp-read estimate: 0.09–0.11% of the 120-Present window.
- RSE: 10.38–19.16%; all 10 windows failed the <=5% gate.
- A selected proxy-heavy run occasionally produced a millisecond-scale outlier, dominating the variance.

**VERIFIED conclusion:** Guest run and exact proxy measurements were nested and could not be added. The variance was too high for optimization decisions.

## Variant B — proxy-exclusive guest samples

The second build paused the selected run at proxy entry and resumed it at proxy exit. It accumulated all guest fragments into one statistical sample, used RAII for proxy exit, and kept proxy time as a separate exact census.

- Last 10 PatHouse windows: 22.10–24.64 FPS.
- Timestamp-read estimate: 0.12–0.14%.
- RSE: 3.04–5.04%.
- However, `sample_raw_us * 4096 / wall_us` was 5.23–5.92. The estimated guest-exclusive execution therefore exceeded the entire wall window by more than 5x.
- 11,270–11,949 samples/window underflowed the calibrated pair correction because most selected blocks were shorter than the approximately 0.225 us adjacent-pair delta.

**VERIFIED conclusion:** Removing proxy heavy tails fixed variance but exposed timer-resolution bias. A single interpreted basic block is shorter than the clock measurement unit; Horvitz expansion multiplies this fixed bias by 4096. Low RSE did not make the estimator accurate.

## Next measurement gate

**INFERRED design, browser verification required:** Treat a contiguous residency in the same module as one epoch. Cache module class by the EIP's 64 KiB page, sample only 1/16 epochs, and time the entire selected epoch. This amortizes two clock reads across hundreds of basic blocks while retaining an unbiased module-time estimator. Proxy intervals remain paused/exact and additive. The old every-transition wall profiler is not reused because it measured tens of thousands of transitions and caused 22–31% timer overhead.

Acceptance remains: intact PatHouse, exact 120 Presents, no exceptions/drops, timestamp-read estimate <=1%, estimator plausibility against wall/proxy bounds, RSE <=5%, and a later matched OFF/ON slowdown <5%.
