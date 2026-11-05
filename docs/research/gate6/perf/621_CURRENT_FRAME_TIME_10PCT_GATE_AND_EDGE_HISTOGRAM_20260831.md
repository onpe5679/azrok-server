# 621 — Current frame-time 10% gate, rejected micro-candidates, and exact exit histogram

Date: 2026-08-31 KST

## Conclusion

- **VERIFIED goal gate:** a candidate is no longer retained merely because it
  improves a local counter or ranks highly. It must reduce actual PatHouse
  frame time by at least 10% in a fresh-process visual A/B. A 10% frame-time
  reduction requires an FPS multiplier of at least `1 / 0.9 = 1.1111x`.
- **VERIFIED actual in-app browser scene:** the Codex in-app browser was driven
  through the original character selector and rendered the real PatHouse room,
  furniture, rug, pink Azron and HUD. Performance numbers remain isolated Edge
  processes because one persistent browser process accumulates V8 tiers/cache.
- **VERIFIED attribution split:** fresh-process A/C/B shows that the large
  current gain is primarily expanded current-scene AOT coverage, not the
  multi-direct-loop delta alone. The exact-key C corpus overlaps B by 97.4507%,
  so this is a bounded attribution rather than exact identical-corpus proof.
- **VERIFIED rejection:** a renderer base-UBO dirty split produced
  `36.6560 -> 36.0527 FPS`; frame time changed
  `27.2807 -> 27.7372 ms`, **1.6734% worse**. The opt-in code and its test were
  immediately removed.
- **VERIFIED static rejection:** safe Binaryen post-link optimization preserved
  all `33,912` direct-call markers/patch rows and removed zero actual call
  boundaries. It is not sent to browser A/B under the 10% rule.
- **VERIFIED instrumentation implementation:** a separately named
  multi-direct-loop runtime now emits exact per-site markers and
  `{block key, site id, source EIP, kind, static target}` metadata. The paired
  transformer counts only an anchor-captured game CPU and validates a
  60/61/62/63 owner/cookie/pointer/count ABI. Production runtime/cache remain
  untouched.
- **VERIFIED dynamic exit window:** an exact production-B byte-identical alias
  counted 234 selected exits for 20.006765 seconds in actual PatHouse. The
  transform island entered `3,150,256` times; its loop took the back edge
  `3,148,652` times and fell through `1,604` times, or **99.949084% taken**.
- **NOT VERIFIED revolutionary follow-up:** those direct counts now have to be
  converted into a content-bound HLE/mega-function and clear the same 10%
  actual-frame-time gate.

## Expanded-AOT versus multi-loop boundary

Fresh Edge profiles used the same `perfC1` account, actual PatHouse entry,
scene-ready gate, and independent browser process per leg.

| condition | runs (FPS) | mean |
|---|---:|---:|
| A: old Touch2 + old grouped cache | 21.8414 / 22.5946 | 22.2180 |
| C: Touch2 + current-scene record/grouping | 30.4872 / 30.7030 | 30.5951 |
| B: multi-direct runtime + current-scene cache | 31.3299 / 35.8338 | 33.5819 |

- A -> C mean: `+37.7041%`
- C -> B mean: `+9.7622%`
- A -> B mean: `+51.1470%`
- drift: A `3.4485%`, C `0.7078%`, B `14.3757%`

**VERIFIED:** the large deployable effect exists. **INFERRED:** expanded AOT is
the dominant contributor. **NOT VERIFIED:** an exact multi-loop percentage,
because the C/B key sets are not identical and B variance is high.

Artifacts:

- `artifacts/performance/fresh_process_abc_auto2_20260831.csv`
- `artifacts/performance/fresh_process_abc_auto3_20260831.csv`
- `tools/boxedwine_local/profiles/azrok-jit-record-touch2-conditionc2-player-20260831.zip`
- `tools/boxedwine_local/profiles/azrok-jit-grouped-touch2-conditionc2-player-currentabi1-20260831.zip`

