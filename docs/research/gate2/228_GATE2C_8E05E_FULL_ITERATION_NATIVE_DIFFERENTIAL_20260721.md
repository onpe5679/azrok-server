# 228 Gate 2c 8E05E full one-iteration native differential

Date: 2026-07-21

## Scope

This extends document 226's A+B fixture to document 225's largest bounded
call-free unit: one iteration beginning at `0x1008E05E`, following every
call-free successor through the existing latch, or stopping immediately
before the indirect draw setup. It is a test-only relocated-interpreter oracle.
Production dispatch and browser assets are unchanged, and no browser session
was opened.

## VERIFIED -- three exact path families

The fixture installs the exact bytes for A, B, C, E, and the latch at both the
original and relocated addresses. It also installs the first excluded call-
setup bytes at `0x8E076` so the pre-PUSH successor is unambiguous.

The test-only fused helper covers:

1. **A+B+latch:** equal material ID increments `[SS:EBP+8]`, then increments
   EDI and selects either `0x8E05E` or `0x8E0A9` from
   `[DS:ESI+0x264]`;
2. **A+C+E+latch:** mismatch with unsigned `counter <= EBX` resets
   `[SS:EBP+8]=EBX`, then executes the same latch and either successor;
3. **A+C pre-PUSH:** mismatch with unsigned `counter > EBX` stops at
   `0x8E076` with no write and the exact `CMP32(counter,EBX)` tuple, before
   any stack mutation, GPR setup, or indirect call.

NormalCPU reaches these results through the exact decoded block sequence. The
helper shadows all selected reads and at most one write, then commits the guest
dword before final EDI/flags/EIP state. No production helper is connected.

## VERIFIED -- counter relations and latch successors

Eight fused cases pass in addition to document 226's five A+B cases:

- equal with latch taken;
- equal with latch fallthrough;
- equal counter wrap from `0xFFFFFFFF` to zero;
- mismatch with `counter < EBX`, reset, latch taken;
- mismatch with `counter == EBX`, reset, latch fallthrough, under independent
  nonzero DS/SS/CS bases;
- mismatch with `counter > EBX`, pre-PUSH side exit at `0x8E076`;
- equal write target exactly aliasing the later latch-count dword;
- reset write target exactly aliasing the later latch-count dword.

Thus `<`, `==`, and `>` around block C, both latch successors after writes,
and the call-boundary exit are directly interpreter-verified.

## VERIFIED -- write forwarding

Architecturally, B or E writes `[SS:EBP+8]` before the latch reads
`[DS:ESI+0x264]`. The helper's buffered read applies byte forwarding from the
pending dword into the latch-count value before selecting the latch successor.

The two exact-alias cases force the forwarding to affect control flow:

- equal changes the aliased count from 2 to 3 before testing `newEDI=1`;
- reset changes the aliased count from 1 to EBX=3 before testing `newEDI=3`.

Both full CPU/FPU/SIMD and 16 KiB memory snapshots match NormalCPU. Reading the
old count or publishing the write after the latch would select a different
successor and fail the fixture.

## VERIFIED -- state and memory comparison

Every fused path compares:

- all nine BoxedWine register slots;
- raw flags, complete lazy tuple, `oldCF`, and normalized EIP;
- DS, SS, CS and the remaining segment bases;
- complete x87 state, MXCSR, and all XMM registers;
- all 16 KiB of fixture data, including the buffered write and sentinels.

The equal path leaves final latch `CMP32` while preserving carry through B's
INC and the latch INC. The reset path preserves block C's carry into the latch
INC. The pre-PUSH path retains block C's tuple and leaves EDI and guest memory
unchanged.

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

## Status

- **VERIFIED native dynamic/static:** all three call-free path families,
  counter relations, both latch successors, and exact-alias forwarding are
  state- and memory-exact.
- **NOT VERIFIED live branch mix:** document 226 already proves retained
  counters cannot recover it; no new browser instrumentation was used.
- **NOT VERIFIED production:** a reusable write tier still needs permission,
  COW, remap/identity revalidation, cross-page writes, and fail-closed fault
  coverage before this test-only algorithm can enter dispatch.

