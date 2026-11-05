# 618 — Current PatHouse expanded-AOT + multi-direct-loop gain

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED actual PatHouse A-B-A-B:** the accepted control measured
  `20.8840 / 21.7682 FPS`, while the candidate measured
  `30.3458 / 29.4154 FPS`. The three adjacent candidate effects are
  `+45.3065% / +39.4043% / +35.1301%`; robust median is **+39.4043%** and
  condition-mean effect is **+40.1128%**.
- **VERIFIED semantic witness:** all eight canonical before/after screenshots
  show the real PatHouse room, rug, furniture, pink Azron and HUD. No character
  selector, starter splash or transition frame is counted as a performance
  leg.
- **VERIFIED deployable pair:** the candidate uses the opt-in generic
  BoxedWine multi-laminar structured-loop runtime and a fresh 44,395-block
  current-PatHouse AOT cache. It registered `143 groups / 44,395 entries /
  33,912 patches` and preserved the existing currentabi1 runtime offsets.
- **VERIFIED local default promotion:** the loopback launcher and bare game
  page now select that exact runtime/cache pair. The page hashes the archive
  and grouped manifest and checks the exact corpus/stitch counts before guest
  execution. The former Touch2/currentabi1 assets remain immutable rollback
  URLs.
- **VERIFIED final default smoke:** a fresh URL with no explicit
  `runtimeStem` or `jitCacheUrl` registered
  `data-jit-replay-multi-direct-loops="1:143:44395:33912"`, loaded the exact
  candidate runtime script, naturally selected saved `Azrok1`, and rendered
  actual PatHouse.
- **IMPORTANT attribution boundary:** the measured B condition combines two
  changes: the larger current-scene AOT corpus and multi-direct-loop codegen.
  The A-B-A-B proves the deployable pair, not the isolated percentage of either
  component. The control continued compiling missing file-backed blocks in
  PatHouse; avoiding that work is part of the observed user-facing gain.

## The real >=20% critical path

The browser-wide V8 trace was repaired so profile selection no longer chooses
an audio/I/O Worker blocked in libc `__read`. It maps the opaque grouped-Wasm
URLs, compares every profile's mapped-entry sample distribution to the exact
#607 owner census, excludes mailbox/read-dominated profiles, and selects the
only eligible game-owner profile, `0x5` / sampled TID `45384`.

Direct runtime-Wasm/source witnesses identify its two largest exclusive leaf
functions:

| Runtime Wasm index | Exact semantic identity | Leaf time | Owner active share |
|---:|---|---:|---:|
| 6414 | `wasmStartJITOp(CPU*, DecodedOp*)` | 2,300,557 us | 15.1692% |
| 6481 | `NormalCPU::run()` | 2,021,280 us | 13.3277% |
| combined | dispatcher/JIT entry boundary | 4,321,837 us | **28.4968%** |

The identification is not a guessed symbol-map join. Runtime Wasm SHA-256
`d717235b...efea96` is pinned; function 6414 contains the exact
`DecodedOp::flags2 +28`, atomic `pfnJitCode +12`, owner-hazard and generated
block-call body, while 6481 contains `CPU::thread +728`, `nextOp +740`, CS
address `+48`, EIP `+112`, big-mode `+1632` and the next-op function-pointer
call. These match the current C++ source boundaries directly.

Because the rows are exclusive leaf samples, their combined conditional
Amdahl ideal is `1 / (1 - 0.2849684) = 1.39854x`, or **+39.8540%**. This is a
bound, not the attribution of the measured candidate. It nevertheless proves
that the requested revolutionary surface exists at the dispatcher/regional
boundary. The measured condition mean `+40.1128%` is close, but must not be
presented as causal equality because expanded AOT also removes live compile
work.

The same CPU-time trace demotes the earlier misleading proxies:

- `hash_short_file_name` block `10635F1F` is only `9,084 us = 0.0599%` of
  selected active time in the mapped sample;
- Azrok hot-function HLE therefore remains supplemental, not the primary
  revolutionary lever;
- owner entry counts and `entryHits * static opCount` are useful coverage
  proxies but are not CPU time.

Artifacts:

- `artifacts/performance/regional_browser_allthread_v8_trace_actual_pathouse_20260830.summary.json`
- `artifacts/performance/runtime_dispatch_hot_functions_actual_pathouse_20260830.json`
- `tools/browser_diagnostics/analyze_azrok_browser_trace.py`
- `tools/browser_diagnostics/verify-runtime-dispatch-hot-functions.mjs`

## Fresh multi-loop raw cache

The production sibling is:

```text
boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1
JS   b5135db7989b38b6d3e52c3420dd5f8028ea3a941927f7c12735d866d57c7954
Wasm e6f9ae4183358ec6145ffdd6e118454b3af9d454a1fed20113a77ec1cbace57f
```

It differs from Touch2 by the opt-in
`BOXEDWINE_WASM_JIT_MULTI_DIRECT_LOOPS` generator gate. The existing fixture
continues to cover disjoint/shared-budget, nested/flags, crossing fail-closed,
SMC fresh-decode and fault equivalence. One shared 64-backedge budget applies
to the complete generated activation.

The first record export exposed a separate scalability bug: the shell started
one `CompressionStream` for each of more than 44,000 modules and permanently
stalled Edge. `saveJitModules()` now uses a bounded 16-stream worker pool and
the shell URL cache-buster was advanced. The same corpus then exported in
about ten seconds.

Raw artifact:

```text
path     tools/boxedwine_local/profiles/
         azrok-jit-record-multidirectloops1-20260830-211541.zip
bytes    67,635,624
SHA-256  b4f4ab4708f8bb3b11514b0dfae5986735055f8e34a3c10a8237796189c2f5d0
manifest 1220b3dc236e13dcef874feb4d2b968c70be48c08b2c7e4b168ba7c7aaca72e3
entries  44,395
```

