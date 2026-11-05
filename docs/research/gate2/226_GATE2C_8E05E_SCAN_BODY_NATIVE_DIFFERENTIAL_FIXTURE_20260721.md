# 226 Gate 2c 8E05E scan-body native differential fixture

Date: 2026-07-21

## Scope

This is a native TestCPU oracle for the first material-ID scan body at
`acknex.dll+0x8E05E`. It does not modify production dispatch or browser assets
and does not launch another game session. Static instruction boundaries are
shared with the exact function export used by documents 218 and 220.

## VERIFIED -- existing evidence cannot recover successor mix

Document 219's browser observer counted only exact entries `0x8E05E` and
`0x8E0A0`, publishing count 1 and powers of two. Both reached a published
lower bound of 33,554,432, but those censored lower bounds do not preserve the
final counts or distinguish the equal successor at `0x8E06C` from the mismatch
successor at `0x8E071`. The older 16-byte sampled-time buckets likewise contain
neither branch counts nor successor identities.

Therefore the live equal/mismatch ratio is **NOT VERIFIED** from retained
profile/trace material. Recovering it would require new counters, but no
browser was opened for this fixture task.

## VERIFIED -- exact A+B trace

The fixture covers the first split and the equal-path write:

```text
8b86540200008b04b83b450c7505ff4508eb2f
SHA-256 f385bbafc6a673d6aba9f9c7cf740b59b4ec5f1a9ca37da3d0e75d586ee3a379
```

```asm
1008E05E  MOV EAX,[DS:ESI+254h]
1008E064  MOV EAX,[DS:EAX+EDI*4]
1008E067  CMP EAX,[SS:EBP+0Ch]
1008E06A  JNZ 1008E071
1008E06C  INC dword ptr [SS:EBP+8]
1008E06F  JMP 1008E0A0
```

The mismatch path stops at `0x1008E071` with the selected material in EAX,
the exact `FLAGS_CMP32` tuple, and no guest write. The equal path performs the
counter read-modify-write after all three prior reads and the CMP, then stops
at `0x1008E0A0` with the exact `FLAGS_INC32` tuple and `oldCF` inherited from
the equal CMP.

The following mismatch continuation is intentionally outside this first
fixture. Static analysis shows it compares the counter, may reset it and
return to the latch, or may reach an indirect D3D call. A production helper
must side-exit before that call unless a resumable call-boundary contract is
added.

## VERIFIED -- differential cases and write order

New test-only files:

- `source/test/cpu/testHotAOTScanBody.cpp`
- `source/test/cpu/testHotAOTScanBody.h`

The exact bytes are installed at the original and a relocated interpreter
address. NormalCPU executes A in one basic-block dispatch and, for equality,
B in a second dispatch. The test-only helper uses resident read-only MMU plans
for the dependent pointer/material/parameter/counter reads and performs the
single guest write only after all values are shadowed.

Five full-state cases pass:

1. mismatch to `0x8E071`, preserving the CMP tuple and making no write;
2. equality, incrementing a normal counter and reaching `0x8E0A0`;
3. equality with counter `0xFFFFFFFF`, proving modulo wrap and INC32 flags;
4. equality with independent nonzero DS, SS, and CS bases;
5. equality where `[SS:EBP+8]` aliases the selected material array element.

The alias case is the write-order proof: EAX and the CMP inputs observe the
old array value, and only afterward does the counter RMW increment that same
guest dword. A helper that wrote early or reread the aliased source after the
write would diverge from the interpreter snapshot.

Every case compares all nine register slots, raw and lazy integer state,
normalized EIP, all segment bases, complete x87 state, MXCSR, every XMM
register, and the full 16 KiB fixture data region. Snapshot fields are compared
explicitly rather than by raw-struct `memcmp`, avoiding C++ padding as false
evidence.

## Verification

```text
BoxedWine.exe 13 1 1
Test D3D9Web Hot AOT Scan Body Fixture ... OK
0 tests FAILED

BoxedWine.exe 0 14 1
...
Test DSP Audio Write Math ... OK
Test D3D9Web Hot AOT Scan Body Fixture ... OK
0 tests FAILED
```

## Status and remaining gate

- **VERIFIED native dynamic/static:** exact A+B successor and equal-path write
  ordering are state- and memory-exact for the five resident cases.
- **NOT VERIFIED live successor mix:** retained browser/profile artifacts are
  insufficient; no new browser was launched.
- **NOT VERIFIED production write tier:** the test-only helper deliberately
  does not claim fault-safe/COW/read-only guest writes. Production requires a
  transactional write preflight/commit tier, alias forwarding, and explicit
  side exits before the indirect D3D call.

