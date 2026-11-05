# 421 -- Gate 6 INT 0x9A specialized-helper semantic admission (2026-07-26)

## Status

**VERIFIED static admission boundary.  No candidate source, build, cache,
replay, browser run, or FPS result exists.**

420 establishes that Int9A is material and each observed epoch-63 Int9A maps
to one D3D bridge call: `fn8Int9A=21191` equals the six-index bridge-call sum
`0+0+17645+119+3427+0`.  This is coverage only; it does not establish a time
share or a performance effect.

## Current semantics

**VERIFIED:** The Wasm JIT has no Int9A arm: `Jit::dynamic_int9A()` is
unconditionally `emulateSingleOp()` in
`source/emulation/cpu/jit/jitOther.h`.  That path writes current EIP, commits
dirty GP state, invokes `CPU::runNextSingleOp()`, reloads state, invalidates
cached GP/segment state and retains its existing bailout/SMC handling
(`wasm/jitWasmCodeGen.cpp`).  `runNextSingleOp()` reaches NormalCPU Int9A,
which reads the guest-stack index with `peek32(0)`, calls `callD3D9Web`, and
performs normal `NEXT()` EIP advancement (`normal/normal_other.h`).

`callD3D9Web()` additionally reads stack words 1 and 2, performs guest-memory
accesses/dispatch, and may write EAX.  Therefore an inline Wasm replacement
cannot preserve this boundary merely by copying a known index or by skipping
the helper's CPU-state protocol.

## Authorized design boundary

**VERIFIED:** A pure-Wasm D3D replacement is not authorized.  The only
admissible minimum is a private generated Int9A arm that keeps the existing
entry EIP and full eight-GP commit, then invokes a specialized C++ helper.  The
helper must re-decode the current instruction and fast-path only an actual
`Int9A`; all mismatch, fault and exceptional paths must fall back to the exact
existing `runNextSingleOp()` path.

For a fast success, the helper must retain `peek32(0) -> callD3D9Web`, advance
EIP by the re-decoded instruction length, and obtain the successor exactly as
NormalCPU would.  The generated caller must retain post-helper GP/segment
invalidation, FLAGS_NULL handling and the ordinary SMC/bailout arm.  This can
remove only the generic decoded-op copy/function-pointer dispatch portion; it
does not remove D3D bridge, JS dispatch, stack reads, EAX effects or async
completion.

## Required fixture before implementation

**NOT VERIFIED:** No differential fixture exists yet.  It must compare the
new helper with generic `runNextSingleOp()` for: valid index/EAX result;
guest-stack partial/unmapped faults at all three `peek32` words; re-decode
mismatch; SMC/bailout; successor EIP; all eight GP plus segments/flags before
and after; and D3D index partition/async error propagation.  Until that
fixture passes and a private cache-OFF render succeeds, production source,
record/replay and FPS measurement remain forbidden.

The required fixture matrix is now concrete.  Every row must execute identical
guest bytes through control `emulateSingleOp` and candidate generated roots,
then compare EIP, all 8 GP, EFLAGS/lazy state, SS/ESP, `nextOp`, bailout and
persistence state, D3D call log, and candidate fast/fallback counters.

1. Index `0..5`, varied stack words `0..2`, index result/EAX and one exact
   D3D stub call; visible cache-OFF proof separately covers real index 2/3/4/5.
2. Post-compile SMC substitution to non-Int9A: runtime re-decode must yield
   `fast=0/fallback=1` and generic-equivalent state.
3. ESP/SS edge plus unmapped/read-protected `peek32(0..2)` reads: signal,
   handler EIP, GP, next-op and bailout must be control-equivalent.
4. Valid and out-of-range D3D index with EAX and non-EAX sentinel registers.
5. Code-page mutation immediately before/after Int9A in an active JIT block:
   existing SMC arm and bailout check must preserve successor/active-block
   exit exactly.
6. Dirty EAX..EDI, segment bases and non-null lazy flags across the next block:
   the arm must retain existing full invalidation rather than infer EAX-only
   effects from the current D3D body.

**VERIFIED reusable boundaries:** current fallback is
`jitOther.h:141-143`; generic EIP flush/host sync and post-helper invalidation
are in `jitWasmCodeGen.cpp:15013-16,15172-79`; NormalCPU is
`normal_other.h:201-210`; and existing generated-root/fault and seeded-GP test
patterns are in `source/test/cpu/testFPU.cpp:1717-1810` and
`testCPU.cpp:884-1024`.  A private table entry may only be appended at the
established `jitWasmCodeGen.cpp:5847-5904` table; reordering is forbidden.
