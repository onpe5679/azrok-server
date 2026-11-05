# 287. Gate 6 threaded pair publication and fault-safe GP store sinking

## Status

- **VERIFIED static/offline:** register-threaded groups use two consecutive
  worker-table slots per entry: the legacy wrapper slot followed by the typed
  `(cpu, reloc, eax..edi) -> (eax..edi)` slot.
- **VERIFIED static:** initial and lazy installation publish typed first and
  wrapper second. Missing export or partial installation rolls both back.
  Owner and individual retirement purge both slots. Legacy groups retain the
  original one-slot path.
- **VERIFIED offline execution:** one exact terminal sequence containing all
  eight contiguous GP stores removes 56 bytes and carries GP values through a
  typed `return_call`. Seven-store and wrong-base variants retain the original
  dispatcher exit byte-for-byte.
- **VERIFIED fail-closed publication guard:** the typed edge requires a
  nonzero target `DecodedOp`, wrapper token equal to live atomic
  `DecodedOp::pfnJitCode`, a nonzero typed token exactly equal to
  `wrapper+1`, no bailout, no one-byte yield, and depth below 64.
- **VERIFIED fixture fallback:** uninstalled, invalidated, typed-unpublished,
  typed-mismatched, bailout, yield, and depth-limit cases all execute the
  original eight stores, `helpers.fn_6`, and tuple return.
- **PARTIAL C++ build:** Emscripten wasm32+pthreads syntax compilation passes,
  but the complete BoxedWine test executable has not yet been linked and run.
- **NOT VERIFIED browser:** no threaded candidate runtime/cache has been
  deployed. The accepted ABI2 baseline remains the only live browser runtime.

## P0 found and closed before deployment

The first guarded typed tail checked only bailout, yield, and depth. It did not
compare the target relocation publication token with the target's live atomic
`pfnJitCode`. That allowed two stale-entry cases:

1. the source could run before the target had been installed;
2. an invalidated target could retain a stale grouped body until quiescent
   retirement.

The first attempted fix added the publication predicates but forgot one
`i32.and` between the publication predicate and the scheduler predicate.
Binaryen therefore emitted the former as `drop(...)`; the explicit
`uninstalled` fixture caught a real typed call (`fetchDelta=0`) instead of
dispatcher fallback.

After adding the missing conjunction, a freshly generated artifact passed:

```json
{
  "valid": true,
  "fetchCalls": 9,
  "threadedMemoryUnchanged": true,
  "threadedEdi": "0x4427",
  "wrapperEdi": "0x5527",
  "partialFallbackPreserved": true,
  "wrongBaseFallbackPreserved": true,
  "boundaryFallbacksPreserved": ["bailout", "yield", "depth"],
  "publicationFallbacksPreserved": [
    "uninstalled",
    "invalidated",
    "typed-unpublished",
    "typed-mismatched"
  ],
  "sunkTails": 1,
  "sunkBytes": 56
}
```

The independently regenerated proof artifact is:

```text
tools/boxedwine_local/threaded-store-sink-fixture8c-pairv3.zip
tools/boxedwine_local/threaded_store_sink_fixture8c_pairv3_extract
```

## Other direct gates

Loader and export rows:

```json
{"valid":true,"cases":8,"exportedFunctionRows":32}
```

Two-entry multi-result merger:

```json
{
  "valid": true,
  "groups": 1,
  "entries": 2,
  "exportsPerEntry": 2,
  "observed": ["0x2217", "0x3327"]
}
```

Actual C++ emitter/merger output executed by V8:

```json
{"valid":true,"observedEdi":["0x2217","0x3327"]}
```

## Reboot recovery / accepted baseline

The rebooted services were restored without opening another game instance.
The same in-app browser tab reloaded the accepted
`boxedwine.upstreamjit64fn6inlineabi2` runtime and returned through automatic
selection to reference-correct PatHouse.

- **VERIFIED dynamic:** HTTP/runtime/cache/app/root assets returned 200.
- **VERIFIED dynamic:** WebSocket, TCP bridge, and game server connections
  remained established.
- **VERIFIED dynamic:** heartbeat continued every ten seconds with no
  `WS_CLOSED`.
- **VERIFIED dynamic/browser:** walls, carpet, furniture, character, and Korean
  UI remained correct. HUD observations were 44.2 and 48.0 FPS.
- **VERIFIED dynamic:** no D3D/WebGL/OOM/unreachable/runtime exception markers
  and both error logs remained empty.

These numbers are liveness/reference evidence, not a threaded performance
result.

## Next gate

1. Add an explicit Azrok build target enabling
   `BOXEDWINE_WASM_JIT_THREADED_BODY_ABI`.
2. Link and run the C++ pair broker lifecycle test if an allowed build path is
   available.
3. Generate the real PatHouse dual-entry cache from the accepted ABI2 corpus.
4. Load the candidate once, require reference rendering, heartbeat, and zero
   runtime errors, then run adaptive A-B-A against accepted ABI2.

