# 221 Gate 2c 8E0A0 material-latch native differential fixture

Date: 2026-07-21

## Scope

This is a native TestCPU gate only. It does not modify browser assets or a
running game. Document 218 selected the
read-only material-scan latch at `acknex.dll+0x8E0A0` as the first candidate
if the exact browser counter proves it live. Document 219 subsequently proved
that exact entry live. This fixture establishes the interpreter oracle and
transactional state contract required before browser enablement. The fixture
now calls both its independent vector-planner oracle and the allocation-free
production `d3d9WebRunMaterialLatch` helper directly.

## VERIFIED -- exact trace

The exact nine bytes are:

```text
473bbe6402000072b5
SHA-256 7c43a4a20e3cb248a25fbfc4dee85d6d4d54d046aa0fbdaaddd475575777e7b7
```

They decode as:

```asm
1008E0A0  INC EDI
1008E0A1  CMP EDI,dword ptr [ESI+264h]
1008E0A7  JC  1008E05E
           ; otherwise 1008E0A9
```

`INC` preserves the incoming carry in BoxedWine's `oldCF`, increments EDI
modulo 32 bits, and temporarily owns an `INC32` lazy tuple. The following
`CMP` replaces `dst/src/result/lazyFlagType` with the exact `CMP32` tuple while
leaving `oldCF` as the pre-INC carry. `JC` selects `0x1008E05E` exactly when
the incremented EDI is unsigned-less than the resident count.

## VERIFIED -- transactional read contract

The test-only helper performs the `[DS:ESI+0x264]` read-only soft-MMU plan and
validation before changing any CPU state. Effective-address or segment-base
wrap, an unmapped page, a stale plan, or a failed read returns `false` at the
original EIP with EDI, flags, FPU/SIMD state, `nextOp`, and resident memory
unchanged. Only a validated shadow value permits the ordered INC/CMP/EIP
commit.

The production helper reuses this contract and commit order through the
allocation-free `wasmMemoryTryRead32` primitive rather than the fixture's
allocating `std::vector` API.

## VERIFIED -- differential coverage

New test-only files:

- `source/test/cpu/testHotAOTMaterialLatch.cpp`
- `source/test/cpu/testHotAOTMaterialLatch.h`

The same nine bytes are installed at `0x1008E0A0` and at a relocated
interpreter copy `0x1108E0A0`. The helper page also carries the exact three
containing-function anchors required by its fail-closed guard. Because the
taken target is itself one of those anchors, the decoded reference stops at
the successor after one three-instruction NormalCPU basic-block dispatch
rather than overwriting it with a TestEnd marker. Eight resident/control cases
compare both helpers with the decoded interpreter:

1. incoming CF clear, unsigned-taken;
2. incoming CF set, unsigned-taken, proving exact `oldCF` preservation;
3. incremented EDI equal to the count, fallthrough;
4. incremented EDI greater than the count, fallthrough;
5. EDI `0xFFFFFFFF` wrapping to zero, unsigned-taken;
6. equal/fallthrough under a nonzero CS base;
7. a taken read through a nonzero DS base;
8. a fallthrough dword read whose bytes genuinely span two independently
   mapped 4 KiB guest pages.

Two more cases prove no-commit side exits for an unmapped `[ESI+0x264]` read
and for `ESI+0x264` wrapping the 32-bit effective address.

Every comparison covers all nine BoxedWine register slots, raw flags, the
complete lazy tuple and `oldCF`, normalized physical EIP, all six segment
bases, MXCSR, every XMM register, and complete x87
control/status/TOP/tag/cache/register/environment/MMX state. Side exits also
retain the exact `nextOp` pointer and a resident-memory sentinel.

The production signature cache also has a direct memory-identity regression
case. After accepting the hot entry in the TestContext memory, the same CPU
and numeric entry are switched to a separately allocated `KMemory` containing
valid nine-byte entry bytes but deliberately missing the three containing-
function anchors. The helper rejects it without state mutation. This proves
that the cache key includes `KMemory*` rather than reusing an acceptance based
only on the numeric entry.

## Verification

The MSVC Test/x64 target builds successfully. The isolated fixture and the
expanded focused integration set pass:

```text
BoxedWine.exe 0 1 1
Test D3D9Web Hot AOT Material Latch Fixture ... OK
0 tests FAILED

BoxedWine.exe 0 13 1
Test D3D9Web Hot AOT Material Latch Fixture ... OK
Test D3D9Web Hot AOT Branch Read Fixture ... OK
Test D3D9Web Hot AOT Copy Loop Fixture ... OK
Test Runtime WASM JIT Guards ... OK
Test WASM Branch Tier ... OK
Test WASM Memory Tier ... OK
Test Runtime WASM Emitter ... OK
Test WASM JIT Stackified Register Block ... OK
Test D3D9Web Hot AOT Transform3x3 ... OK
Test D3D9Web Hot AOT TransformCoord ... OK
Test D3D9Web Hot AOT X87 Outer Loop Fixture ... OK
Benchmark D3D9Web Hot AOT X87 Outer Loop ... OK
Test DSP Audio Write Math ... OK
0 tests FAILED
```

## Status

- **VERIFIED native dynamic:** both the independent test-only helper and the
  production `d3d9WebRunMaterialLatch` helper pass all requested resident,
  nonzero-DS, cross-page, wrap, carry,
  fallthrough/taken, segmented-CS, and no-commit cases are state-exact against
  current NormalCPU.
- **VERIFIED static:** bytes, successors, read surface, lazy-flag ownership,
  and transactional boundary agree with documents 218 and 220.
- **VERIFIED production helper on native Test/x64:** the allocation-free read,
  complete nine-byte guard, `oldCF`, overflow side exits, and final state
  commit are directly differential-tested.
- **NOT VERIFIED browser:** browser dispatcher enablement, rendering, and FPS
  remain the counter-free release A/B gate.
