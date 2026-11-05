# 209 Gate 2c runtime-WASM CPU-state correctness and call cost

Date: 2026-07-21

## Scope

This is an isolated Emscripten Node pthread probe for the extended
`wasmRuntimeEmitCpuBlockModule` path. It does not start Azrok, modify
`NormalCPU`, or measure browser FPS. Its purpose is to verify the complete
compact CPU exchange record and directly measure the current worker-local
call boundary before game-loop integration.

## VERIFIED -- GPR, lazy tuple, and EIP are bit-exact

`tools/wasmRuntimeCpuStatePerfProbe.cpp` emits one 341-byte module containing:

1. `ADD EAX, 0x9e3779b9`
2. `XOR ECX, EAX`
3. `SUB EDX, ECX`
4. `CMP EDX, 0x13579bdf`

The probe compares the generated module against a separate C++ reference for
64 independent initial states. Every one of the 13 32-bit words is compared:
eight GPRs, `lazyDst`, `lazySrc`, `lazyResult`, `lazyType`, and `nextEip`.
The non-writing CMP leaves EDX intact while publishing its exact lazy tuple.
All 64 cases pass bit-for-bit. A subsequent one-million-call accumulated state
also matches the C++ reference bit-for-bit.

The same module ID and identical bytes produce install return values `1` then
`0`, directly verifying a cold install followed by a worker-local cache hit.

## VERIFIED -- direct call boundary cost

Build configuration matches the important worker and memory constraints of
the browser artifact while remaining an isolated Node probe:

```text
em++.exe wasmRuntimeEmitter.cpp wasmRuntimeCpuStatePerfProbe.cpp -O2 -pthread
  -sPROXY_TO_PTHREAD=1 -sPTHREAD_POOL_SIZE=1
  -sINITIAL_MEMORY=1073741824 -sALLOW_MEMORY_GROWTH=0
  -sENVIRONMENT=node -sEXIT_RUNTIME=1
  -o wasmRuntimeCpuStatePerfProbe.perf209.js
```

After 10,000 warm-up calls, five fresh-process measurements of 1,000,000
calls were:

| Run | total ms | ns/call |
|---:|---:|---:|
| 1 | 43.178 | 43.178 |
| 2 | 38.906 | 38.906 |
| 3 | 45.052 | 45.052 |
| 4 | 45.663 | 45.663 |
| 5 | 42.806 | 42.806 |
| Mean | 43.121 | 43.121 |
| Median | 43.178 | 43.178 |

Each timed iteration calls the public hot API `wasmRuntimeRunModule`. Thus the
measured scope includes the Emscripten WASM-to-JS `EM_JS` boundary, worker-local
Map lookup plus delete/set LRU refresh, the generated WASM export call, twelve
state-word loads, four operations, twelve state-word stores, and the EIP
store. It excludes module-byte copying and compilation because those belong
to the cold install path.

This result shows that the current per-block worker-local dispatch is in the
tens-of-nanoseconds range in this Node/V8 configuration. It does not establish
a browser value and must not be converted into an FPS prediction.

## Artifacts

- Source: `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/tools/wasmRuntimeCpuStatePerfProbe.cpp`
- JS: `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/tools/wasmRuntimeCpuStatePerfProbe.perf209.js`
- WASM: `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/tools/wasmRuntimeCpuStatePerfProbe.perf209.wasm`

## NOT VERIFIED

- The runtime-generated backend is still not connected to `NormalCPU::run`.
- The probe contains no guest-memory operands, direct branches, x87, or SIMD.
- It does not measure compile latency, browser-worker scheduling, end-to-end
  frame time, rendering correctness, audio, or PatHouse FPS.
- The 65 FPS goal remains unmet.

