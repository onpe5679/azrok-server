# 624 — Acknex +49650 batch64 HLE rejected; host math is the wrong surface

Date: 2026-08-31 KST

## Conclusion

- **VERIFIED implementation:** an isolated ABI-v3 runtime intercepts exact
  `acknex.dll+0x49650` and commits at most 64 complete transform elements per
  helper call. It preserves signed `JL`, lazy flags, ESP/EIP, partial commit,
  safe fallback, stale-code re-decode, yield, termination, bailout and mapping
  epochs. The Edge differential fixture passes preferred, historical and
  current ASLR bases.
- **VERIFIED real amortization:** actual PatHouse B1 processed `24,265,220`
  elements in `383,005` chunks, or `63.3548` elements/chunk. Element-to-import
  boundary count fell **98.4216%**. Code/live-target mismatches and stale exits
  were zero.
- **VERIFIED performance rejection:** production B A1 measured `46.1453 FPS`
  (`21.6707 ms/frame`); batch64 B1 measured `13.2638 FPS`
  (`75.3932 ms/frame`). FPS fell **71.2564%** and frame time worsened
  **247.9041%**. Both pre/post windows visibly show the real PatHouse.
- **VERIFIED root boundary:** reducing import/guard frequency was not enough.
  The C++/SIMDe host transform math itself is far slower than the existing
  generated Wasm/JIT SSE body. Whole-function and batch64 HLE are both rejected
  and remain undeployed.
- **NEXT:** reuse the verified semantics only as an oracle. The next candidate
  must fuse the original generated-Wasm bodies directly, keeping math in Wasm
  and removing dispatcher edges without calling the host helper.

## Why the first outer recording was invalid

The first AOL raw archive did not contain the helper arm at `+49650`. The
compile-time matcher assumed the 13-op/33-byte persistent entry was one decoded
linked list, but the ordinary decoder ends its first list at the direct CALL
after three ops. Conversely, record mode can retain the ten continuation ops.

The corrected admission contract hashes the exact first three ops / nine bytes:

```text
MOV EDX,EBX
MOV ECX,EDI
CALL acknex+46760
normalized hash 0x4FA89EE0 at all three tested bases
```

It permits an optional continuation after that exact prefix. The helper still
validates the full 33 live bytes, exact backing DLL SHA, +46760 body, both
thunks, both transform kernels and both live IAT targets before the first
write. Thus record-path compatibility did not weaken live identity.

The fixed raw module's grouped export contains exactly one
`call helpers.fn_36` followed by the outcome check. WAT inspection was done
before any browser run.

## Fixture gate

The isolated Edge fixture passes:

```text
Acknex +49650 batch64 outcome/flags/ESP/EIP/fallback/epoch fixture OK
Test Acknex +49650 batch64 outer-loop fusion ... OK
0 tests FAILED
```

Covered counts include `0/1/63/64/65/1964`, plus partial type fallback,
element-zero safe fallback, injected yield/bailout/epoch/termination,
stale-code exit, signed-JL overflow boundaries, mprotect epoch and generated
admission at `0x10000000`, `0x7F360000` and `0x7F3A0000`.

## Exact candidate identity

```text
runtime stem  boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1acknexouterloop1
JS SHA256     342a3053e619cada3cb6f6da796bece00e919cab8ee9ce2b1c56f02c079dd3e6
Wasm SHA256   5cca4830eddf5b65e3fbc2dd24aab5cbcf223f7c06dcb49eaf9bcc6f0ea1b893
ABI           3 / 51 U64 words / 408 bytes
reloc map     12969688 / 262144

cache         azrok-jit-grouped-acknexouterloop1-prefixgatefix2-abi3-union-20260831.zip
cache SHA256  0259f1a6451da28c2a893dba2850f493d12287ee0d09490e80f504240cdde620
manifest SHA  ee3a1d92b69471a8ee97393e58014e33a19f28fe98e59350d2de3686d24567fe
groups        145
entries       44,483 (production-B key superset)
patches       34,026
```

## Actual PatHouse result

| leg | Presents / wall | FPS | frame time | scene |
|---|---:|---:|---:|---|
| A1 production B | 1,385 / 30.013890 s | 46.1453 | 21.6707 ms | PatHouse before/after |
| B1 AOL64 | 398 / 30.006441 s | 13.2638 | 75.3932 ms | PatHouse before/after |

The first automatic B1 scene-ready wait expired as the late PatHouse transition
was becoming stable. The browser stayed on the exact URL and registered cache;
an actual-PatHouse screenshot and counter snapshot were taken, then the same
process received a 15-second warmup and official 30-second direct-Present
window. The measured B1 is therefore valid, while the expired preflight itself
is not a performance row.

Final B1 counters:

```text
outerHelperEntries     384,769
outerSafeFallback        1,764
outerPartialResume     383,005
outerStaleCodeExit           0
outerCompletedLoops     12,355
outerChunks            383,005
outerElements       24,265,220
outerChunkLimitStops   370,650
outer yield/bailout/termination/epoch  0 / 0 / 0 / 0
codeMismatch*                 0
```

The measured structural amortization is real, but it made no positive frame
contribution. Per the 10% rule, A2 was skipped and AOL64 was immediately
rejected.

## Artifacts

- `artifacts/performance/acknex_outer_loop_ab_result_20260831.json`
- `artifacts/performance/acknex_outer_loop_b1_final_counters_20260831.json`
- `artifacts/performance/acknex_outer_loop_fusion_contract_20260831.md`
- `artifacts/performance/acknex_outer_loop_fusion_contract_20260831.json`
- `artifacts/performance/acknex_outer_loop_prefixgatefix2_raw_20260831.json`
- `artifacts/performance/acknex_outer_loop_prefixgatefix2_abi3_union_cache_20260831.json`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-acknex-outer-loop-source.mjs`
- `tools/browser_diagnostics/build_acknex_hle_union_cache.py`

## Next gate

1. locate/co-locate the current `+49650`, `+46760`, thunk and two SSE bodies in
   generated Wasm;
2. clone or inline those original Wasm functions inside the caller group,
   preserving the existing relocation and fault paths;
3. eliminate the direct/dispatcher edges without any host helper import;
4. run the same actual-PatHouse 10% frame-time gate and reject immediately if
   it misses.