The generic `azrok-jit-record-raw.zip` was restored byte-exact to SHA-256
`3533dfb2b2b6a18f029065e2dcdec3a14f6c25ccedcc68208dfd51a64f32f165`.

## V8 tier boundary and invalid B4 interpretation

The B4 trace contains:

- baseline compilations: `44,969`
- top-tier compilations: `5,592`
- top-tier/baseline: `12.4352%`

Forcing `--no-liftoff` produced an actual-PatHouse `29.0385 FPS`, so eager
top-tier compilation is **VERIFIED rejected**.

B4 itself is **not** a stable-PatHouse CPU attribution trace: its sampled span
ended before the canonical room measurement and reports trace data loss.
Consequently its `_emscripten_get_now`, dispatcher and Wasm leaf percentages
must not be used as current B frame-time shares.

Artifacts:

- `artifacts/performance/b4_multidirect_v8_tier_trace_20260831.json`
- `artifacts/performance/b4_multidirect_v8_tier_trace_20260831.summary.json`
- `artifacts/performance/b_noliftoff_scenevalid_20260831.csv`

## Current B owner window

A byte-identical B runtime alias plus a derived owner-anchored entry cache
captured an actual PatHouse 20.0057-second window:

```text
owner CPU                 0x214251f0
generated entry hits      245,541,925
generated entries/second  12,273,613
generated entries/Present 331,813.41
nonzero entries           9,644 / 44,395
top-100 hit share         59.0008%
Presents / FPS            740 / 36.9895
```

Both before/after screenshots are visually PatHouse. A later trace/census
overlap window confirmed the same owner pointer, but profile-distribution
similarity remained too weak to call any V8 CPU profile the authoritative game
thread. Therefore the 331k entries/Present is **VERIFIED**, while a precise
per-function CPU-time attribution remains **NOT VERIFIED**.

Artifacts:

- `artifacts/performance/b_owner_census_20260831.csv`
- `artifacts/performance/b_owner_census_20260831.raw.json`
- `artifacts/performance/b5_samewindow_owner_census_20260831.csv`
- `artifacts/performance/b5_multidirect_samewindow_trace_20260831.json`

## Rejected renderer UBO split

A data-loss-free historical actual-PatHouse trace showed `uploadState` at
12.444% of its main-thread wall window. The candidate therefore split
FFVertexData / FFPixelState / FFPixelStages invalidation and stopped GL-only
depth/blend/cull/color-mask changes from dirtying UBOs.

The classifier and flag-off compatibility tests passed, and both candidate
screenshots rendered PatHouse correctly. The real fresh-process result was:

| leg | FPS | frame time |
|---|---:|---:|
| control | 36.6560 | 27.2807 ms |
| candidate | 36.0527 | 27.7372 ms |

This is `-1.6458% FPS` / `+1.6734% frame time`. The implementation was removed
instead of being retained as an inactive optimization branch.

Evidence:

- `artifacts/performance/ubo_dirty_split_ab_20260831.csv`
- `artifacts/performance/ubo_dirty_split_ab_20260831/a1_control/`
- `artifacts/performance/ubo_dirty_split_ab_20260831/b1_candidate/`

## Rejected generic post-link inlining

An isolated Binaryen transform discovered and guarded a real relocation hazard:
an optimizer can fold a marker plus memory offset into a different constant.
A mutable-zero identity barrier made marker recovery fail-closed and the full
143-group output deterministic.

Actual B result:

```text
group Wasm bytes   46,308,572 -> 46,113,967 (-0.4202%)
patch rows         33,912 -> 33,912
surviving markers  33,912 -> 33,912
removed/duplicated 0 / 0
```

Because no direct-call boundary disappeared, this candidate was rejected
without a browser A/B.

## Exact exit histogram implementation

The private diagnostic runtime is:

