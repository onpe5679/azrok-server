# 623 — Acknex HLE terminal-relocation matcher fix

Date: 2026-08-31 KST

## Conclusion

- **VERIFIED B1 failure:** the first actual-PatHouse whole-function HLE run
  reached the helper `23,391,040` times but completed it zero times. Every
  entry fell through `FallbackCodeBytes`; all other fallback counters were
  zero. Its diagnostic 13.9651 FPS is rejected and is not an HLE speed result.
- **VERIFIED root cause:** both exact six-byte `FF 25` thunks place a four-byte
  relocation at offset 2, so the suffix after the relocation has length zero.
  `codeMatchesRelocated()` nevertheless sent this empty suffix to
  `readOnlyMemoryEquals()`, whose `readable()` contract rejects zero lengths.
  Therefore byte-exact live thunks were unconditionally rejected.
- **VERIFIED minimal correction:** an empty prefix or suffix is now skipped;
  every non-empty byte and the relocated dword are still compared exactly.
  No module, RVA, decoded-block-hash, live-target, CPU-state, memory or alias
  guard was weakened.
- **VERIFIED regression fixture:** exact terminal relocations succeed at both
  preferred and current ASLR bases. A one-byte opcode mutation and a one-byte
  relocation mutation each fail closed with the exact component, offset,
  address, expected byte and actual byte recorded.
- **VERIFIED failure containment:** ABI v2 records a component-level mismatch
  and one atomic first-failure record. A rejected code contract is cached only
  negatively for the same process/mapping generation, preventing millions of
  repeated full comparisons. Successful contracts are not cached, so SMC and
  IAT changes remain checked on every helper entry.
- **VERIFIED fixed actual activation:** a fresh ABI-v2, cache-off PatHouse run
  reached `7,305,872` helper entries, completed `7,304,116`, retained `1,756`
  legitimate type fallbacks, and recorded zero code, live-target or component
  mismatches. A direct CDP screenshot was visually confirmed as the real
  Azrok1 PatHouse 3D room.
- **VERIFIED grouped performance rejection:** after exact ABI-v2 regrouping,
  fresh-process actual-PatHouse A1/B1 measured `40.7870 -> 10.9649 FPS`.
  Frame time changed `24.5176 -> 91.2001 ms`, **271.98% worse**. The B1 helper
  succeeded `15,802,344 / 15,804,108 = 99.9888%`; this is no longer a matcher
  failure. Per-element host import/guard/math is catastrophically slower than
  the existing grouped JIT SSE path, so whole-function HLE is rejected and not
  deployable.

## Actual B1 failure

Readback from `artifacts/performance/acknex_hle_b1_counters_20260831.json`:

```text
candidateAccepted       1
helperEntries           23,391,040
helperSuccess           0
fallbackCodeBytes       23,391,040
fallbackIdentity        0
fallbackLiveTarget      0
all remaining fallbacks 0
```

The candidate rendered the real PatHouse, but the helper performed five code
range comparisons and then executed the original generated guest body on every
call. Its 13.9651 FPS versus the 42.5465-FPS control measures this repeated
validation catastrophe, not the transform HLE.

## Exact matcher defect

Both Acknex import thunks have this relocation shape:

```text
length             6
opcode prefix      FF 25       (offset 0, length 2)
absolute IAT dword             (offset 2, length 4)
suffix length      6 - 2 - 4 = 0
```

The old predicate was logically:

```text
compare(prefix length 2)
AND compare(relocated dword)
AND compare(suffix length 0)
```

`readOnlyMemoryEquals()` begins with `readable()`, and `rangeNoWrap()` defines a
valid range as `len && address + len <= 2^32`. The last call therefore returned
false for every exact terminal relocation. The validation order checks the
entry body first and `ThunkCoord` second, explaining why B1 never reached the
live-IAT check or any later fallback.

The ABI-v2 pre-fix fixture made this observable without relaxing the guard:

```text
component  ThunkCoord (2)
offset     0xFFFFFFFE
expected   0x101
actual     0x101
meaning    fast predicate rejected, but a complete byte scan found no mismatch
```

This also agrees with independent PE inspection:

- exact `acknex.dll` SHA-256:
  `876f6870f6858c3829c0830415bf30cf7dd375590810eef231a7e6b1a68eedc6`;
- entry relocation: `+46760 + 0x13`;
- thunk relocations: `+84364 + 2`, `+84477 + 2`;
- target kernels: no base relocations;
- the current live witness already matched both thunks 6/6 bytes.

Thus ASLR, mapped-file provenance and stale target bytes are not this failure's
cause.

## Minimal fix and fail-closed behavior

`codeMatchesRelocated()` now treats only a structurally empty comparison edge
as vacuously true:

```text
prefix length == 0          -> do not call the memory comparator
relocated dword             -> still exact
suffix begins at total len  -> do not call the memory comparator
all non-empty edges         -> still exact
```

The success path is deliberately not cached. It continues to revalidate the
entry, two thunks, two target kernels and both live IAT targets on each helper
entry. The new negative cache is safe in the opposite direction: once a
mapping generation fails, later byte repair cannot make that process silently
execute HLE; the mapping must change first.

ABI v2 appends these diagnostics without changing the first 21 ABI-v1 words:

- five code-component mismatch counters;
- negative-cache fallback count;
- first mismatch state, component, offset, address, expected, actual, base,
  entry, process id and mapping generation.

## Verification

The COOP/COEP Edge fixture reports:

```text
Acknex transform-island SHA/RVA/hash/IAT differential/fallback fixture OK
Test Acknex transform-island HLE differential/fallback ... OK
```

It covers:

