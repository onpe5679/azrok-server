# 215 Gate 2c next observed-entry differential fixture

Date: 2026-07-21

## Scope

No browser/game session was started and no production dispatcher was changed.
This work uses document 201's existing PatHouse profile, the exact acknex.dll
Ghidra export, and the native TestCPU differential infrastructure.  It asks
which part of the actually observed `FUN_1004a6d0` entry can be specialized
without repeating document 212's mistake of assuming that an internal address
is visible to the hot-AOT hook.

## VERIFIED -- whole-function call boundaries

`FUN_1004a6d0` is `[0x1004A6D0,0x1004AC29)` (0x559 bytes, 396
instructions).  It contains direct calls at `A7C8`, `A7E0`, `A930`, `A964`,
and `ABFA`, and COM Lock/Unlock calls at `A78D/A798` and `A943/AC0F`.
Lock publishes a guest pointer used by later writes.  A helper cannot call one
of these and then return `false`: replaying the guest instruction would repeat
an externally visible side effect.

`FUN_1008df5d` is `[0x1008DF5D,0x1008E0E1)` (0x184 bytes, 129
instructions).  After its null guard it makes three unconditional COM calls at
`8DF8A`, `8DFA7`, and `8DFBC`, then zero or more DrawIndexedPrimitive calls at
`8E046`, `8E097`, and `8E0CB`.  Whole-function replacement would have to
preserve exact call order, arguments, HRESULTs, and fault points, so it is not
the first safe helper target.  A future fixture may use guest COM stubs as a
call-skeleton oracle, but that would prove only the stub boundary, not
equivalence with real COM callees.

## VERIFIED -- exact `A8D0..A906` copy loop

The selected first test-only candidate is the exact 54-byte loop
`[0x1004A8D0,0x1004A906)`:

- EAX is the current record index; ESI and EDI are source/destination.
- Each iteration performs six ordered dword read/write pairs at offsets
  `0..0x14`, not a semantic `memcpy`.
- It then reloads `EBX=[0x102FF4CC]`, increments EAX, EDI and ESI (record
  stride 0x2c), executes `CMP EAX,[EBX+0x28]`, and takes signed `JL`.
- Therefore source/destination overlap and writes that alias the root pointer
  or count are observable.  Hoisting the count, loading all six dwords before
  writing, or substituting `memcpy` would be incorrect.

The new test-only fixture is:

- `source/test/cpu/testHotAOTCopyLoop.cpp`
- `source/test/cpu/testHotAOTCopyLoop.h`

It relocates the exact 54 acknex bytes for the interpreter oracle and compares
them with a one-dispatch C++ helper.  The snapshot covers all nine BoxedWine
register slots, raw flags and the full lazy tuple, normalized EIP, x87 status/
TOP, MXCSR, all XMM registers, the root page, and 64 KiB of data memory.

Seven passing success cases cover one and many records, a resumed nonzero index,
`src==dst`, four-byte forward overlap, an ordered write changing
`[root+0x28]`, and an ordered write changing the root global itself.  The last
two directly enforce reload-per-iteration semantics.  A separate corrupted-
byte case verifies that the guard rejects before changing registers, flags,
EIP, `nextOp`, or guest memory.

```text
BoxedWine.exe 0 1 1
Test D3D9Web Hot AOT Copy Loop Fixture ... OK
0 tests FAILED

BoxedWine.exe 0 12 1
all twelve focused branch/copy/WASM/SSE/x87/audio tests ... OK
0 tests FAILED
```

MSVC Test/x64 compiled with zero warnings and zero errors.  The first build
attempt exposed an existing `/MP` shared-PDB collision; the verified command
uses one MSBuild node plus `MultiProcessorCompilation=false`.

## Production helper contract

The eventual production helper should be a separate optional function and
must not use a bulk copy.  Its entry guard must bind the Acknex address space,
exact EIP, immutable bytes across all 54 bytes, and the current decoded-code
identity.  It must preflight and revalidate every resident source/destination,
root, and count page before the first write.

Returning `false` is legal only before the first architectural or memory
change.  After the first write the helper must complete with the original
ordered accesses or raise the same guest fault at the same instruction; it may
not fall back and replay the loop.  It must reread `0x102FF4CC` and
`[root+0x28]` every iteration, preserve u32 wrap, set the final `FLAGS_CMP32`
tuple, set EIP to `A906`, and refresh `nextOp`.

The current top-level hook sees `FUN_1004a6d0`, but document 212 showed that it
does not necessarily see internal loop entries.  Production integration must
therefore either (a) prove `A8D0` is a dispatcher-visible entry, or (b) enter
through `A6D0` and use a resumable, call-boundary-safe state machine.  Do not
install an unconditional `A8D0` check on static reasoning alone.

## Comparison with `A836` and `FUN_1008df5d`

`[0x1004A836,0x1004A8C2)` is the second candidate.  It performs six x87
lerps per 0x2c-byte record and likely offers more arithmetic savings, but its
fixture must preserve x87 control/status, extended intermediates, rounding,
NaNs/denormals, ordered writes, source/destination aliasing, and final CMP.
The proven copy fixture is the smaller correctness gate before that work.

For `FUN_1008df5d`, only the read-only table lookup
`[0x1008DFF4,0x1008E006)` and material run scanning from `0x1008E05E` are
plausible pure kernels.  A scanner may return the next index/run boundary, but
must stop before a DrawIndexedPrimitive boundary.  Whether either internal
address is visible to the current dispatcher is **NOT VERIFIED**.

## Status

- **VERIFIED native dynamic:** exact `A8D0..A906` bytes and seven complete
  differential cases pass; the helper consumes a multi-record loop in one
  harness dispatch.
- **VERIFIED static:** the function and COM/direct-call boundaries above.
- **NOT VERIFIED production:** no runtime dispatcher change was made.
- **NOT VERIFIED browser:** no entry marker, rendering, or FPS claim is made.
