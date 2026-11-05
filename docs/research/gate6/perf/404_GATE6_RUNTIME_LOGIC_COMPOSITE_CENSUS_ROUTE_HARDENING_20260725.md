# 404 - Gate 6 runtime lazy logical-composite census route hardening (2026-07-25)

## Scope

This is the private, cache-OFF coverage diagnostic authorized by 402. It does not change a condition predicate and it is not an inline candidate, cache, replay, or FPS result.

## Static route evidence (VERIFIED)

The private target is `azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeRuntimeLogicCompositeCensus`, with isolated build directory `Build/AzrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeRuntimeLogicCompositeCensus1`, macro `BOXEDWINE_WASM_JIT_RUNTIME_LOGIC_COMPOSITE_CENSUS`, and runtime stem `boxedwine.upstreamjit64fn6inlineabi2logiccompositecensus1`.

The module exports an ABI-1 snapshot whose fixed layout is 5,184 bytes / 648 `U64`: six condition rows of 53 current lazy-flag-type counts, 53 CFOF predecessor-type counts, and two potential logical-width counts. The page requires the exact private stem, `runtimeLogicCompositeCensus=1`, and `jitCacheUrl=off`; it verifies all three exports, `_malloc`, `_free`, ABI 1, and the exact byte count. Its reader rejects a nonzero invalid-type bucket, requires each CFOF-predecessor partition to equal the current CFOF bucket, and independently recomputes b8/b32 potential counts from their permitted logical runtime types.

Two static/dynamic route defects were repaired before any browser use:

1. The private build directory is now a prerequisite consumer of `boxedwine-wasm-jit-module-broker.js`, preventing a broker edit from leaving a stale private sidecar.
2. A central page gate rejects more than one private diagnostic URL mode, and every existing census/parity peer validator now lists `runtimeLogicCompositeCensus` as forbidden. The C++ macro has a matching compile-time isolation gate against the other production diagnostics.

The page's executable inline modules parse successfully with Node `vm.SourceTextModule` (five modules); this parsing did not execute the page.

## Build-link observation (VERIFIED / unresolved)

A fresh low-priority `-j31` build compiled the changed `jitWasmCodeGen.cpp` object (1,849,923 bytes) and reached final Emscripten linking without a source diagnostic. The first link attempt stopped before `emcc.py` ran because Windows returned CreateProcess 206 for the enormous object-list command line. This is a host command-length failure, not evidence of a source or Wasm failure.

The private link rule is therefore narrowed to write only that target's object list to its build-local response file and invokes Emscripten as `em++ @...objects.rsp -o ...`; the response file is 30,739 bytes. The low-priority `-j1` relink with `EM_FORCE_RESPONSE_FILES=1` completed without an error line and emitted a 327,498-byte JS (SHA-256 `5ADCF5B96B672F17AFC27039FE7EA073DCC7E517D51DE582F9CC010ED25A2E15`) and a 3,050,419-byte Wasm (SHA-256 `DC1CE00FEECE50093387AC4247D437F4D3197FF687629E3933454143951BE45B`). Generated JS binds all three required census exports. Only these unique-stem sidecars were copied into `assets_d3d9web`; build-to-served and HTTP-200 byte hashes match exactly. The direct runtime census is recorded separately in 405.

## Decision

**VERIFIED.** The private source/page/make/artifact route is closed. The resulting coverage and its reader-layout P1 repair are recorded separately in 405. Accepted assets remain untouched.
