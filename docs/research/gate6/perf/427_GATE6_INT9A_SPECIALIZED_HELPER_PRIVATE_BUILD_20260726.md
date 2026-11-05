# 427. INT 0x9A re-decode guarded specialized helper: private source and build

Date: 2026-07-26  
Status: **VERIFIED static and private build; cache-OFF runtime NOT VERIFIED**

## Admission

426 closes the last production async P1 row.  This card introduces a new private-only production macro, `BOXEDWINE_WASM_JIT_INT9A_SPECIALIZED_HELPER`, and nothing into the accepted `boxedwine.upstreamjit64fn6inlineabi2` stem.  Its compile guards require multi-threaded Wasm JIT, D3D9Web and its async ring; they reject `__TEST`, direct-normal dispatch, I9F1, both INT9A censuses and the logical-composite candidate.  The new target is:

```text
azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeInt9ASpecialized
Build/AzrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeInt9ASpecialized1
```

No staged asset, HTML route, app ZIP, cache raw, grouped replay or accepted artifact was changed in this card.

## Preserved boundary

**VERIFIED static.** The candidate shares the I9F1-tested re-decode boundary but removes all fixture-only mutation:

1. Generated code commits the current instruction EIP, flushes dirty GP locals, arms the ordinary SMC bailout, then calls one append-only private host helper.
2. The helper obtains a live `DecodedOp`; inaccessible or non-`Int9A` decode falls back to exact `CPU::runNextSingleOp()`.
3. Only a freshly decoded `Int9A` copies the live operation, preserves the normal terminal sentinel, and calls existing `normal_int9A`.  That existing normal operation retains its `START_OP`, all stack reads through `peek32(0..2)`, `callD3D9Web` / JS return-to-EAX behavior and successor processing.
4. Existing traced-stub retirement remains in place.  A delivered exception records a private fault counter, sets the already-fixture-proven bailout marker `2`, and the generated boundary clears active-block state and returns without successor-EIP overwrite.
5. Return invalidates generated GP/segment caches and resets the compile-time lazy-flag assumption to `FLAGS_NULL`, preserving downstream state re-read.

The candidate exposes a private direct/fallback/fault getter solely for a later cache-OFF runtime admission.  It does not make a direct helper route persistent or compatible with any existing cache manifest.

## Build verification

**VERIFIED.** A serial `-O3` build completed.  The parent command reached its 120-second shell limit while compiler children were still live, so the partial state was not used; the child compilation/link completed afterward and `make -q` returned 0.  The produced private files are Wasm-valid and contain the getter export:

```text
boxedwine.js    327,010 bytes  SHA-256 35C3DE289BFA9D580D1A4284B328A8360E5C9E315CAE7558DF49EFBC8FA1B3ED
boxedwine.wasm 3,049,347 bytes SHA-256 3EEF77CC6FEFCC20F16792BD37BCD417C29294052713306C6ACA8F9DA020BAA6
Wasm magic: 00 61 73 6D
export: wasmJitInt9ASpecializedGet
```

## Next gate

Before any cache action, create a strict private page/staging identity which accepts only this stem with `jitCacheUrl=off`, reads the three counters, and rejects every accepted/census/fixture/replay composition.  It must then prove visible real-game cache-OFF render and a nonzero direct count with no unsupported fault/fallback interpretation.  Only after that can a fresh private record, exact-manifest transform, replay render and a fresh primary-display accepted-vs-candidate Present A-B-A(B) be considered.