1. preferred base `0x10000000` and current base `0x7F3A0000`;
2. NormalCPU differential state/memory results;
3. exact six-byte terminal-relocation admission;
4. thunk opcode offset-0 mutation rejection;
5. thunk relocation offset-2 mutation rejection;
6. component/byte evidence and negative-cache behavior;
7. all original identity, code, IAT, MXCSR, segment, stack, alias, alignment,
   memory and type fallbacks.

Fixed isolated runtime:

```text
stem  boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1acknextransformislanddiag2
ABI   2 / 37 U64 words
reloc 12,969,624 / capacity 262,144
JS    330,584 bytes / a88c68ec1784fd19361364c80851174c8fdd3acca322969474955cd93586865e
Wasm  3,078,299 bytes / e5df5c792943d5d6a332f5522d897723985b47ea183ca7d24c49321819267ba1
```

## Fixed actual PatHouse activation

The first fresh ABI-v2 runtime was intentionally launched with `jitCacheUrl=off`
to separate helper correctness from grouped-cache/runtime-map compatibility.
Direct counter readback after PatHouse entry showed:

```text
candidateAccepted             1
helperEntries         7,305,872
helperSuccess         7,304,116
fallbackType              1,756
fallbackCodeBytes              0
fallbackLiveTarget              0
codeMismatch*                   0
firstMismatch                none
transform3x3Runs       7,304,116
transformCoordRuns     7,304,116
```

The `1,756` type fallbacks are the original `matrixRecord.type != 3` path, not
a guard defect; they continue through the unchanged guest body. Code identity,
both thunks, both target kernels and both IAT targets remained accepted.

Screenshot:

```text
path   artifacts/performance/acknex_hle_diag2_cacheoff_live_20260831.png
bytes  784,400
SHA256 847d46278e97ad839197a4a7c9791d09b0c928b13a11c407f0c039efad72461c
review actual PatHouse 3D: Azrok1, character, HUD, furniture and room geometry
```

The visible 14.3-FPS HUD at capture is explicitly non-canonical: cache-off
compiles the current corpus during play and is not comparable to grouped B.
This smoke proves activation and semantics only.

## Exact-runtime grouped frame-time rejection

The ABI-v2 runtime reported relocation map `12969624 / 262144`. The HLE raw
record was regrouped against that exact map and unioned with the 84 production-B
keys absent from the new run. The resulting cache is a strict key superset:

```text
runtime stem  boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1acknextransformislanddiag2
cache         azrok-jit-grouped-acknextransformislanddiag2-abi2-union-20260831.zip
cache SHA256  f14a3cdf730ba0bf4f2a7dc543eacb2e8ed039d7b9ed3463b5754db8e4f3e069
manifest SHA  e089a58f7cc901de65b08c02c58ef997b30a7568bbfa2d1717d82ba634b16002
groups        145
entries       44,458 (all 44,395 production-B keys plus 63 HLE-run-only keys)
patches       33,930
```

One first candidate launch ended before any Present and is invalid. It was
closed and retried only after an explicit account-release wait. The valid
fresh-process pair used identical 45-second scene settle, 15-second warmup and
30-second direct-Present windows:

| leg | Presents / wall | FPS | frame time | visual |
|---|---:|---:|---:|---|
| A1 production B | 1,224 / 30.009536 s | 40.7870 | 24.5176 ms | PatHouse before/after |
| B1 whole HLE | 329 / 30.004769 s | 10.9649 | 91.2001 ms | PatHouse before/after |

```text
FPS effect        -73.1167%
frame-time effect +271.9779%
```

B1 counter readback proves the helper was active rather than falling through:

```text
helperEntries       15,804,108
helperSuccess       15,802,344  (99.9888%)
fallbackType             1,764
fallbackCodeBytes             0
fallbackLiveTarget            0
all codeMismatch*              0
transform3x3Runs      15,802,344
transformCoordRuns    15,802,344
```

The candidate is therefore **REJECTED**, not merely inconclusive. A2 was not
run because a 3.72x frame-time regression is far outside the 10% acceptance
gate and the user explicitly forbids spending more legs on sub-threshold
candidates. The verified transform semantics remain reusable; the next attempt
must amortize the import and guard over the outer `+49650` loop.

## Files and artifacts

- `tools/boxedwine_local/bwujit_threaded_abi/source/emulation/cpu/wasm/wasmJitAcknexTransformIsland.cpp`
- `tools/boxedwine_local/bwujit_threaded_abi/source/emulation/cpu/wasm/wasmJitAcknexTransformIsland.h`
- `tools/boxedwine_local/bwujit_threaded_abi/source/test/cpu/testWasmJitAcknexTransformIsland.cpp`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/makefile`
- `tools/browser_diagnostics/collect_acknex_transform_island_counters.mjs`
- `artifacts/performance/acknex_hle_b1_counters_20260831.json`
- `artifacts/performance/acknex_hle_matcher_boundary_fix_20260831.json`
- `artifacts/performance/acknex_transform_island_fixture_edge_abi2_20260831.json`
- `artifacts/performance/acknex_hle_diag2_cacheoff_live_20260831.json`
- `artifacts/performance/acknex_hle_diag2_cacheoff_live_20260831.png`
- `artifacts/performance/acknex_hle_diag2_ab_20260831.csv`
- `artifacts/performance/acknex_hle_diag2_b1_valid_counters_20260831.json`
- `artifacts/performance/acknex_transform_island_diag2_abi2_union_cache_20260831.json`

## Remaining gate

1. keep the whole-function HLE runtime/cache isolated and undeployed;
2. reuse its bitwise-verified transform kernels inside a bounded 64-element
   `+49650` outer-loop helper so code/IAT guards and the import boundary are
   amortized across a chunk;
3. preserve partial-commit/fault/yield/redecode semantics and repeat the same
   fresh-process 10% frame-time gate.
