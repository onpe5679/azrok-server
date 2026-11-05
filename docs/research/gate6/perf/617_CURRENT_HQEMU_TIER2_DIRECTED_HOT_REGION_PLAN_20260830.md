# 617 — Current HQEMU-style tier-2 directed hot-region plan

Date: 2026-08-30 KST

> **Important boundary:** `30.2575%` below is the share of current PatHouse
> **owner-generated block-entry hits covered by structurally directed,
> multi-block candidates**. It is not CPU-time coverage, estimated speedup, a
> dynamic internal-edge taken rate, or the number of dispatcher boundaries
> already proved removable. Those three latter quantities remain `UNKNOWN`.

## Conclusion

- **VERIFIED implementation:** a deterministic HQEMU tier-2 candidate planner,
  machine-readable compiler-input plan, source-content map, synthetic fixture,
  and independent verifier now exist. No runtime or production asset was
  modified.
- **VERIFIED directed multi-block surface:** the selected output has 13/13
  multi-block regions, 103 unique blocks, 849 decoded ops in total, and 112
  admitted internal structural edges. Every block is forward-reachable from
  its region entry. Region size is 2–18 blocks and 8–152 ops, below the hard
  256-op ceiling.
- **VERIFIED current owner-entry coverage:** the union covers
  `6,124,880 / 20,242,521 = 30.257496%` of the accepted #607 single-owner
  PatHouse block-entry count. Single-block contribution is exactly zero.
- **VERIFIED fail-closed edge rule:** raw `exits[kind].count` is an emitted-site
  count, not dynamic hotness, and `firstTarget` is only one target witness.
  Only `count == 1` plus a unique exact target may become an internal edge.
  All `count > 1` exits remain `multi-site-first-target-only` dispatcher side
  exits. The selected plan contains 197 side-exit slots, including 21 such
  multi-site ambiguous slots.
- **VERIFIED stable content identity:** selected `Azrok.exe`, `ntdll.so`, and
  `libc.so.6` identities include exact archive hashes and exact extracted-file
  SHA-256 values. Region identity uses module family/content, RVA, and block
  hash rather than install path or runtime load base.
- **INFERRED module mapping boundary:** direct resolver rows account for
  `4,853,948 = 23.978970%` of owner entries. Another
  `1,270,932 = 6.278526%` is assigned by the unique verified archive-file span
  behind directly resolved module bases. Publication must recheck the module
  file hash and every selected block hash; the plan does not promote this
  range inference to direct resolver evidence.
- **NOT VERIFIED performance:** no tier-2 compiler body, background compiler,
  live publication, dynamic edge profile, or actual PatHouse A/B exists yet.
  This is the first executable compiler-input boundary, not a performance
  result and not the requested epoch-making gain by itself.

## Why the old cache pipeline is not tier-2

The existing code contains reusable pieces but does not perform HQEMU-style
background regional optimization:

1. `wasmPgoQuiesce` has useful token/epoch, membership, active-block, capture,
   timeout, and fail-closed release semantics. However the current CPU lifecycle
   hooks are fixture-only and Touch2 does not enable the production PGO macro.
2. Raw exit `count` is incremented when an exit site is emitted, and only one
   `firstTarget` is retained per kind. It is not an edge-frequency profile.
3. `buildGraph()` uses that manifest as structural topology. Existing grouping
   forms weak connected components, splits oversized components by Wasm byte
   size, and bin-packs them. It is not owner-hot directed region formation.
4. Binaryen optimization runs on each block before grouping. There is no
   whole-region post-fusion optimization that can keep GP/flags/x87 state in
   locals across block edges.
5. `wasmModuleMerger` validates compatible module shapes and concatenates
   bodies/exports, but it receives no CFG or edge semantics and does not fuse
   cross-block state. MT runtime merging is performed by the submitting CPU,
   not a spare background compiler Worker.

Relevant source boundaries:

- `source/emulation/cpu/wasm/wasmPgoQuiesce.h:33-57`
- `source/emulation/cpu/wasm/wasmPgoQuiesce.cpp:153-277`
- `source/emulation/cpu/normal/normalPlatformMultiThreaded.cpp:27-190`
- `project/emscripten/makefile:264-268`
- `source/emulation/cpu/wasm/jitWasmCodeGen.h:918-928`
- `source/emulation/cpu/wasm/jitWasmCodeGen.cpp:15196-15448`
- `source/emulation/cpu/wasm/jitWasmCodeGen.cpp:16628-16649`
- `project/emscripten/boxedwine-wasm-jit-cache-pipeline.mjs:3315-3524`
- `project/emscripten/boxedwine-wasm-jit-cache-pipeline.mjs:3841-3905`
- `source/emulation/cpu/wasm/wasmModuleMerger.cpp:167-427`

## Planner contract

The planner combines four evidence layers:

1. the current 30,550-entry raw v5 corpus and its structural exit witnesses;
2. the exact grouped-cache order used by the #607 counter buffer;
3. the accepted #607 current PatHouse owner-entry counts;
4. the #608 top-100 resolver plus exact root/app archive content identities.

Admission and selection are deterministic:

