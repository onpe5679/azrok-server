# 616 — Current browser threading and regional-AOT direction

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED provenance:** the deployed emulator still uses the GitHub
  BoxedWine `BOXEDWINE_WASM_JIT` architecture: x86 decoded blocks are emitted
  as WebAssembly, installed into `wasmTable`, and reached through
  `DecodedOp::pfnJitCode`.
- **VERIFIED boundary:** it is not an unmodified upstream binary. The local
  Wasm-JIT directory differs materially from upstream master
  `2473488cfcf1ba914daf5aad097da0c59bb16073`, and adds the grouped-cache,
  publication, broker, D3D9Web, IME/touch and diagnostic contracts used here.
- **VERIFIED threading:** every guest Wine `KThread` already owns one `CPU*`
  and runs on an Emscripten pthread/Web Worker. The Touch2 build uses
  `-pthread`, a 32-Worker pool and `PROXY_TO_PTHREAD=1`.
- **VERIFIED rendering overlap:** the guest CPU Worker submits Present batches
  through the existing three-slot shared ring. `MAIN_THREAD_ASYNC_EM_ASM`
  executes the page-owned WebGL2 `dispatchBatch()` concurrently on the browser
  main thread. `OFFSCREENCANVAS_SUPPORT` remains 0.
- **VERIFIED limitation:** adding more idle Workers does not divide one Acknex
  main x86 instruction stream. Its EIP, GP registers, flags, segments, x87,
  memory faults, syscalls, signals and `nextOp` are sequential state in one
  `CPU*`.
- **INFERRED rejection:** arbitrary multi-Worker execution of that one stream
  would require dependency/alias tracking, fault-order preservation,
  checkpoints, conflict detection and rollback. That is a speculative
  thread-level execution engine, not a scheduler flag, and is not the next
  practical performance gate.
- **INFERRED direction:** use spare Workers for compile/optimization work while
  keeping execution sequential, then execute fewer, larger, guard-free
  structured Wasm regions. This is the best current combination of steady-FPS
  potential and reuse across other 32-bit Wine games.

## Upstream versus local fork

The following core contract remains upstream BoxedWine design:

```text
x86 DecodedOp basic block
  -> JitWasmCodeGen / WasmEmitter
  -> WebAssembly module export
  -> wasmTable slot
  -> DecodedOp::pfnJitCode
```

The local checkout's `include/boxedwine.h` definition of
`BOXEDWINE_WASM_JIT` is byte-identical to the inspected upstream revision.
The core header also describes building x86 basic blocks into Wasm modules and
executing them from the table.

However, `jitWasmCodeGen`, `wasmEmitter` and `wasmModuleMerger` have substantial
local changes, while `wasmPgoQuiesce` and `source/opengl/d3d9web.cpp` are local
additions. The upstream comparison found approximately +4,294 / -501 lines in
the Wasm-JIT folder. Therefore the accurate short answer is:

> The JIT foundation is the original GitHub BoxedWine JIT, but the current
> deployed runtime is a heavily extended local fork, not pristine upstream.

## Current Worker topology

The current execution path is:

```text
browser page / WebGL2 renderer
          ^
          | MAIN_THREAD_ASYNC_EM_ASM, 3-slot shared Present ring
          |
proxied BoxedWine main pthread
          |
Wine KThread A -> CPU* A -> Web Worker A
Wine KThread B -> CPU* B -> Web Worker B
...
```

`scheduleThread()` starts a native platform thread for each guest KThread;
the Emscripten platform implementation maps it to `pthread_create()`. Each
thread then loops in its own `cpu->run()` until termination. The 44 worker CDP
targets seen in a browser census include the 32 preallocated pool, proxied main
and active/idle workers; they are not 44 simultaneously busy guest CPUs.

The renderer is already a separate concurrent side. Past accepted evidence
measured approximately 20.05 ms/frame on the game Worker and 11.72 ms/frame on
renderer-main, with a Present wait near 1 ms/frame in one window. Eliminating
that wait entirely would be only about a 3% ceiling at 30 FPS. This is why
moving the same renderer to another Worker is more likely to improve jitter
than to create the required steady-FPS jump.

## What spare Workers can still do

### Good uses

- compile and optimize future regions in the background;
- prepare immutable AOT region packs before gameplay;
- execute genuinely separate guest KThreads;
- run a renderer only if later evidence shows browser-main became the critical
  path;
- execute a large data-parallel kernel only after non-overlapping iteration
  semantics are proved.

### Not automatic gains

- increasing `PTHREAD_POOL_SIZE` when the game creates no additional busy
  thread;
- splitting arbitrary instructions from one `CPU*` between Workers;
- moving WebGL after async overlap has already hidden most renderer time;
- compile Workers as a steady-state FPS claim when all hot code is already in
  the immutable replay cache.

## Why the next JIT is structurally different

The prior attempts kept generated functions separate and paid checks at their
edges:

- exact PIC-thunk internal clones: small positive, about +3.15%;
- broad `NtCurrentTeb` region: neutral;
- selective `NtCurrentTeb` region: negative and rejected.

The next candidate does not add another guarded edge. It extends the existing
single-function structured-loop emitter so multiple laminar backward loops in
one generated Wasm body share one 64-backedge budget. Normal loop edges become
local `br` operations; GP/flags/memory semantics remain the original emitted
instructions, and only budget/bailout/side exits return to the dispatcher.

The current owner census directly identified the missed surface:

```text
Wine hash loop backedge       439,255 / 20.008940 s
Wine extension loop backedge  407,129 / 20.008940 s
total                         846,384
                              1,796.99 / Present
                              4.1812% of owner generated entries
```

This alone is not expected to be a revolutionary gain; it is the smallest
safe proof that a real guard-free structured-region direction works. The same
audit found the whole `hash_short_file_name` family at 9.4075% of entries and
the broader directory/name family at 16.7798%, so repeated-input or
cross-handle processed-name caching remains the larger follow-up if a content
fingerprint census proves reuse.

## Parallel renderer track

Document 615 proved a real renderer batching density: 170 draws/Present, with
89 state-filter candidates in 13 groups and a theoretical 170 -> 94 call
surface. Actual Edge exposes `WEBGL_multi_draw`. No call was adopted because
non-adjacent order independence, alpha-test distribution and depth ties remain
unproved. This track stays parallel to regional AOT rather than being confused
with “more CPU workers”.

## Next gate

1. Finish the opt-in multi-laminar structured-loop fixture with shared budget,
   nested/disjoint/crossing, SMC, fault and flags coverage.
2. Prove macro-off/default byte identity.
3. Produce an immutable candidate record/replay cache and verify that the two
   hot loops are local structured branches.
4. Run fresh actual-PatHouse A-B-A; do not infer FPS from entry-count removal.
5. Independently collect content fingerprints at the two exact
   `hash_short_file_name` callers before implementing a filename-result cache.
