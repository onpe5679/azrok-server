# 625 — Acknex direct generated-Wasm fusion activated and rejected

Date: 2026-08-31 KST

## Conclusion

- **VERIFIED implementation:** a post-link transformer rebinds only the exact
  current `acknex.dll+0x49650` export in `group-0103.wasm` to a pure-Wasm SIMD
  outer transform macro. The other 142/143 groups remain byte-identical, all
  504 target-group exports and 120 relocation patches are preserved, the
  original function remains as same-module fallback, and no host transform
  helper is imported.
- **VERIFIED activation:** after correcting the transform-wrapper relocation
  immediate from offset 20 to the source-proved offset `0x13` (19), actual
  PatHouse executed `41,892,525` fused elements. This is not an entry-count
  proxy: the candidate's own pure-Wasm fast-element counter advanced.
- **VERIFIED performance rejection:** the adjacent production control A2 was
  `52.4548 FPS / 19.0640 ms`; active fusion5 B2 was
  `50.7276 FPS / 19.7131 ms`. FPS fell **3.2927%** and frame time worsened
  **3.4049%**. Both candidate screenshots visibly show the real PatHouse.
  The candidate misses the required 10% frame-time reduction and is rejected;
  no A3 or deployment is justified. The rejected fusion3/fusion4/fusion5 ZIPs
  were removed after preserving hashes, counters, screenshots and deterministic
  regeneration tooling; the production cache remains present and unchanged.
- **VERIFIED interpretation:** the first apparent A1-to-fusion3 gain was drift,
  not fusion. A1 was 46.6818 FPS, fusion3 B1 52.4289, and the immediately
  following production A2 52.4548. Fusion3 had `fastElements=0` and B1/A2 was
  `-0.0494%` FPS. Control drift A1-to-A2 was `+12.3667%`.
- **NEXT:** do not keep tuning this per-game macro. Capture an authoritative
  current-production-B owner-thread CPU profile, then admit only a structural
  candidate whose measured time share can clear 10%. The two live candidates
  are mapping-epoch cached region translation and dependency-gated generated-
  Wasm parallel execution; their current exact time shares remain unknown.

## Failure sequence that produced the valid candidate

### fusion1 — semantic boundary caught before browser performance

The first macro incremented `CPU::blockInstructionCount` on the natural,
bailout and 64th-budget exits. The original bounded loop adds nine instructions
only for an admitted internal backedge. The fixture was expanded and fusion1
was removed before it could become a performance result.

### fusion2 — diagnostic counters corrupted the live relocation map

The runtime's exported `relocMapBase=12968408` is the usable map pointer after
an explicit 64-U32/256-byte reserve. fusion2 incorrectly wrote diagnostic
counters at `relocMapBase + words 60..63`, which are live routing slots.
Browser console capture directly reported `RuntimeError: memory access out of
bounds`; the corrupted run reached `15,821,784` macro fallback entries.

The corrected storage contract is:

```text
counter storage base  12968152 = relocMapBase - 64*4
reserve words 60..63  12968392 / 396 / 400 / 404
usable reloc map      12968408
```

The fixture now changes the reserve counters while proving live map sentinel
slots 60 and 62 remain unchanged. The structural verifier also rejects the
four old live-map counter addresses if they appear in the generated Wasm.

### fusion3 — safe but no fast execution; apparent gain was drift

fusion3 registered the exact opt-in loader identity and rendered PatHouse
without corruption. Its process-lifetime counters were:

```text
entries          46,760,676
fast elements             0
initial fallback 46,760,676
partial/budget            0
```

Fresh-process visual A-B-A:

| leg | condition | Presents / wall | FPS | frame time |
|---|---|---:|---:|---:|
| A1 | production B | 1,401 / 30.011703 s | 46.6818 | 21.4216 ms |
| B1 | fusion3, all fallback | 1,573 / 30.002520 s | 52.4289 | 19.0734 ms |
| A2 | production B | 1,574 / 30.006809 s | 52.4548 | 19.0640 ms |

The closest B1/A2 pair is neutral and the candidate executed no fused element.
Therefore the A1/B1 `-10.96%` apparent frame-time change is not causal.