- minimum owner hit count: 32;
- maximum decoded ops per region: 256;
- module boundary: never crossed;
- internal edge: forward, unique exact target, and emitted-site count exactly 1;
- ambiguous, unknown, cross-module, unobserved, and multi-site exits: dispatcher;
- candidate: at least two blocks, all forward-reachable from one entry;
- selection: descending union owner-entry coverage, disjoint block sets, stable
  tie-breaks;
- stop: first deterministic set reaching at least 30% of all owner entries.

The candidate inventory contained 2,288 eligible seeds, 1,296 directed
multi-block candidates, and 992 singleton seeds rejected from the coverage
claim. Forty-one overlapping candidates were skipped before the target was
reached.

## Selected result

| Rank | Module | Entry | Blocks | Ops | Owner entries | Share |
|---:|---|---|---:|---:|---:|---:|
| 1 | Azrok.exe | `004DB9B6` | 5 | 63 | 677,566 | 3.3472% |
| 2 | Azrok.exe | `00662CCD` | 13 | 65 | 613,165 | 3.0291% |
| 3 | libc.so.6 | `104F0DB0` | 2 | 38 | 570,027 | 2.8160% |
| 4 | ntdll.so | `1067918D` | 2 | 8 | 566,134 | 2.7968% |
| 5 | libc.so.6 | `104F36A4` | 12 | 53 | 558,179 | 2.7575% |
| 6 | libc.so.6 | `10502743` | 13 | 129 | 539,563 | 2.6655% |
| 7 | ntdll.so | `10638D3C` | 18 | 152 | 503,093 | 2.4853% |
| 8 | ntdll.so | `10635617` | 12 | 55 | 491,207 | 2.4266% |
| 9 | ntdll.so | `10636A7D` | 11 | 74 | 392,417 | 1.9386% |
| 10 | ntdll.so | `106360C4` | 5 | 57 | 351,774 | 1.7378% |
| 11 | ntdll.so | `10635FFE` | 3 | 100 | 289,030 | 1.4278% |
| 12 | ntdll.so | `10679D59` | 2 | 17 | 288,719 | 1.4263% |
| 13 | Azrok.exe | `00592085` | 5 | 38 | 284,006 | 1.4030% |

The output also records every block's raw/counter identity, current owner
hotness, module RVA/file offset, block hash, direct-versus-inferred mapping
status, internal edges, every side-exit slot, SCCs, observed exact-graph
reducibility, and publication/invalidation requirements.

## Exact artifact identities

```text
plan JSON SHA-256
05b49498841f997a14d51a0c95262d77e413538b916f6ed1f324eeb38e76a1af

semantic raw-corpus SHA-256
b573a1c8f4fdd4e41a1f2d5d584d7b064f983dc439e2a36318946d4124488cf7

ASLR/path-independent selected-region semantic SHA-256
be2048b2ec3abce5e7f7ab09b3c483c015ad3836f4f1157aa1ebbe85eae781fd

ntdll.so  3a03b005d9311f521ee26c49dd395850f9a379ba0d0195559bb383309eec88b7
libc.so.6 141319771edb3c2ffbd91d7617dc133bc70eafa3bf718defa60d11ba5a729d7d
Azrok.exe 39680da744df27cf13eae03f675d91c301b3ca9332f6979ca4447fba9908caba
```

## Verification

Commands run from the repository root:

```powershell
node tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/plan-hqemu-tier2-hot-regions.mjs
node tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/test-hqemu-tier2-hot-region-planner.mjs
node tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-hqemu-tier2-hot-regions.mjs --expect-sha256 05b49498841f997a14d51a0c95262d77e413538b916f6ed1f324eeb38e76a1af
```

Verified assertions:

- exact source/archive/module hashes;
- byte-identical deterministic regeneration;
- 13/13 forward-reachable multi-block regions;
- no duplicate selected blocks;
- per-region op count at most 256;
- every block has all three exit slots represented as internal edge or side
  exit;
- every multi-site exit remains a side exit;
- exact aggregate owner-entry coverage at least 30%;
- CPU-time, dynamic transition, and dispatch-removal claims remain absent.

## Files

- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/hqemu-tier2-hot-region-planner-lib.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/plan-hqemu-tier2-hot-regions.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-hqemu-tier2-hot-regions.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/test-hqemu-tier2-hot-region-planner.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/hqemu-tier2-module-content-map.json`
- `artifacts/performance/hqemu_tier2_hot_regions_20260830.json`

## Next implementation gate

The minimum real tier-2 implementation is now sharply bounded:

1. add a per-exit-site identity and owner-filtered dynamic taken/target
   histogram so the `UNKNOWN` dispatch-removal surface becomes measurable;
2. consume this plan in a new DecodedOp/IR region builder, not the current
   body-concatenating merger;
3. materialize CPU state only at the enumerated side exits, retain GP/lazy
   flags/x87 locals across internal edges, and run a whole-region Binaryen pass;
4. compile immutable region packs on spare Workers;
5. use the existing quiescence design as the publication barrier after exact
   runtime ABI, module SHA, block hash, page generation, and SMC checks;
6. only then run actual-PatHouse visual A/B and measure FPS/frame time.

Until steps 1–6 exist, this document proves a sufficiently broad directed
compiler input, not the requested performance improvement itself.

