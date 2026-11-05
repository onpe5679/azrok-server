# 208 Gate 2c runtime WASM CPU state and stackified lowering

Date: 2026-07-21

## Scope

This extends document 205's generated-module proof without connecting an
unmeasured opcode subset to `NormalCPU::run`. The goal is to replace the
eight-GPR demonstration ABI with a production-shaped transactional state
exchange and lower the tested scalar Stackified subset into generated WASM.

## VERIFIED -- explicit CPU exchange record

`WasmRuntimeCpuState` is a POD record in Emscripten linear memory containing
eight 32-bit GPRs, BoxedWine's lazy `dst/src/result/LazyFlagType` tuple, and
the selected next guest EIP. The module snapshots these into WASM locals,
evaluates the non-faulting block, and commits only at the end. ADD/SUB/XOR
retain the original destination/source/result tuple; CMP/TEST update only the
tuple and do not overwrite their destination.

## VERIFIED -- real worker execution

The 1 GiB shared-memory `PROXY_TO_PTHREAD` Node probe executes a generated
CPU-state module containing MOV, ADD, CMP, XOR, and TEST. It checks affected
GPRs, the final lazy tuple, non-writing CMP/TEST behavior, and EIP bit-for-bit:

```text
runtime wasm emitter probe OK bytes=234 cpu_bytes=338
```

## VERIFIED -- reusable runtime Stackified generator

`wasmJitRuntimeStackified.cpp` lowers game-independent register/immediate
MOV/ADD/SUB/XOR/CMP/TEST blocks. Each compiled block keeps immutable guest and
module bytes, verifies the full source byte range, exchanges state through the
POD record, and reacquires `nextOp` after successful commit. Module IDs are
only hints; the worker cache compares complete module bytes. Eviction triggers
one reinstall of the immutable module before fallback.

A subsequent static audit found and fixed four integration hazards before
production selection: live blocks now use their distinct wasm32 owner pointer
instead of a collidable 32-bit content hash; source identity and all bytes are
checked before/after compilation and again after WASM execution but before
guest-state commit; the C++ and worker module caches are both capped at 256;
and non-pthread builds add the block op count to the cooperative scheduler's
instruction counter. The generated module still writes only its shadow record
until these post-execution guards pass.

The native integration build and focused tests pass:

```text
Test WASM Branch Tier ... OK
Test WASM Memory Tier ... OK
Test Runtime WASM Emitter ... OK
Test WASM JIT Stackified Register Block ... OK
Test D3D9Web Hot AOT Transform3x3 ... OK
Test D3D9Web Hot AOT TransformCoord ... OK
Test D3D9Web Hot AOT X87 Outer Loop Fixture ... OK
Test DSP Audio Write Math ... OK
0 tests FAILED
```

## Boundary / NOT VERIFIED

The measured top PatHouse candidates had zero hits for this register-only
subset, so enabling it now would add lookup cost without an FPS claim.
`createWasmJitRuntimeStackifiedGenerator()` is not selected by
`NormalCPU::run`; memory operands, generated branches, x87, and SIMD are not
yet emitted. The validated MMU, branch, SIMD, and x87 pieces must be connected
before browser A/B. The 65 FPS goal remains unmet.
