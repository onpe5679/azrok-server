# 288. Gate 6 threaded loader GP capability fail-closed audit

## Status

- **VERIFIED static / fixed, browser candidate NOT VERIFIED:** the v3
  register-thread loader originally accepted a `threadedGpAbi.storeSinking:true`
  cache after checking only the adjacent-slot pair capability.  It did not
  require the GP-carrying tail capability.
- **VERIFIED static:**
  `wasm_jit_get_threaded_gp_abi_version()` returns zero unless
  `BOXEDWINE_WASM_JIT_THREADED_TAIL_ABI` is defined.  The original
  `azrokMultiThreadedJitAudioO3AsyncRingThreadedBodyAbi` target defined only
  `...THREADED_BODY_ABI` and did not export the GP getter.
- **VERIFIED fail-closed fix:** the source and deployed `boxedwine-shell.js`
  now require both `register_thread_abi_version == 1` and
  `threaded_gp_abi_version == 1` for a typed cache.  Missing GP export is
  treated as zero and rejected before group staging.  The candidate Make target
  now defines the tail ABI and exports its getter.
- **VERIFIED offline:** the loader verifier passes 9 cases, including
  `pair=1/gp=0 -> runtime-gp-abi-mismatch`; the source/deployed shell SHA-256
  values match.  The pair-publication/store-sinking and two-entry multi-result
  fixture verifiers still pass.
- **VERIFIED build / dynamic suite PARTIAL:** a wasm32+pthreads test build
  carrying both ABI macros links, its 2,421,722-byte Wasm validates in V8, and
  the browser suite reaches `Test WASM JIT dual-entry emitter ... OK`.  MT
  broker publication tests remain blocked by the pre-existing worker
  `callHandler` command mismatch (see document 272); that failure is not used
  as a threaded-browser result.

## Rejected deployment shape

Pair publication alone proves only that wrapper and typed table slots are
adjacent and atomically published.  It does not prove that compiled-to-compiled
tails return all eight GP registers or that the corresponding CPU-memory stores
were sunk only at synchronized exits.  A Body-only build would therefore have
accepted a cache whose execution contract it does not advertise.

The loader now rejects this before it records grouped modules, with the reason
`runtime-gp-abi-mismatch`.  Legacy wrapper-only caches remain accepted.

## Remaining gate

Build and stage a new tail-enabled PatHouse runtime, regenerate the actual
dual-entry cache from the accepted corpus, then perform cache-OFF reference
rendering before any fresh replay or A-B-A measurement.  No threaded PatHouse
runtime, cache, screenshot, or FPS result exists yet.
