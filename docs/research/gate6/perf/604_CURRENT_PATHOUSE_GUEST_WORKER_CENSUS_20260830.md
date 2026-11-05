# 604 — Current PatHouse guest-worker clock-free census

Date: 2026-08-30 KST

> **FOLLOW-UP 605:** the current exact-entry gate was completed.  All 11
> historical `+49650` transform-loop entries were zero in an accepted current
> PatHouse window, so that region is rejected for the present workload.

## Conclusion

- **VERIFIED visual/browser:** both the launch sample and the census window
  captured PatHouse before and after timing.  The room, rug, furniture, pink
  Azron, left HUD, lower status panel, and empty character-slot labels remain
  visible in all four PNGs.  None is the selection/transition screen rejected
  by 603.
- **VERIFIED build/ABI:** the isolated runtime
  `boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2guestcensus1` keeps
  the current cache relocation map at `12968408 / 262144`.  Its census ABI is
  `1`, with 60 U32 words arranged as three stripes of 20 counters.  The
  currentabi1 verifier accepted all 94 groups, 30,550 entries, 28,944 patches,
  and all 94 Wasm modules.
- **VERIFIED dynamic:** one visually accepted 30.006803-second PatHouse
  window counted 276,306,321 outer JIT entries, 276,306,322 valid C++ to Wasm
  calls, zero slot misses, zero memory-page-array refreshes, and 115,981,547
  generated-Wasm to C++ helper calls.
- **VERIFIED dynamic:** helper-call composition was `fetchNext` 83,556,769
  (72.04%), condition helpers 24,977,542 (21.54%), single-op emulation
  6,459,361 (5.57%), flag materialization 910,140 (0.78%), and x87 cache
  69,728 (0.06%).  The remaining measured helper families were negligible.
- **INFERRED:** guest control-flow/bookkeeping crossings are a serious current
  optimization surface.  The census establishes exact call counts, not CPU
  time; it does not prove that 72.04% of guest time is in `fetchNext`.
- **NOT VERIFIED:** the current hot EIP/region and a deployable FPS gain.  The
  next gate is generated-Wasm entry counting for the known `+49650` transform
  loop, including entries reached through internal direct/generic tails.

## Why a new runtime was necessary

The primary guest pthread does not reliably service CDP profiler commands
while executing its synchronous guest loop.  Page-realm profiling therefore
cannot identify guest hot regions.  The diagnostic runtime instead reuses the
64 U32 words that currentabi1 already reserves immediately before the indirect
relocation map.  Sixty words hold three contention-reducing stripes of the same
20 counters.  No new static counter storage is inserted before the map, and
generated cache modules are not modified by this broad census.

The build is opt-in through `BOXEDWINE_WASM_JIT_GUEST_CENSUS`.  Production
Touch2 remains a separate immutable stem.  Static checks passed with the macro
both enabled and disabled, and the actual linked Wasm reported:

```text
reloc map base  12968408
capacity        262144
census ABI      1
census words    60
copy/reset      exported
```

The staged and loopback HTTP bytes match:

| Asset | Bytes | SHA-256 |
|---|---:|---|
| JS | 330,198 | `0764b62a83436a56959ac8d8d05837a7270a381900bd51ad24bf451f3e2752d6` |
| Wasm | 3,058,453 | `831940105f360136c913ce6a45d03e89d6041f9b4bf87af3e3459501adeb503f` |

## Visual acceptance

The fresh launch used the current fastboot4 app, current Korean root,
currentabi1 cache, visible 1024x768 CSS canvas, 640x480 backing canvas, and an
isolated Edge profile on CDP 9346.  Direct-Present readiness was followed by
180 seconds of scene settling and 15 seconds of warmup.  The before/after PNGs
then visibly showed PatHouse for the complete 30-second interval.