### fusion4 — exact first-failure diagnosis

A diagnostic-only variant replaced aggregate fallback/partial atomics with 55
mutually exclusive first-failure buckets in the same reserve. In actual
PatHouse all `33,527,244` entries selected exactly one reason:

```text
entry-code-transform-wrapper  33,527,244
all other reasons                       0
```

Direct source comparison then found the one-byte error:

```text
HLE/source relocation offset   0x13 / 19
fusion1..4 specification       20
relocated immediate            40 4c 6a 7f
following opcode byte          8b (must remain unchanged)
```

fusion5's fixture and cache verifier pin all five values.

## fusion5 exact identity and activation

```text
runtime stem
  boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1

cache
  azrok-jit-grouped-multidirectloops1-directwasmfusion5-currentabi1-20260831.zip
archive SHA-256
  6ca35b6aaf2203a068dcd50fe1f6c11563ede4a356c65394fd9a14dc0dfa553f
manifest SHA-256
  4ff6a443b258aae82c47565f192fcefbc319da34e2616fc5317d29f719602b66
semantic contract SHA-256
  31d3bde0c643559435eafc806d70ca371573fe065c200dab5473e9ab2fa95145
target group SHA-256
  bd5065de5f729eb730893cfd6eea463b74ea99c8651805ec7acdf904b5cc0d61
```

The loader accepts this candidate only with explicit
`acknexDirectFusion=1` and exact runtime/cache/archive/manifest/semantic/source
runtime/target-group pins. Production defaults are unchanged.

Process-lifetime counters after the B2 measurement:

```text
entries             2,212,374
fast elements      41,892,525
initial fallback    1,244,571
partial stops         967,803
fast elements/entry    18.9356
```

Dominant safe exits were single-page translation boundaries:

- initial matrix translation: 605,880;
- initial source/destination translation: 417,314 / 219,638;
- partial source/destination translation: 408,882 / 219,630;
- chunk budget: 330,876.

This proves that moving math into Wasm and removing the host helper was not
enough. The macro repeatedly pays full code admission plus per-element softMMU
translation and frequently returns at page boundaries. The active result is
slower than production, so further tuning is not admitted without a new
current-B CPU-time bound.

## Verification

Passed for fusion5:

```text
verify-acknex-direct-fusion-cache.mjs
test-acknex-direct-fusion.mjs
verify-acknex-direct-fusion-loader-gate.mjs  (20 cases)
python -m unittest tools.test_d3d9web_page_contract tools.test_azrok_home_contract
44 tests OK
```

The full tools suite passed 310/310 at the fusion3 checkpoint. A later full
suite attempt at the fusion4 checkpoint had one unrelated structured-capture
fixture `FileNotFoundError`; focused fusion/page/home verification remained
green and no server/capture code was changed by this work.

## Artifacts

- `artifacts/performance/direct_wasm_fusion_ab_20260831.csv`
- `artifacts/performance/direct_wasm_fusion_ab_result_20260831.json`
- `artifacts/performance/direct_wasm_fusion_b1_counters_20260831.json`
- `artifacts/performance/direct_wasm_fusion4_reason_counters_20260831.json`
- `artifacts/performance/direct_wasm_fusion5_b2_counters_20260831.json`
- `artifacts/performance/timewindow_reanalysis_20260831.md`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/acknex-direct-fusion-spec.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/boxedwine-wasm-jit-cache-acknex-direct-fusion.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/test-acknex-direct-fusion.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-acknex-direct-fusion-cache.mjs`
- `tools/boxedwine_local/verify-acknex-direct-fusion-loader-gate.mjs`

## Next gate

1. expose the exact current Worker realm's thread-local `CPU*` in an isolated
   diagnostic runtime;
2. join it to the owner pointer used by the current-B entry histogram;
3. collect stable actual-PatHouse CPU profiles only for that exact owner;
4. measure transform-region and softMMU/TLB shares;
5. implement neither parallel loop execution nor mapping-epoch span caching
   unless its measured Amdahl bound can reduce frame time by at least 10%.
