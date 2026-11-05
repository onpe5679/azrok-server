# Gate 2C — Acknex x87 outer-loop exact C++ trace-AOT

## Status

- **VERIFIED static:** the implementation covers the measured first-entry
  interval `[0x1004AA80,0x1004ABE7)` and internal backedge through
  `0x1004AA77`; it is not a one-iteration subset.
- **VERIFIED static:** the wrapper is a separate production translation unit
  and is not selected from `NormalCPU::run()` yet.
- **VERIFIED dynamic:** the native Test/x64 integration build succeeds and all
  eight differential cases pass bit-exact state/memory comparison.
- **NOT VERIFIED browser:** production dispatch integration and PatHouse A/B
  remain gated and are not enabled by this change.

## Implementation

Files:

- `source/emulation/cpu/normal/hotAotX87Trace.h`
- `source/emulation/cpu/normal/hotAotX87Trace.cpp`
- `source/test/cpu/testHotAOTX87.cpp`

`d3d9WebRunX87OuterLoopTrace` consumes the whole outer loop in one C++ call.
It directly models the measured instruction sequence rather than recursively
dispatching decoded x86 ops. The existing differential fixture's formerly
disabled hook now invokes this wrapper and requires exactly one harness
dispatch on the hot side.

## Exactness boundaries implemented

- **VERIFIED static:** stack operands use `SS.base + ESP + displacement`; CS
  relative EIP is reconstructed from every linear fault point.
- **VERIFIED static:** guest reads and writes remain interleaved in instruction
  order. The helper does not snapshot records or prewalk the link chain.
- **VERIFIED static:** signed nonnegative links are followed without an
  invented bounds or iteration cap. Cycles retain original nontermination.
- **VERIFIED static:** x87 instructions use BoxedWine's existing `FPU`
  operations. This retains the current cached-F64 versus ext80/SoftFloat
  choice, rounding, TOP/tags, status, NaN comparison, and store conversions.
- **VERIFIED static:** ADD/SUB/CMP/TEST update BoxedWine's lazy tuple in
  program order. Normal exit leaves the final count CMP tuple.
- **VERIFIED static:** a distributed byte signature checks entry, both
  absolute operands, and the final backedge before mutation. Its four words
  were re-read from the 368-byte differential fixture.

## Remaining gate

The wrapper remains intentionally unwired from normal dispatch even though all
eight current cases pass bit-exact comparison. The fixture covers flat/segmented SS,
outer counts 1/3, all four config combinations, comparison edge inputs, every
x87 rounding mode, initial depths 0/1/3/6, and one/multiple/out-of-count links.
Fault injection, explicit alias cases, and browser timing remain later gates.

## Native verification

- **VERIFIED:** MSVC Test/x64 integration build completed successfully.
- **VERIFIED:** test index 7, `D3D9Web Hot AOT x87 outer-loop fixture`, passed
  all eight reference-interpreter versus one-call-wrapper cases.
- **VERIFIED:** the surrounding focused runtime-guard, branch, MMU, emitter,
  Stackifier, SSE2, and DSP tests also passed. A later unrelated
  `MemoryAccess32` page fault from expanding the test range is not attributed
  to this fixture.
