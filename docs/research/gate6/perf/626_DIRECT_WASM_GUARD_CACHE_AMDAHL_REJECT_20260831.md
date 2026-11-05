# 626 — Direct-Wasm early-preflight / mapping-epoch guard cache lacks a 10% Amdahl bound

Date: 2026-08-31 KST

## Conclusion

- **VERIFIED baseline/candidate:** actual PatHouse production A2 was
  `52.4548 FPS / 19.064032 ms`; active fusion5 B2 was
  `50.7276 FPS / 19.713134 ms`, or about `+3.405%` frame time. Fusion5 is
  rejected.
- **VERIFIED activation structure:** the same live candidate snapshot had
  `2,212,374` entries, `41,892,525` fast elements, `1,244,571` initial
  fallbacks and `967,803` partial/budget stops at `16,817` Presents. This is
  `131.5558` validations and `2,491.0819` fast elements per Present.
- **VERIFIED static guard burden:** each entry validates six exact code spans,
  totaling 604 bytes and 157 U32/byte comparisons plus six page translations.
  At the observed entry rate this is about 79.46 KB and 20,654 comparisons per
  Present (`4.03 MB/s`, `1.048 M comparisons/s` at candidate FPS).
- **REJECTED early-preflight successor:** cheap first-element span/type checks
  can skip the code guard only for the `56.2550%` initial-fallback cohort. To
  reach 10% below A2, this partial skip requires the full code guard to consume
  at least `23.0441%` of candidate wall time. No measurement supports that.
- **REJECTED perfect epoch-cache successor:** even deleting essentially every
  repeated code guard requires it to own at least `12.9635%` of candidate wall
  time. At the measured entry rate that is `19.4253 us/validation` or
  `123.73 ns/comparison`, before charging other instructions. The hot,
  predictable shared-memory guard has no credible structural basis for this
  cost.
- **DECISION:** implement neither an early-preflight-only fusion6 nor a new
  mapping/code-epoch ABI. Production remains unchanged and no successor source
  was added.

## Required swing

```text
A2 frame                         1000/52.4548 = 19.064032 ms
B2 frame                         1000/50.7276 = 19.713134 ms
10%-better target               19.064032*0.9 = 17.157629 ms
required removal from B2         2.555505 ms/frame
required share of B2 wall       12.9635%
```

The fusion5 counter snapshot is cumulative and later than the 30-second A/B
window. It is not used as a synchronized time measurement; only internally
matched entries/elements/Presents are used for structural rates.

## Why reordering is too small

Initial fallbacks were:

| reason | count |
|---|---:|
| source translation | 417,314 |
| destination translation | 219,638 |
| matrix type value | 1,739 |
| matrix translation | 605,880 |
| total | 1,244,571 / 2,212,374 = 56.2550% |

Moving these checks before the code guard skips about 74.0067 validations,
44.70 KB and 11,619 comparisons per Present. To save the required
`2.555505 ms`, every skipped validation must cost at least `34.5307 us`, or
`219.94 ns` per comparison. Equivalently the full code guard must be 23.0441%
of B2 wall time. That is not credible for hot linear-memory equality checks
with overwhelmingly untaken failure branches.

## Why epoch caching is not admitted

A perfect cache is the generous upper bound: skip approximately all
`131.5558` validations/Present. It still requires `19.4253 us` per validation
or `123.73 ns` per comparison to clear the 10% gate. There is no guard timer
supporting that attribution; entry counts are not CPU time.

It is also not a safe local Wasm-global toggle. Correct invalidation spans
`mprotect`, unmap/remap, decoded-code invalidation, process reuse and multiple
worker instances. The mapping/code generation is host `KProcess` state, not a
pinned field of the production grouped-Wasm ABI. A safe cache needs a new
per-process shared epoch plus runtime/page/manifest publication contracts.
Creating that architecture for an unmeasured and structurally small guard
would violate the 10% admission rule.

## Evidence

- `artifacts/performance/direct_wasm_fusion_ab_20260831.csv`
- `artifacts/performance/direct_wasm_fusion5_b2_counters_20260831.json`
- `docs/research/gate6/perf/625_ACKNEX_DIRECT_WASM_FUSION_REJECT_20260831.md`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/acknex-direct-fusion-spec.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/boxedwine-wasm-jit-cache-acknex-direct-fusion.mjs`

## Status

- **VERIFIED:** arithmetic above and the input measurements/static byte counts.
- **NOT VERIFIED:** isolated wall time of code validation.
- Since the missing time measurement is exactly what would have to prove a
  >=10% surface, the successor is rejected rather than implemented.
