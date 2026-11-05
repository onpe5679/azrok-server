# 410 -- Gate 6 logical-composite32 private candidate source (2026-07-26)

## Status

**VERIFIED source/static route implementation PARTIAL. No build, cache,
browser render, replay or FPS sample has occurred.**

## Implemented private boundary

A new private target
`azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeRuntimeLogicComposite32`
uses a separate build directory and the accepted ABI2/D3D9Web flag family,
plus only `BOXEDWINE_WASM_JIT_INLINE_RUNTIME_LOGIC_COMPOSITE32` and a private
ABI getter export.  Its compile-time exclusion gate rejects tests, the 408
fixture, census/profile paths, Z/NZ/parity/MOVSD/MOVSB/FISTP candidates and
censuses, threaded-body/tail, GP-cache variants and fallback stats.

The generated candidate is a separate `getCondition` arm.  It requires
compile-time `FLAGS_NULL`, exact six conditions, and exact OR32/AND32/XOR32/
TEST32 runtime enums.  Its candidate formulas are the 408 oracle formulas.
The non-admitted branch retains the exact per-condition helper plus `tmpReg`
load with no GP sync/invalidation, matching runtime Z/NZ's directly verified
read-only helper boundary.  Fixture counters and its `CPU` layout remain
unreferenced by production code.

`wasm_jit_get_runtime_logic_composite32_abi_version()` returns 1 only in this
private target and zero everywhere else.  The PatHouse page now accepts its
dedicated `runtimeLogicComposite32=1` mode only with its private stem and
`jitCacheUrl=off`, rejects mixed diagnostic/audio/capture modes, and checks
the runtime getter before guest execution.  This permits the future cache-OFF
render/record gate but deliberately rejects any replay URL until identity pins
are implemented.

The grouped-cache pipeline now has a mutually exclusive
`--runtime-logic-composite32` transform identity.  It requires the exact
private stem, raw-manifest SHA and CPU result/lazy-type offsets, then emits a
separate `azrok-runtime-logic-composite32-v1` runtime identity and the exact
four-type/six-condition/`FLAGS_NULL_ONLY` descriptor.  No transform has run;
the page replay-side final archive/manifest pin and mutation regression remain
absent, so a generated artifact would still fail closed.

## Static checks

The page's complete inline JavaScript parses with Node.  A make dry run
propagates the exact private macro and ABI export to all compile/link commands.
Its final response-file write cannot run under `make -n` because the build
directory is intentionally not created in a dry run; that is a dry-run
filesystem limitation, not a compile result.  No build was started to avoid
creating artifacts before the remaining pipeline/replay identity gate exists.

## Remaining required gate

The page replay path still needs final archive/grouped-manifest pins and
mutation/cross-pair regression.  Until that is done, the candidate can only
be cache-OFF; it cannot obtain a replay cache or any performance role.