```text
stem boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1anchoredexithist1
JS   2742d659c7cb7178d61621b2aba5b0d10843344f7c492eaaec7906c2506d6227
Wasm f3a99d3de6532fdfad4cfac9a5a0e9cf50bd3f3cdd58236e26c6d62600605438
```

It keeps the production build macro-separated and emits the exact inert marker:

```text
i32.const 0x4a495458; i32.const localSiteId; i32.xor; drop
```

The real PathHouse marker record is:

```text
path     tools/boxedwine_local/profiles/
         azrok-jit-record-multidirectloops1-anchoredexithist-marker1-20260831.zip
bytes    81,641,968
SHA-256  7592c09573d268d164e315e46c7de06bd99c587e1e8af338e755a4c1e4c2791f
manifest 1c5483b5a80005e940cf0e8a1cb4a7b367b1321555aa533e995dbce6b8ffb974
entries  50,721
sites    477,541 (next1 166,988 / next2 19,912 / jump 290,641)
```

All 50,721 entries declare `exitSiteAbiVersion=1`; every site-count sum matches
the legacy next1/next2/jump aggregate. The generic raw archive was restored
immediately after preserving this uniquely named capture.

Verifier:

```powershell
node tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-anchored-exit-histogram-cache.mjs
```

Result: `anchored exit-histogram raw-cache verifier: PASS`.

## Actual B-current exact exit window

The marker producer's live reserve ABI had moved by 704 bytes, so its first
stamped cache was rejected fail-closed. A byte-identical production-B runtime
alias was then bound explicitly to production B's reserve words. It has no
histogram control exports and is accepted only under the manifest-declared
`reserve-atomics-no-export-v1` contract.

```text
runtime alias       boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1anchoredexithistalias1
JS SHA-256          b5135db7989b38b6d3e52c3420dd5f8028ea3a941927f7c12735d866d57c7954
Wasm SHA-256        e6f9ae4183358ec6145ffdd6e118454b3af9d454a1fed20113a77ec1cbace57f
cache SHA-256       2fa42e59b8f98ba6b6a36fd23c236746f21e02b5963429291570f3af28f79fd6
site-table SHA-256  57891b011174bcc282dbc00370ce8e15bcd11d78904487a2c19730d0c1e85daa
owner CPU           0x23265320
window              20.006765 s / 803 Presents
selected exits      234 (171 surviving / 63 Binaryen-DCE deterministic zero)
observed taken      78,823,883
transform entry     3,150,256
loop taken / exit   3,148,652 / 1,604
loop taken ratio    99.949084%
```

**VERIFIED semantic witness:** both before/after screenshots show the actual
PatHouse room, rug, furniture, pink Azron and HUD. **VERIFIED cleanup:** owner,
cookie, pointer and count reserve words plus staged state all returned to zero.
The `40.1364 FPS` inside this instrumented window is diagnostic only and is not
used as a production performance comparison.

Artifacts:

- `artifacts/performance/b_current_exit_histogram_20260831.csv`
- `artifacts/performance/b_current_exit_histogram_20260831.raw.json`
- `artifacts/performance/b_current_exit_histogram_20260831.top.csv`
- `artifacts/performance/b_current_exit_histogram_20260831/anchored_exit_histogram_20260831_075830_before.png`
- `artifacts/performance/b_current_exit_histogram_20260831/anchored_exit_histogram_20260831_075830_after.png`

## Next gate

1. map the current B owner top entries to exact module/file bytes;
2. rebase or regenerate a current multi-block selection against the 50,721-key
   marker corpus without claiming old coverage;
3. use the now-complete same-PatHouse taken-edge window to admit only exact
   current paths;
4. construct a real HLE/mega-function body that keeps required architectural
   state and preserves SSE reciprocal/f32 behavior;
   live across admitted internal edges;
5. reject it unless fresh-process actual-PatHouse frame time improves by at
   least 10%; only a passing candidate may be deployed.