The four exact Wine hash-family witness modules all validate and now contain
8–10 structured Wasm loops with an explicit 64 budget; the old corpus had the
single-loop form.

## Grouped candidate

The raw cache was transformed with the same currentabi1 publication,
next1/next2, depth-local, generic-indirect and inline-fetch contracts as the
control:

```text
path     tools/boxedwine_local/profiles/
         azrok-jit-grouped-multidirectloops1-currentabi1-20260830.zip
bytes    7,146,876
SHA-256  03a322841ae2ff221aba793ab832318349deeb8a3d3a1db2bf5c3ce189a7dbb5
manifest 08e4a2a6a226b85d9dd17ff51916952f11f3736068acaa61679298690c997baf
groups   143
entries  44,395
patches  33,912
```

All 44,395 modules optimized; every merged group passed Binaryen and browser
`WebAssembly.validate` inside the pipeline. The final manifest reports:

- 11,304 local next1/next2 tail rewrites;
- 319,267 generic-indirect tail rewrites;
- currentabi1 relocation map `12968408 / 262144`;
- inline fetch ABI `2:728:72:36:112:48:1632:652`;
- 0 permanent runtime compile failures in the observed candidate runs.

## Actual PatHouse A-B-A-B

The first control measurement immediately after entering PatHouse was
`20.3052 FPS`; it was excluded from the canonical A1 slot to avoid favoring
the candidate with the control's earliest cold interval. After an additional
45-second window and one minute of settling, that same control became canonical
A1 at `20.8840 FPS`. It still had ongoing missing-block compilation, which is
exactly what the expanded candidate cache removes.

| Order | Condition | Presents / wall | FPS | Visual |
|---:|---|---:|---:|---|
| 1 | A1 current Touch2/currentabi1, settled | 940 / 45.010458 s | 20.8840 | PatHouse before/after |
| 2 | B1 expanded-AOT + multi-loop | 1,366 / 45.014449 s | 30.3458 | PatHouse before/after |
| 3 | A2 current Touch2/currentabi1 | 980 / 45.019814 s | 21.7682 | PatHouse before/after |
| 4 | B2 expanded-AOT + multi-loop | 1,324 / 45.010371 s | 29.4154 | PatHouse before/after |

Control drift was `+4.2339%`, so the run was extended to B2 under the existing
3% rule. Candidate drift was `-3.0660%`. The three adjacent effects were:

```text
B1 / A1 - 1 = +45.3065%
B1 / A2 - 1 = +39.4043%
B2 / A2 - 1 = +35.1301%
median         +39.4043%
```

Condition means are `A=21.3261`, `B=29.8806 FPS`, or `+40.1128%`.

Machine-readable evidence:

- `artifacts/performance/multidirectloops_pathouse_abab_20260830.json`
- `artifacts/performance/multidirectloops_pathouse_abab_20260830.csv`
- `artifacts/performance/multiloop_aba_{a1warm,b1,a2,b2}_measure_{before,after}.png`

## Local default and rollback

`tools/boxedwine_local/azrok_launch.js` now prewarms and launches the candidate
pair. `index_d3d9web_pathouse.html` uses the same pair for a bare URL and for
post-logout character-select reentry.

Before registering the candidate, the page requires all of:

- exact runtime stem and cache URL as one pair;
- archive SHA-256 `03a322...7dbb5`;
- manifest SHA-256 `08e4a2...97baf`;
- manifest version 2;
- exactly 143 groups / 44,395 entries;
- exactly 11,304 local direct rewrites and 319,267 generic-indirect rewrites;
- the existing runtime publication/generic/inline-fetch ABI checks.

The former runtime and cache were not overwritten:

```text
boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2
/profiles/azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-currentabi1.zip
```

They remain an explicit rollback and the control identity for future tests.
This local promotion has not been claimed as a `playazrok.com` remote deploy.

## Verification

Passed after promotion:

```text
node project/emscripten/verify-multi-direct-loops-source.mjs
node tools/browser_diagnostics/verify-runtime-dispatch-hot-functions.mjs
node tools/boxedwine_local/verify-multidirectloops-loader-gate.mjs
python -m unittest tools.test_d3d9web_page_contract \
  tools.test_azrok_home_contract tools.test_boot_splash_visibility
# 47 tests OK

# all tools/boxedwine_local/verify-*-loader-gate.mjs plus the multi-loop gate
# 11/11 PASS
```

The final browser smoke used no explicit runtime/cache query fields. It loaded
the candidate JS, registered `143/44395/33912`, naturally selected saved
`Azrok1`, maintained server heartbeat and rendered actual PatHouse. Screenshot:
`artifacts/performance/multiloop_default_smoke_20260830_pathouse.png`, SHA-256
`d361369c94ac684600082546f8b1db9c0e631e0c3a8cda5c2853d5c2da94c343`.

## Next architecture gate

This result meets the requested revolutionary local performance gate without
an Azrok-specific HLE. It does not finish the broader HQEMU compiler:

1. keep #617's 13 directed / 103-block / 30.2575%-entry plan as compiler input;
2. add dynamic per-site edge counts and CPU-time attribution;
3. fuse the admitted regions into one body so internal edges avoid both
   `NormalCPU::run` and `wasmStartJITOp`, rather than only using larger replay
   coverage and intra-body loops;
4. use spare Workers for compilation/publication after quiescence;
5. admit HLE only for a whole function that independently clears a measured
   CPU-time threshold, not because it ranks highly by entry count.
