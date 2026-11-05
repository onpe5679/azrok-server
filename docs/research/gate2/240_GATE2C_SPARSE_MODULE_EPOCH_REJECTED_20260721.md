# 240 — Gate 2c sparse module-epoch timer rejected (2026-07-21)

## Result

- **VERIFIED browser, character-selection workload:** The contiguous-module epoch profiler compiled, passed the 16 native regression tests, and emitted internally consistent 120-Present reports.
- **REJECTED before PatHouse:** The observed transition density invalidated the measurement-cost and timer-resolution assumptions, so the session was stopped before treating any result as a game-scene profile.

## Direct measurements

Two consecutive 120-Present character-selection windows reported:

- `epochs=2,160,097` in each window, not the 37k–150k planning range.
- `selected_epochs=135,146` and `134,715` at Bernoulli 1/16.
- `timer_reads=262,142` and `261,086`.
- Timestamp-read perturbation alone was 3.53% and 3.58% of wall, above the 1% gate.
- Pair-correction underflow occurred for 121,970 and 122,297 selected epochs.
- Global RSE was 5.28% and 7.64%, also above the 5% gate.

The 64 KiB page cache and module-only boundary rule were active. The game alternates between classified module pages often enough that a same-module residency is still commonly shorter than the browser timer pair.

## Conclusion

**VERIFIED:** Timing module transitions, even sparsely at 1/16, remains too invasive and too close to the clock resolution. This is not a PatHouse performance result and cannot be used to rank modules.

**INFERRED next design, browser verification required:** Remove the per-`cpu->run()` profiler hook. Register the render CPU EIP address once, sample that shared 32-bit value from the browser's time axis at approximately 1 ms, and aggregate sampled 64 KiB pages. Read a shared proxy-depth flag so synchronous proxy periods remain separate from the existing exact proxy census. This changes the sampling basis from executed blocks/transitions to elapsed time and avoids multiplying timer bias by tens of millions of runs.
