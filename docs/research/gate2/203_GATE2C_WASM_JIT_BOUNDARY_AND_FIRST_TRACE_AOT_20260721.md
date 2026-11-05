# 203 Gate 2c WASM JIT boundary and first trace-AOT

Date: 2026-07-21

## Scope

This gate starts from document 201's existing CPU measurement rather than
repeating a broad profile. The first implementation target is the measured
pure-SSE `acknex.dll` function `FUN_101041d7`; the architectural target is a
reusable BoxedWine x86-to-WASM hot-block compiler.

## VERIFIED -- native JIT commit cannot be reused in WebAssembly

- BoxedWine already provides reusable x86 decode, `DecodedOp` chaining,
  address-indexed decoded-op caching, jump indirection, dynamic-code detection,
  and code-page invalidation.
- Native AsmJit commits executable host bytes into data memory and publishes
  host pointers through `DecodedOp::pfnJitCode`. WebAssembly data memory is not
  executable, so that commit backend is unusable in a browser.
- The current pthread artifact imports fixed 1 GiB shared memory and exports a
  fixed `4972/4972` function table. It cannot grow without relinking.
- Each worker has a worker-local WebAssembly table while `DecodedOpCache` is in
  shared linear memory. A generated worker-local function/table slot therefore
  must not be stored in shared `DecodedOp::pfn` or `pfnJitCode`.
- Old `srcgen.cpp` refers to deleted `Op`/`Block` APIs and is not buildable for
  the current decoder.

## VERIFIED -- reusable boundary

The reusable runtime needs a CPU/worker-local `eip -> compiled block` cache,
the current `DecodedOp` decoder, and interpreter side exits before unsupported
instructions. Code writes/unmaps must invalidate via epoch/hash; dynamic-code
pages are fallback in the first version; cache size is bounded by LRU.

The first runtime-generated module may be called once per block through a
worker-local JS map. Document 205 verifies that a split install/run API can
keep the exported function in that map and make hot calls without recopying
module bytes, so table growth is an optional later call-overhead optimization,
not an MVP prerequisite. Arbitrary CFG can initially use a `loop` dispatcher; reducible
regions can later be stackified into structured `if`/`loop` regions.

## VERIFIED -- first trace-AOT target

`FUN_101041d7` is 204 bytes / 66 x86 instructions, including 42 SSE
instructions, no x87, no call, and no indirect branch. Its ABI is:

```c
void __stdcall transform3x3(
    float out_xyz[3],
    const float in_xyz[3],
    const float matrix_rows[3][4]);
```

It computes `(in.x*M0 + in.y*M1) + in.z*M2`, without translation. Its exact
function-byte SHA-256 is
`fa1864c7e65ec472bcfcaad7c06ae2373122f6f1c7e5a84f04519d4164b3aba7`.
The two direct callers are at `0x10102AEB` and `0x10103863`.

`BOXEDWINE_D3D9WEB_HOT_AOT` is guarded by address and distributed byte
signatures. It snapshots the original 48-byte matrix read footprint in the
original row order, preserves alias behavior, uses explicit f32 rounding
points, restores EAX/ECX/lazy TEST flags/XMM state, and applies exact
stack-segment-aware `RET 0x0c` behavior. Non-default MXCSR or signature mismatch
falls through to the interpreter.

## VERIFIED -- next measured trace

The higher-leverage `0x1004AA77..0x1004ABE7` loop is 111 instructions with 85
memory instructions and 29 x87 instructions. It has no call/ret and needs only
16 mnemonics. Its x87 values are popped before exit, making it the next safe
side-exit trace after the SSE proof.

## VERIFIED -- reusable stackified scalar backend

`wasmJitStackified.cpp` is the first game-address-independent concrete backend
behind the worker-local `WasmJitCodeGenerator` interface. Its deliberately
non-faulting subset is 32-bit register/immediate `MOV`, `ADD`, `SUB`, `XOR`,
`CMP`, `TEST`, plus 32-bit `LEA`. It copies only immutable decoded scalar
fields and never retains a `DecodedOp` pointer. An immutable guest-byte
snapshot is checked before commit, closing a recycled-pointer/ABA invalidation
case in addition to the engine's decoded-identity check.

The block loads eight guest GPRs into locals, evaluates the immutable uop list,
and commits GPRs plus the final BoxedWine lazy-flag tuple at block exit. Memory
operands remain side exits because fault ordering needs a separate commit
model. Direct conditional branches remain side exits because they need exact
lazy-flag materialization and two validated successors. The existing cache now
uses an exact per-worker LRU rather than unordered first-entry eviction.

The separate `testWasmJitStackified.cpp` oracle decodes and runs a nine-op
mixed block through both NormalCPU and this backend, compares all GPRs, EFLAGS,
lazy-flag type, and EIP, and verifies that memory MOV and direct Jcc are
rejected. It now also verifies identity-bound unsupported/minimum-length
negative caching, `OP_FLAG_NO_JIT`, compiled-block fallback backoff, LRU
admission for cold/negative entries, and CPU registry cleanup. MSVC x64 Test
reports `OK / 0 failed`; `normalCPU.cpp`, `wasmJitMvp.cpp`, and
`wasmJitStackified.cpp` also compile as Emscripten pthread objects with the
browser build flags.

## VERIFIED -- pre-integration cache/lifecycle hardening

- Cache admission is bounded before creating every entry. Cold and unsupported
  EIPs therefore cannot bypass `maximumBlocks`; eviction is exact worker-local
  LRU for all entry states, not only compiled blocks.
- Unsupported and too-short decisions are negative-cached against the current
  `DecodedOp*` identity. KMemory publishing a replacement identity clears the
  decision. `OP_FLAG_NO_JIT` is rejected before consulting the backend.
- A transactional compiled-block `Fallback` discards the compiled object,
  reacquires the authoritative `cpu->nextOp`/KMemory identity, and applies
  bounded exponential retry backoff. Null compilation uses the same backoff.
- `NormalCPU::~NormalCPU()` calls `wasmJitForgetCpu(this)`, preventing a later
  CPU allocation at the same address from inheriting a stale worker-local
  engine.
- KMemory currently exposes decoded-op invalidation and write-count machinery,
  but no exact monotonically increasing per-code-page epoch. Therefore the
  stackified MVP conservatively compares every captured guest byte on every
  compiled hit. This is correct but costs O(block byte count) per hit; an epoch
  fast path remains deferred until an exact code-generation counter exists.

## INFERRED / NOT VERIFIED

- **INFERRED:** the address-specialized hook is an exactness and entry-overhead
  proof, not by itself reusable across games. Reuse comes from the planned
  `DecodedOp -> generated WASM` compiler.
- **VERIFIED by 204:** browser visual/FPS A/B now covers both adjacent SSE
  functions and the required clean-worker procedure.
- **VERIFIED by 205:** runtime-generated WASM compilation and direct execution
  from a worker-local JS-held instance work with the fixed shared-memory build;
  no table insertion is required for the MVP. NormalCPU integration is pending.
- **NOT VERIFIED:** 65 FPS remains unmet; prior accepted release mean is 26.78
  FPS.
