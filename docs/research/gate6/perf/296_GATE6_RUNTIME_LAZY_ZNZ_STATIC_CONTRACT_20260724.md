# 296. Gate 6 runtime-lazy Z/NZ pure-Wasm contract

## Status

**VERIFIED static/build/differential fixture/loader gate; cache-OFF PatHouse,
replay, and performance NOT VERIFIED.** This is a new candidate, isolated from the
rejected parity67 and typed direct-tail paths.

The first isolated `azrokMultiThreadedJitAudioO3AsyncRingRuntimeLazyZnZ`
pthread `-O3` build was deliberately invalidated before deployment when static
audit found one unreturned scratch local (`typeLocal`) in the new emitter
path. The source now frees it. The rebuilt candidate `boxedwine.wasm` is
3,050,503 bytes, validates as a `WebAssembly.Module`, and its glue binds all
six runtime-lazy Z/NZ capability/layout exports. The candidate is still not
deployed.

`verify-runtime-lazy-znz-loader-gate.mjs` passes 17 fail-closed cases plus
eight exact PatHouse-page gate fragments. It covers both cache/runtime feature
cross-pair directions, malformed manifests, every required getter absent, and
each live layout-field mismatch. The existing pair page and shell GP verifiers
continue to pass 5/5 and 9/9.

The dedicated pthread Wasm-JIT fixture is built with
`BOXEDWINE_WASM_JIT_INLINE_RUNTIME_ZNZ` and directly executes a producer and
Z/NZ consumer across an indirect compiled-block boundary. It passes all 49
producer enum values (including b8/b16 high-byte masking, DSHL/DSHR/NEG),
NONE, CFOF and repeated-CFOF, plus NZ-nonzero. Browser output records
`Test runtime lazy Z/NZ across indirect JIT block boundary ... OK`. The wider
639-test run still has the pre-existing Emscripten-6 broker `callHandler`
failures; those occur before the Z/NZ fixture and are not treated as a
candidate regression. Invalid lazy types cannot be dynamically constructed
without a candidate-only force hook because `FLAGS_NULL` has no LazyFlags
implementation; their helper-only and 8-GP nonmutation claims remain static.

## Direct static facts

`JitWasmCodeGen::getCondition()` already inlines Z/NZ only when its
compile-time `currentLazyFlags` names a small known producer set. At a block
entry, merge, or interpreter bailout that cache is deliberately reset to
`FLAGS_NULL`, then the existing generic path calls `helpers.fn_16`/`fn_17`.
Those exact Z/NZ helpers read `CPU::getZF()` and write only `CPU::tmpReg`;
they do not mutate GP registers, EIP, or the lazy tuple. The specialized
invalid-state fallback may therefore retain the helper without the generic
all-GP synchronization/invalidation boundary.

The verified lazy type contract is:

| runtime type | ZF source |
| --- | --- |
| `FLAGS_NONE` (0) | architectural `CPU.flags & ZF` |
| producer 1..49 | masked `CPU.result` is zero |
| `FLAGS_CFOF` (50) | exactly one `CPU.lazyFlagTypePrev` indirection, then above |
| `FLAGS_NULL` (51), second CFOF, out of range | existing Z/NZ helper only |

All producers 1..49 are result based. The b8/b16 masks are mandatory because
`CPU::result` is a union and its upper bits can preserve an older wider value.
The runtime candidate uses b8 for 15 producers, b16 for 17 (including DSHL/
DSHR), and b32 for 17.

## Fail-closed deployment contract

The candidate adds `runtimeLazyZNZ` to its fresh grouped-cache manifest and a
runtime capability getter plus exact getters for flags/result/lazy-type/
lazy-type-prev offsets and `ZF`. The PatHouse loader rejects both directions
of a cross pair: a manifest declaring the feature with a runtime that lacks
it, or a feature runtime with a manifest that does not declare it. It also
rejects any kind/version/offset/mask/enum/fallback mismatch before group
registration.

## Required gates before any FPS sample

1. Differential fixture: NONE, CFOF to NONE/b8/b16/b32, every producer width
   with high-bit garbage, NULL/out-of-range fallback selection, block entry,
   post-`emulateSingleOp`, Jcc/SETcc/CMOV/LOOPZ/LOOPNZ, and all eight GP words
   unchanged by the Z/NZ fallback.
2. New runtime build with parity define absent; fresh record and fresh grouped
   cache with the new manifest only.
3. Loader negative cases for missing runtime feature, missing manifest feature,
   and each offset mismatch.
4. cache-OFF visible 1024x768 PatHouse integrity (post-pulse), zero bridge
   async-ring errors, no compile/console error, and recent heartbeat.
5. Fresh replay must report `fn_16/fn_17=0/0` on the same candidate cache.
   Only then run its independent visible 30-second A-B-A.
