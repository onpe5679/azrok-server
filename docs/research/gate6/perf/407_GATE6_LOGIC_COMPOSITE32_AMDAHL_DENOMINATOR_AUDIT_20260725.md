# 407 -- Gate 6 logical-composite32 Amdahl denominator audit (2026-07-25)

## Status

**VERIFIED denominator audit; numerical time Amdahl bound NOT VERIFIED.**

This is a measurement-accounting decision only.  It starts no browser, build,
cache, replay, or FPS sample.

## Direct denominator reconciliation

`401`'s `786,355 / 22.337 s = 35,204.15/s, 11.29%` is an exact share of the
EOC1 `fn_8` opcode-fallback delta, whose denominator is `6,965,027` entries
(`317`).  It is not a share of all generated-Wasm helper entries, guest-worker
CPU time, wall time, or frame time.

`402`'s `513,360 / 15 s` and `405`'s `1,470,907 / 60 s` instead count actual
condition-helper entries in distinct private cache-OFF diagnostic processes.
`405` identifies `61,281` safe b32 logical entries inside its own six-condition
helper total.  Neither diagnostic records `fn_8`, nor shares a snapshot epoch,
asset, or wall-time attribution with EOC1.  The three values therefore cannot
be divided as one common sampled population.

The only reproducible cross-diagnostic *entry-rate proxy* is:

| Numerator | Rate | Reference rate | Ratio |
| --- | ---: | ---: | ---: |
| 405 b32 logical potential, `61,281 / 60 s` | 1,021.35/s | 317 EOC1 `fn_8`, `6,965,027 / 22.337 s = 311,817.45/s` | 0.32755% |

That ratio is **not an Amdahl time fraction**.  A condition helper and an
`emulateSingleOp`/`fn_8` entry have different bodies and potentially very
different C++/Wasm/guest-work costs.  It also omits all non-helper worker time.

## Why existing timing cannot close the gap

The code has helper timing instrumentation, but `313` directly records that
under `BOXEDWINE_MULTI_THREADED` its helper-call statistics are disabled and
sampled timing is not valid for this selection decision.  The retained 313
family counters are also entry counts, not CPU-time samples.  There is thus no
existing compatible numerator/denominator from which to calculate either the
candidate's worker-time fraction or a numerical FPS ceiling.

Consequently, the following claim is **NOT VERIFIED** and must not be made:

> The b32 logical-composite optimization has a less-than-one-percent FPS
> ceiling.

## Decision

The proposed pre-fixture rejection is not authorized: the available 0.32755%
is a useful prioritization signal but not a time upper bound.  Conversely, it
does not authorize an implementation or performance claim.  The smallest
remaining evidence step is still the private fixture required by `406`:
indirect-boundary b32 correctness plus explicit candidate/fallback witnesses.
Only after that fixture can a private candidate reach cache-OFF integrity and
the normal record/replay/fresh-process A-B-A(B) performance gate, where the
real end-to-end result, not a synthetic Amdahl estimate, decides adoption.
