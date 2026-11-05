# 216 Gate 2c 46780 branch/read native differential fixture

Date: 2026-07-21

## Scope

This is a native TestCPU gate only.  It does not modify the production
dispatcher and it does not open a browser or game session.  Document 213
selected the exact acknex.dll trace `[0x10046780,0x1004678C)` after excluding
the AA-region buckets; this document builds its relocated interpreter oracle
and test-only helper.

## VERIFIED -- exact trace and transactional contract

The exact 12 bytes are:

```text
7c2885c9742483790403751e
SHA-256 545cc01e90d77ccc2845d96f804873064f0cf7e39e67e9667c25c6363fe5f05e
```

They decode to `JL 467AA`, `TEST ECX,ECX`, `JZ 467AA`,
`CMP dword [ECX+4],3`, `JNZ 467AA`, with fallthrough `4678C`.

The test-only helper evaluates the incoming signed condition with
`getSF()!=getOF()` and therefore does not materialize or replace the incoming
lazy tuple.  If ECX is zero, it commits the exact `TEST32` tuple.  If a memory
read is needed, it first uses the verified read-only soft-MMU plan from
document 206, reads into a shadow value, revalidates the page identity, and
only then commits the final `CMP32` tuple and successor EIP.  A failed read
plan returns `false` at the original entry with CPU and memory untouched.

## VERIFIED -- differential cases

The new test files are:

- `source/test/cpu/testHotAOTBranchRead.cpp`
- `source/test/cpu/testHotAOTBranchRead.h`

The exact bytes are relocated to a second executable page for the interpreter
oracle.  Taken and fallthrough targets contain TestCPU end markers.  Each
successful case compares all nine BoxedWine register slots, raw flags, the
complete lazy tuple, old carry, normalized physical EIP, x87 TOP/status,
MXCSR, and every XMM register.

Five resident/control cases pass:

1. incoming signed JL taken, with an intentionally unmapped ECX target,
   proving no read and exact preservation of the incoming lazy tuple;
2. ECX zero, producing the `TEST32` tuple and taken successor;
3. resident `[ECX+4] != 3`, producing the `CMP32` tuple and taken successor;
4. resident `[ECX+4] == 3`, producing the `CMP32` tuple and fallthrough;
5. the equal case under a nonzero CS base, proving physical-target relocation.

A sixth case supplies a nonzero ECX whose `[ECX+4]` is unmapped.  The helper
returns side exit before publishing the intermediate TEST tuple.  All GPRs,
raw/lazy flags, EIP, `nextOp`, FPU/SIMD state, and a resident memory sentinel
remain unchanged, allowing the interpreter to reproduce TEST-then-fault
ordering.

## Verification

MSVC Test/x64 builds with zero warnings and errors.  The exact fixture and the
focused integrated set pass:

```text
BoxedWine.exe 0 1 1
Test D3D9Web Hot AOT Branch Read Fixture ... OK
0 tests FAILED

BoxedWine.exe 0 12 1
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

- **VERIFIED native dynamic:** the five-instruction helper is bit/state exact
  for all requested control paths, resident read, segmented CS, and the
  no-commit read-fault side exit.
- **VERIFIED static:** exact bytes, successors, and lazy-flag ownership agree
  with document 213 and the Ghidra export.
- **NOT VERIFIED production/browser:** no dispatcher integration, exact live
  entry count, rendering, or FPS claim is made.  Document 213's entry-counter
  gate still precedes production installation.

