# 286. Gate 6 dual-entry register-threaded ABI spike

## Status

> **RESOLVED by 287.** The first store-sinking implementation omitted the live
> target publication check. Document 287 records the corrected two-token guard
> and direct uninstalled/invalidation/typed-token/boundary fallback fixtures.
> Browser deployment remains separately NOT VERIFIED.

- **VERIFIED direction:** the accepted common dispatcher removes most outer
  C++ to Wasm activations, but compiled blocks still use the legacy
  `(cpu, relocBase) -> void` body ABI and synchronize GP state through CPU
  memory. Documents 273, 274, and 281 make this the next broad execution
  candidate rather than another one-helper micro-optimization.
- **VERIFIED V8 ABI spike:** a 126-byte standalone module with
  `execute(cpu, reloc)` and
  `execute_threaded(cpu, reloc, eax, ecx, edx, ebx, esp, ebp, esi, edi)`
  passes `WebAssembly.validate`. The exported arities are 2 and 10, and the
  wrapper forwards `edi=0x1107` exactly to the internal body.
- **PARTIAL implementation:** a workspace-local BoxedWine copy now emits a
  legacy wrapper plus paired threaded body behind
  `BOXEDWINE_WASM_JIT_THREADED_BODY_ABI`. Local indices 0..67 remain unchanged:
  GP locals 2..9 become parameters, while segment/scratch/FPU/SIMD locals keep
  their old indices.
- **VERIFIED static safety correction:** internal entry must set all eight
  `m_gpLoaded=true` and all eight `m_gpDirty=true`. Incoming GP values may be
  newer than CPU memory; a register untouched by the current block must still
  be committed at the next observable helper/fault/terminal boundary.
- **PARTIAL runtime merger:** the local runtime merger accepts either one
  legacy body or an exact two-body pair, exports wrapper `bN` and internal
  `tN`, and rejects mixed shapes and a second function that is not exactly
  ten `i32` parameters returning void.
- **VERIFIED offline pipeline fixture:** two synthetic dual-entry v5 modules
  passed Binaryen optimization, merged into one grouped module, retained two
  wrapper/internal export pairs, emitted the explicit `threadedGpAbi`
  capability, passed `WebAssembly.validate`, and forwarded distinct EDI values
  `0x2207` and `0x3307`.
- **VERIFIED fail-closed pipeline gate:** dual-entry input is rejected when
  legacy direct-call or generic-common-dispatch rewriting is requested. Those
  paths cannot be enabled until the ten-argument threaded-tail rewrite and
  exact success-arm store sinking exist.
- **NOT VERIFIED build/runtime:** reboot left no WSL distribution, and the
  managed filesystem sandbox denies executing the external Emscripten clang.
  Therefore the changed C++ translation units and tests have not yet been
  compiled, and no threaded artifact has been loaded into the game browser.

## Why this is the next large lever

Direct prior evidence:

1. Document 273 measured 322,513.25 compiled-Wasm block activations per
   PatHouse frame before the common dispatcher.
2. Document 274 reduced outer C++ to Wasm activations by 98.4628% and measured
   a robust +20.7996% adjacent FPS median. Boundary reduction therefore
   transfers to browser frame time.
3. The ordinary compiled bodies still lazily load EAX..EDI from `CPU` memory
   and `syncDirtyRegsToHost()` at observable exits. The common dispatcher did
   not create a register-carrying block ABI.
4. Document 281 attributes approximately 16.39 CPU ms/Present to the busiest
   renderer worker and retains broad V8/Wasm execution as the primary lever.
5. The completed parity67 gate in document 285 was inside noise. Another
   isolated flag helper is lower priority than eliminating block-to-block GP
   memory traffic.

## Implemented workspace spike

The original dirty `C:\bwujit` tree was not modified. A tracked-file snapshot
was copied to:

```text
tools/boxedwine_local/bwujit_threaded_abi
```

Changed files in that snapshot:

```text
source/emulation/cpu/wasm/wasmEmitter.h
source/emulation/cpu/wasm/wasmEmitter.cpp
source/emulation/cpu/wasm/jitWasmCodeGen.h
source/emulation/cpu/wasm/jitWasmCodeGen.cpp
source/emulation/cpu/wasm/wasmModuleMerger.cpp
source/test/cpu/testWasmJitBatch.h
source/test/cpu/testWasmJitBatch.cpp
source/test/testMain.cpp
```

The emitter now has an explicit
`beginFunction(funcIdx, locals)` overload. It fail-closes unless code bodies
are emitted in the same order as local-function declarations.

The generator creates:

```text
execute          : (cpu, relocBase) -> void
execute_threaded : (cpu, relocBase, eax..edi) -> void
```