That launch interval measured 805 Presents / 30.008706 s = 26.8255 FPS.  This
is not a candidate/control comparison: every hot outer entry and helper call
performs a relaxed atomic increment in this private census build.

The attached census window was also visually accepted before and after.  It
measured 772 Presents / 30.006803 s = 25.7275 FPS.  The diagnostic FPS is used
only to prove live PatHouse activity during the counter delta; it must not be
compared with the uninstrumented 29.2257-FPS control as an optimization result.

## Exact 30-second counter delta

| Counter | Count | Per second | Share of helper calls |
|---|---:|---:|---:|
| OuterJitEntry | 276,306,321 | 9,208,122.6 | n/a |
| CallBlockNoReloc | 31,274,899 | 1,042,260.3 | n/a |
| CallBlockReloc | 245,031,423 | 8,165,862.4 | n/a |
| SlotMiss | 0 | 0 | n/a |
| MemArrayRefresh | 0 | 0 | n/a |
| HelperFetchNext | 83,556,769 | 2,784,594.2 | 72.04% |
| HelperCond | 24,977,542 | 832,396.0 | 21.54% |
| HelperEmulate | 6,459,361 | 215,263.2 | 5.57% |
| HelperFlags | 910,140 | 30,331.1 | 0.78% |
| HelperX87 | 69,728 | 2,323.7 | 0.06% |
| HelperWriteMemCheck | 7,227 | 240.8 | 0.01% |
| HelperReadMem | 780 | 26.0 | less than 0.01% |
| HelperWriteMem / SSE / Movsd32r / BlockEnter | 0 | 0 | 0% |

`CallBlockNoReloc + CallBlockReloc` differs from `OuterJitEntry` by one because
the two clock-free snapshots bracketed active workers without stopping them.
This is the expected boundary skew, not a cache or slot failure.

## Interpretation boundary

This census proves frequency at existing C++ boundaries.  It deliberately does
not place atomics inside generated group functions, so internal
`return_call`/`return_call_indirect` entries are not counted by
`OuterJitEntry` or `CallBlock*`.  It therefore cannot select a fused region by
itself.

The strongest existing candidate remains the same-binary object transform
loop:

```text
+49650 -> +46760 -> indirect transform 1 -> indirect transform 2
       -> +49659 -> loop back to +49650 / exit +4966D
```

Past PatHouse probes saw `+49650/+46760` at least 16,777,216 times each and the
loop branch taken 99.949%, but those are older-runtime measurements.  Current
selection requires exact entry deltas for `+49650`, `+49659`, `+4966D`,
`+46760`, `+467AA`, both thunks, both transform targets, and the two return
continuations from a visually accepted current PatHouse window.  Only if those
ratios reproduce will one loop iteration be implemented as the first isolated
fused regional AOT candidate.

## Artifacts

- `artifacts/performance/regional_guest_census_launch_present_20260830.csv`
- `artifacts/performance/20260829T170024504Z_edge_default_cdp9346_pid80264.before.png`
- `artifacts/performance/20260829T170024504Z_edge_default_cdp9346_pid80264.after.png`
- `artifacts/performance/regional_guest_census_actual_pathouse_20260830.csv`
- `artifacts/performance/regional_guest_census_actual_pathouse_20260830.raw.json`
- `artifacts/performance/regional_guest_census_actual_pathouse_20260830.visual-review.csv`
- `artifacts/performance/guest_census_20260830_020620_before.png`
- `artifacts/performance/guest_census_20260830_020620_after.png`

## Next gate

1. Inject opt-in exact-entry counters at the merged generated-Wasm function
   entry, after grouping and direct/generic tail rewriting.
2. Store those counters in the same fixed 64-word ABI reserve under a separate
   snapshot-only runtime, so broad census atomics cannot collide with them.
3. Re-run a visually accepted current PatHouse 30-second window.
4. Implement a fused region only if the candidate entry/branch/target ratios
   pass; otherwise rank the observed current candidates instead.
