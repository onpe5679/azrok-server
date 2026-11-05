# Gate 6 MOVSD warmed SMC DF0 closure (2026-07-25)

Status: **VERIFIED direct browser DF0 differential; wider regression still required**

MRGF4's generated checked CodePage write previously exited before the inline
MOVSR pointer/count tail. The repair emits the completed one-dword `ESI/EDI`
and `ECX` commit only while the guarded EA32 REP inline MOVSR body is being
generated. `emulateSingleOp()` temporarily clears that marker around its own
bailout check, so interpreter-completed nonzero-base, stub, and inner
read/write fallback paths cannot double-commit. Independent static review
found no remaining P0/P1 in this scope.

The same sole CDP page was moved MRGN4 then MRGF4 at entry `391`, with cache
disabled. Rebuilt served HTML/JS/Wasm bytes matched disk SHA-256; both modules
validated and MRGN4/MRGF4/MRGF3 retained exactly 41 public exports.

**VERIFIED final direct outputs:** MRGF4 logged a first Wasm JIT block and
direct-chain ABI, then `generated checked-write=1 bailout-taken=1` and `0
tests FAILED`. Scripted comparison of the complete states after the CodePage
write and after the re-decoded successor passed exactly:

```
post-write: regs=10203040/00000000/A55A0102/A55A0103/A55A0104/A55A0105/F0000184/D0000007 flags=000008D7 eip=00000003 next=242 code=3EF3A540CD9790 source=9097CD40
final:      regs=10203041/00000000/A55A0102/A55A0103/A55A0104/A55A0105/F0000184/D0000007 flags=000008D7 eip=00000004 next=1364 code=3EF3A540CD9790 source=9097CD40
```

The final `EIP=4` also required a test-only Wasm `onTestEnd()` correction to
write the current TestEnd EIP, matching NormalCPU and generic JIT. INT 97
decodes to TestEnd only under `__TEST`, so this has no production opcode path.

This closes only DF0 direct-scalar SMC re-decode. Before publishing the
runtime-zero MOVSD candidate or opening MRG2/cache/replay/FPS, required
regressions are: (1) equivalent DF1 active-code write/redecode differential;
and (2) a nonzero source-base SMC row proving the exact emulation fallback
does not receive the inline post-write commit. All publication remains closed.