The wrapper loads the eight architectural GP values from CPU memory once and
calls the threaded body. The internal body removes the eight GP local
declarations so that its ten parameters occupy the exact previous local
indices. Existing helper/fault/terminal synchronization remains present.

The runtime merger now:

- accepts one legacy body or one exact wrapper/internal pair;
- parses and validates local function signatures;
- emits functions and code bodies in `[wrapper_i, internal_i]` order;
- exports `bN` for the old ABI and `tN` for the threaded ABI;
- rejects legacy/dual shape mixing.

The offline pipeline now performs the same one-or-two-body shape check. For a
paired input it lays out each group as `[wrapper_i, internal_i]`, exports the
   entry key as the wrapper and `t_<entry-key>` as the internal body, and writes:

```json
{
  "threadedGpAbi": {
    "version": 1,
    "gpCount": 8,
    "wrapperParams": 2,
    "internalParams": 10,
    "internalResults": 8,
    "wrapperExport": "entry-key",
    "internalExportPrefix": "t_",
    "storeSinking": false
  }
}
```

## Direct V8 proof

Command:

```text
node tools/boxedwine_local/verify_dual_entry_wasm_spike.mjs
```

Result:

```json
{"valid":true,"wrapperArity":2,"threadedArity":10,"threadedResults":8,"forwardedEdi":"0x1107","bytes":168}
```

Grouped pipeline fixture result:

```text
Optimized: 2/2
Modules: 2
Groups: 1
Direct calls: 0
WebAssembly.validate: pass
wrapper/internal export arities: 2/10 for both entries
observed tagged values: 0x2217, 0x3327
internal results: 8 x i32
storeSinking: false (loader must reject)
```

The reusable fixture and verifier are:

```text
project/emscripten/make-dual-entry-pipeline-fixture.mjs
project/emscripten/verify-dual-entry-grouped-fixture.mjs
```

## Remaining correctness gates

The current spike is deliberately not deployable yet.

1. **VERIFIED source/V8/offline:** the internal ABI now returns all eight GP
   values. `return_call` can therefore carry them through a chain and only the
   cold wrapper performs the final CPU-memory writeback. This removes the need
   for unsafe post-link deletion of store instructions.
2. **VERIFIED fail-closed loader unit:** five cases cover legacy acceptance,
   incomplete `storeSinking:false` rejection, old-runtime rejection, exact v1
   acceptance, and wrong-arity rejection. A threaded cache additionally
   requires the runtime export `_wasm_jit_get_threaded_gp_abi_version()==1`.
3. **VERIFIED audit fixes, C++ build still NOT VERIFIED:** the emitter now
   records the real export count; `onTestEnd()` returns the GP tuple;
   interpreter-helper GP caches are invalidated before the bailout arm; and
   both online/offline mergers relocate each wrapper's internal call index.
   The offline tagged fixture makes entry 0/1 add distinct 0x10/0x20 tags, so
   a second wrapper accidentally calling the first internal can no longer pass.
4. **PARTIAL source:** the offline rewriter recognizes the exact
   `fetchNextOp; local.get eax..edi; return` terminal form and can replace an
   unguarded exact edge with a typed ten-argument `return_call`. Guarded,
   cyclic, yield-aware, and common-dispatch typed tails remain fail-closed.
5. **NOT VERIFIED build/runtime:** every helper, fault, SMC, yield, bailout,
   termination, publication mismatch, and target mismatch path still needs
   compiled differential proof. Profile builds deliberately retain the legacy
   success-arm synchronization because their profile helper observes CPU state.
6. The JS/C++ worker publication path still needs paired wrapper/internal table
   slots. Until that is complete the runtime capability export returns zero and
   the loader rejects the cache.

```text
threadedGpAbi: version 1, gpCount 8, wrapperParams 2,
internalParams 10, internalResults 8, storeSinking false
```

7. Full CPU differential tests must cover partial 8/16/AH writes, helpers that
   mutate GP state, taken/fallthrough branches, DIV/page fault, SMC,
   signal/re-entry, yield, bailout, and termination.

## Build blocker and next action

`wsl.exe` reports that no Linux distribution is installed. Direct invocation
of the Windows Emscripten driver reaches its external `clang++.exe`, which the
managed sandbox denies executing. No attempt was made to bypass that policy,
and the accepted browser runtime/cache remains untouched.

Once an allowed build surface is available, the immediate gate is:

1. compile and run the new emitter/merger tests;
2. implement paired offline pipeline and loader capability validation;
3. build a correctness-only threaded artifact that retains all stores;
4. only then add exact success-arm store sinking and run accepted A versus
   threaded B using adaptive A-B-A, exact Presents, and renderer worker
   CPU/Present.
