# 207 Gate 2c runtime-WASM direct branch contract

Date: 2026-07-21

## Scope

This step follows the runtime-generated module proof in 205 and does not repeat
the CPU profile. It establishes the smallest exact direct `Jcc`/`Jmp` tier that
can be added without publishing worker-local WebAssembly identities through
BoxedWine's shared `DecodedOp` cache. Production `NormalCPU::run` and browser
execution are intentionally unchanged.

## VERIFIED (static) -- interpreter branch state transition

`normal_jump.h` and the `NEXT_BRANCH1`/`NEXT_BRANCH2` macros in
`normalCPU.cpp` establish the exact transition from branch-entry EIP `P`:

- direct `Jcc` taken: `EIP = P + imm + len`;
- direct `Jcc` fallthrough: `EIP = P + len`;
- direct `Jmp`: `EIP = P + imm + len`;
- all additions use 32-bit unsigned wraparound.

Taken execution resolves the target through `DecodedOp::data.nextJump`, a
double pointer to the address-indexed decoder-cache slot, and marks a newly
decoded target with `OP_FLAG2_JUMP_TARGET`. Fallthrough uses `op->next`,
decoding it on demand when absent. `DecodedOp::isDirectBranchWithNext()` maps
the `DECODE_BRANCH_1|DECODE_BRANCH_2` form, while `JumpO..JumpNLE` are the
contiguous 16 x86 condition codes.

## VERIFIED (static/code) -- lazy flags must remain lazy

Normal direct Jcc handlers call `CPU::getCF/ZF/SF/OF/PF` (with three optional
fast getter combinations) but do not call `fillFlags()`. A branch therefore
observes the authoritative lazy tuple without changing `lazyFlagType`,
`lazyFlagTypePrev`, `dst`, `src`, `result`, `oldCF`, or materialized `flags`.

The new independent `wasmBranchTier.cpp` mirrors all 16 predicates through
those authoritative getters and computes only the selected successor EIP.
It deliberately does not retain a `DecodedOp*`, mutate EIP, or publish a
worker-local module handle. `testWasmBranchTier.cpp` covers:

- all 16 conditions from a materialized `FLAGS_NONE` state;
- all 16 from overflow-producing lazy `FLAGS_CMP32`;
- all 16 from zero-producing lazy `FLAGS_TEST32`;
- byte-for-byte preservation of the lazy tuple after each observation; and
- backward taken, forward fallthrough, unconditional jump, and 32-bit EIP
  wrap calculations.

The files are registered in the MSVC Test project and `testMain.cpp`. The
integrated test run including entries 0 through 7 passes with zero failures.

## VERIFIED (static) -- minimum transactional commit contract

A generated module must use this order:

1. C++ verifies the current entry EIP, `cpu->nextOp` identity,
   `memory->getDecodedOp(entryEip)` identity, and the complete captured guest
   byte snapshot before entering generated code.
2. The module executes only non-faulting operations into shadow state. An
   entry-dependent condition may be supplied from the authoritative CPU
   getters; a condition produced inside the block may later be lowered from
   the same lazy tuple formulas.
3. The module returns `taken` or the selected guest successor EIP, never a
   `DecodedOp*` or a JS-map handle.
4. Before publishing any shadow state, C++ repeats the entry identity and byte
   checks and requires that the selected successor already has an
   authoritative decoded-cache identity. If any check fails, it discards the
   shadow state and runs the original interpreter from the unchanged entry.
5. On success, C++ commits GPR/lazy state and EIP together, then reacquires the
   selected successor from KMemory. The compiled cache may record that pointer
   only as a non-dereferenced identity token and must revalidate it every hit.

Requiring a predecoded selected successor is conservative but necessary for
this first tier: instruction-fetch/page faults must remain on the interpreter
path, where BoxedWine already applies its exact exception behavior. A later
tier may decode a missing successor before entry, but it must not attempt that
after partially committing a generated block.

## VERIFIED (static) -- self-modifying invalidation boundary

Writes call `DecodedOpCache::remove`, clear the affected address slots, and
queue old operations for delayed deallocation. Branch `nextJump` indirection
then observes the replacement slot automatically. Because there is no precise
monotonic code-page epoch, generated blocks must retain 203's full guest-byte
comparison and source-identity check. Both selected successor address and
identity must be reacquired; embedding either the old `op->next` or
`*op->data.nextJump` pointer in WebAssembly is invalid.

## NOT VERIFIED

- Direct branches are not yet emitted by `wasmRuntimeEmitter.cpp` and are not
  integrated into `WasmJitEngine` or `NormalCPU::run`.
- `Loop*`, `Jcxz`, indirect jumps, calls, returns, and faulting memory
  operations remain side exits.
- Browser PatHouse behavior, FPS, and the 65 FPS target are unaffected by this
  contract-only production change.
