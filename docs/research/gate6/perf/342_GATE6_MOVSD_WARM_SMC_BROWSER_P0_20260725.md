# Gate 6 MOVSD warmed SMC browser P0 (2026-07-25)

> **SUPERSEDED in part by 343.** The generated DF0 scalar path was repaired and directly passed the final normal-vs-Wasm differential; DF1 and helper-fallback SMC regressions remain open.

Status: **VERIFIED direct browser differential; candidate fail-closed**

## Measurement boundary

This is not an FPS measurement. The sole existing CDP page was moved, never
duplicated, first to MRGN4 and then to MRGF4 at runtime entry `391`. HTTP
bytes for each rebuilt HTML/JS/Wasm asset matched the disk SHA-256 before
navigation. Both private modules validated and MRGN4/MRGF4/MRGF3 retained the
same 41 public Wasm exports. No accepted asset, cache, replay, or performance
path was changed.

## P0 #1: fixture publication, fixed

**VERIFIED.** The first browser MRGN4 attempt had `root=0` even though its
code bytes were `3EF3A541CD9790`. This was not a DS-prefix failure:
`testNewInstruction()` clears the op cache, `pushCode8()` only writes bytes,
and `KMemory::getDecodedOp()` is a lookup-only API. Replacing root and
successor acquisition with `CPU::getOp(address, 0)` publishes the fresh
decode. Static decoder inspection still proves `3E F3 A5` gives base DS.

The rebuilt MRGN4 browser oracle then passed directly:

```
Movsd SMC MRGN4 oracle regs=10203041/00000000/A55A0102/A55A0103/A55A0104/A55A0105/F0000184/D0000007 flags=000008D7 eip=00000004 next=1364 code=3EF3A540CD9790 source=9097CD40
Movsd SMC MRGN4 NormalCPU oracle ... OK
0 tests FAILED in 0s
```

This proves the expected completed state for one source-to-active-successor
copy: ECX zero, ESI source+4, EDI B5+7, EIP 4 after the replacement `INC EAX`,
and the exact seven-byte mutated code.

## P0 #2: generated SMC bailout skips completed MOVSD state

**VERIFIED.** MRGF4 warmed and entered the generated body (`first JIT block
executed`, direct-chain ABI logged). Its generated checked CodePage write and
the actual taken `emitBailoutCheck()` arm both executed exactly once. The
direct textarea witness after the write was:

```
Movsd SMC MRGF4 post-write fresh=0xe3f380 ecx=00000001 esi=F0000180 edi=D0000003 eip=00000003 active=0 bailout=0 checked=1 taken=1
movsd SMC MRGF4 generated bailout/redecode state
1 tests FAILED in 0s
```

Thus the CodePage write itself succeeded, the active block was invalidated,
the fresh successor exists, and the bailout clears its transient fields and
sets next EIP. But `movsr()` performs its pointer/ECX updates *after* `write()`;
the generic `emitBailoutCheck()` exits immediately after the helper. The
observable result is EIP=B5+3 with pre-copy ECX/ESI/EDI, which skips the
replacement successor while also omitting MOVSD's completed architectural
updates. It differs from the independently measured NormalCPU oracle.

The runtime-zero MOVSD optimization is therefore **not publishable**. MRG2,
MOVSB, cache/replay, and FPS work remain blocked. The next implementation must
make a checked-write-to-nonfast destination take exact emulation before the
inline MOVSR body, or defer the bailout until that body commits ESI/EDI/ECX;
it must then repeat the same MRGN4/MRGF4 browser differential with the
generated-path witness appropriate to the selected safe route.
