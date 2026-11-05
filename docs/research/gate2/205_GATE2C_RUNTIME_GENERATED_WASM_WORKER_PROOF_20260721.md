# 205 Gate 2c runtime-generated WASM worker proof

Date: 2026-07-21

## Scope

This step reuses documents 201--204's measured CPU bottleneck and JIT boundary.
It does not repeat profiling and does not integrate an unproven backend into
`NormalCPU::run`. Its single question is whether the fixed Emscripten function
table actually prevents a BoxedWine pthread from generating and executing a
new WebAssembly block at runtime.

## VERIFIED -- a generated module can bypass the fixed function table

`wasmRuntimeEmitter.cpp` now emits a complete WebAssembly MVP binary in C++.
The module:

- imports `env.memory` as the existing fixed shared WebAssembly memory;
- exports `run(i32 statePointer) -> i32`;
- snapshots eight consecutive 32-bit GPR state words into eight WebAssembly
  locals;
- lowers game-independent register-only `MOV`, `ADD`, `SUB`, and `XOR`, with
  register or immediate sources;
- commits all eight locals only after the non-faulting block completes; and
- imports no function table and stores no generated slot in `DecodedOp`.

The runtime bridge constructs `WebAssembly.Module` and
`WebAssembly.Instance` synchronously in the calling worker. It holds the
exported `run` function in a `globalThis` `Map`, which is worker-local under
Emscripten pthreads. The map is capped at 256 entries with exact insertion-
order LRU. Module IDs are only hints: installation compares all module bytes,
so an ID collision cannot execute stale code.

The hot API is split deliberately:

1. `wasmRuntimeInstallModule` copies and validates bytes only on compilation or
   identity replacement.
2. `wasmRuntimeRunModule` performs only the worker-local map lookup and direct
   exported-function call; it does not recopy module bytes.

This proves that the current fixed `4972/4972` Emscripten table is not an MVP
blocker. Table growth remains useful for eliminating the JS map call in a
later tier, but it is no longer required for first runtime-generated code.

## VERIFIED -- deterministic emitter test

`testWasmRuntimeEmitter.cpp` fixes a mixed eight-operation module at 234 bytes
and FNV-1a-64 `9c4957cdded61b43`. It checks repeat emission byte-for-byte,
the WebAssembly preamble, invalid register rejection, inverted memory-limit
rejection, and native executor unavailability.

MSVC x64 Test build:

```text
MSBuild BoxedWine.vcxproj /m /p:Configuration=Test /p:Platform=x64 /p:PlatformToolset=v143
BoxedWine.exe 0 1 1
Test Runtime WASM Emitter ... OK
0 tests FAILED
```

## VERIFIED -- Emscripten pthread execution proof

`tools/wasmRuntimeEmitterProbe.cpp` is linked with the same important runtime
constraints as the browser artifact:

```text
em++.exe wasmRuntimeEmitter.cpp wasmRuntimeEmitterProbe.cpp -O2 -pthread \
  -sPROXY_TO_PTHREAD=1 -sPTHREAD_POOL_SIZE=1 \
  -sINITIAL_MEMORY=1073741824 -sALLOW_MEMORY_GROWTH=0 \
  -sENVIRONMENT=node -sEXIT_RUNTIME=1 \
  -o wasmRuntimeEmitterProbe.worker.js
node wasmRuntimeEmitterProbe.worker.js
runtime wasm emitter probe OK bytes=234
```

The first worker call installs and executes the generated module against the
actual shared linear memory. The probe checks all eight resulting GPR words.
It then installs the same module ID and bytes again, requires the cache-hit
return code, directly executes it a second time, and checks stable overwritten
register results. Thus this is not merely a successful link or module parse.

## Boundary and next integration step

The proof state is a compact eight-word shadow record, not yet the full
`NormalCPU` object. Correct integration must add explicit offsets for GPR,
lazy flags, and EIP (or a compact per-CPU exchange record), and must retain the
existing engine's decoded-identity plus guest-byte invalidation before calling
the installed module. It must not publish worker-local JS handles through the
shared `DecodedOp` cache.

The next reusable tier should lower the already implemented stackified scalar
uops into this emitter, then add lazy flag output and EIP. Memory operands and
branches remain interpreter side exits until fault ordering and successor
identity are represented. Synchronous module compilation also occurs on the
CPU worker; compile latency and direct JS-call overhead must be measured after
correct `WasmJitEngine` integration, not inferred from this proof.

## NOT VERIFIED

- The generated-module backend is not connected to the game execution loop.
- Browser UI execution and PatHouse rendering were intentionally not started
  in this isolated proof; the dynamic result is an Emscripten proxied pthread
  under Node using the same shared-memory WebAssembly APIs.
- Lazy flags, EIP, memory operands, branches, x87, and SIMD code generation are
  not implemented in this emitter yet.
- No FPS claim follows from this proof, and the 65 FPS goal remains unmet.

