# 613 — Current PatHouse `NtCurrentTeb` broad original-region router: neutral

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED implementation:** ten original registered exports spanning Wine
  `NtCurrentTeb`, PIC/PLT, glibc `pthread_getspecific`, and the Wine epilogue
  are co-located in one group.  Nine internal routers preserve the real TLS,
  stack, GOT, condition, and return instructions.
- **VERIFIED publication safety:** an opt-in runtime gives every imported
  zero-reloc original entry an exact U32 publication token.  Same-EIP different
  hash, invalidation, null, multi-worker install, and quiescent free fixtures
  pass.  Default runtime allocation remains macro-off unchanged.
- **VERIFIED loader safety:** manifest ABI1 and runtime getter ABI1 are strict
  equals in both source/served shell and the PatHouse page.  URL mode, runtime
  stem, raw/archive/grouped-manifest hashes, and control/candidate cache name
  are pinned before registration.
- **VERIFIED visual/runtime:** actual PatHouse A-B-A-B-A yields control mean
  26.8230 FPS and candidate mean 26.8275 FPS: **+0.0167%**.  Adjacent candidate
  effect median is **+0.2092%**.
- **REJECTED as a gain / NOT ADOPTED:** the broad 39-site router is neutral.
  Generated-entry frequency was not CPU-time proof; saved dispatcher work is
  offset by publication/depth/EIP guards, especially on residual routes.
- **NOT VERIFIED slowdown:** all effects are within noise.  The result rejects
  the optimization benefit, not semantic correctness.

## Exact hot chain

The accepted anchored census observed 283,067 complete calls in 20.008940
seconds, 600.99 calls/Present.  The co-located sequence is:

```text
10679184 NtCurrentTeb entry
10627B70 ntdll BX PIC thunk
1067918D NtCurrentTeb continuation
10627A60 pthread_getspecific PLT
104F0DB0 libc pthread_getspecific entry
1059200C libc BX PIC thunk
104F0DBD libc key/TLS continuation
104F0DF8 libc value/generation continuation
104F0E11 libc epilogue
106791A1 ntdll epilogue
```

The nine intermediate transitions total 2,547,603 per 20 seconds, 12.5854%
of owner-CPU generated-entry count.  This is a transition-count surface, not a
CPU-time share.

## Zero-reloc publication runtime

Opt-in macro:

```text
BOXEDWINE_WASM_JIT_ZERO_RELOC_PUBLICATION_TOKEN
```

Runtime:

```text
stem   boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2zeroreloctoken1
JS     329853 bytes
SHA256 2a4aff3dd4e1ad0922456c3652919cc2f2b68f4dcfe155620662d0f3cbebdf06
Wasm   3056416 bytes
SHA256 cdc93a884f7724d5713030b414f9f7187258fa2ec732a5905409c739064b565a
```

Linked ABI:

```text
zero-reloc token ABI 1
reloc map/cap         12968408 / 262144
pfn/next/depth/bailout 12 / 740 / 1660 / 132
register-thread ABI   2
```

Of 30,550 entries, 2,965 are zero-reloc wrapper-only originals.  The opt-in
adds exactly 11,860 bytes/process plus allocator overhead.  Reloc-positive
27,585 entries retain existing array size/token position.  Internal routers
are not registration rows and receive no token.

The fixture verifies publication, invalidation, same-EIP different-hash
republication, null mismatch, worker-local lazy install, and reclamation after
owner quiescence.  It reports zero failures.

## Pinned-layout cache pair

Control:

```text
azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-originalregion-control1.zip
4806287 bytes
SHA256 7dd66a6347b910333cea01b4a9a614759aa5c7ec85b3edd4f2c646101e03efde
manifest SHA256 9b3bd59325a5479c6c6174094cb14c7346fe599c7c11bb99304df505b94a6aa1
```

Candidate:

```text
azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-originalregion-candidate1.zip
4806354 bytes
SHA256 2c04a9ebd77a67251014b5c989f2ce0555396a59051c716a940c32d95cb2621d
manifest SHA256 f50aebbfb058a070ef7f59983a652b023f409d7920190a9ed4042015c0dd5910
```

Both have:

```text
94 groups / 30550 unique original exports
2965 zero-reloc / 27585 positive-reloc
9 internal routers / 9 router publication patches
28932 total direct-call patches
host group 93: 389 exports + dispatcher + 9 routers
```

All 94 modules validate.  Non-host 93 groups are byte-identical.  Host modules
have equal size; their only function-body differences are exactly 39 router
callee ULEBs.  Control redirects 0/39; candidate redirects 39/39.  Feature-off
regeneration remains byte-identical to currentabi1.

## Router contract

Every candidate source dispatcher call enters a source-specific router.  It
uses the original needsFetch flag, then checks:

1. actual linear EIP equals the exact target;
2. live `CPU::nextOp` is non-null;
3. target reloc/publication array is non-null;
4. atomic live pfn is nonzero and equals the target publication token;
5. reloc-positive word0 equals live nextOp;
6. yield and bailout are zero;
7. direct-chain depth is below 64, then increments depth once.

Mismatch returns to the existing generic dispatcher.  The route graph is a
linear nine-edge DAG, and the final Wine epilogue retains arbitrary caller
return behavior.

The 39 source dispatcher sites split into:

```text
static normal target       9
dynamic normal target      4  (two RETs, PLT/GOT jump, libc epilogue RET)
residual fallback sites   26
```

The broad candidate routes all 39; only 13 are the observed normal chain.

## Fail-closed integration

The shell and page reject:

- manifest ABI1 with runtime getter missing/0;
- ABI1 runtime with a cache that does not request the capability;
- wrong originalRegion URL mode, runtime stem, or cache URL;
- wrong raw-manifest, archive, or grouped-manifest hash;
- control/candidate mode mismatch.

Only baseline 0/0 and region 1/1 capability pairs are accepted.  Static shell
syntax and page contract tests pass.

## Actual PatHouse A-B-A-B-A

All rows use a fresh visible Edge profile/process, 180-second scene settle,
20-second warmup, and 45-second exact Present window.  Every before/after pair
was manually reviewed as actual PatHouse.

| Order | Condition | Presents / wall | FPS |
|---:|---|---:|---:|
| 1 | A1 pinned control | 1,187 / 45.013258 s | 26.3700 |
| 2 | B1 broad router | 1,189 / 45.007089 s | 26.4181 |
| 3 | A2 pinned control | 1,212 / 45.011749 s | 26.9263 |
| 4 | B2 broad router | 1,226 / 45.012464 s | 27.2369 |
| 5 | A3 pinned control | 1,223 / 45.008199 s | 27.1728 |

```text
A mean = 26.823033 FPS
B mean = 26.827500 FPS
B/A    = +0.016652%

adjacent effects = +0.1824%, -1.8874%, +1.1535%, +0.2359%
adjacent median  = +0.2092%
```

Control A1→A3 drift is +3.0444%; candidate B1→B2 drift is +3.0994%.
Despite borderline drift, both mean and median are effectively zero.

## Next gate

Build a selective candidate on the exact same runtime/layout:

- rewrite only nine statically proven normal sites in five sources;
- retain both dispatcher sites for each of four dynamic-normal sources, eight
  router calls total;
- total redirected calls 17, normal paths 13, residual router paths 4;
- leave the other 22 statically residual sites on the original dispatcher.

This isolates whether broad residual guard cost hid a smaller real gain.

## Artifacts

- `tools/boxedwine_local/bwujit_threaded_abi/source/emulation/cpu/wasm/jitWasmCodeGen.cpp`
- `tools/boxedwine_local/bwujit_threaded_abi/source/test/cpu/testWasmJitZeroRelocPublication.cpp`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/boxedwine-wasm-jit-cache-pipeline.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/ntcurrentteb-original-region-spec.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-original-region-cache.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-original-region-router-fixture.mjs`
- `tools/boxedwine_local/index_d3d9web_pathouse.html`
- `tools/boxedwine_local/assets_d3d9web/boxedwine-shell.js`
- `artifacts/performance/regional_ntteb_region_aba_actual_pathouse_20260830.csv`
- `artifacts/performance/regional_ntteb_region_aba_actual_pathouse_visual-review.csv`
