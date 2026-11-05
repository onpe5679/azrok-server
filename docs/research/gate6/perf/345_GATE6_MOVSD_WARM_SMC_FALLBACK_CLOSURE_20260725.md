# Gate 6 MOVSD warmed SMC fallback closure (2026-07-25)

Status: **VERIFIED direct browser SMC differential complete; publication still gated**

MRGN4 and MRGF4 now cover all required warmed successor-write rows at entry
`391`: generated scalar DF0, generated scalar DF1, and runtime nonzero-source
DS fallback. Each asset was rebuilt and verified byte-for-byte through 8765;
the one existing CDP page was moved between the two private targets only.

**VERIFIED direct fallback witness:** both NormalCPU and Wasm report
`bases=DS:F0000000/ES:00000000`, ESI `00000184`, EDI `D0000007`, ECX 0,
the same seven-byte mutation `3EF3A540CD9790`, and the same final EAX/EIP/
next/TestEnd state. Thus ESI offset `0x180` demonstrably used the nonzero DS
base to read the already-verified linear source `F0000180`.

MRGF4 additionally reports:

```
fallback generated checked-write=0 bailout-taken=1
```

The zero checked-write proves the guarded runtime chose `emulateSingleOp()`
rather than the inline MOVSR body. The taken bailout proves the interpreter's
successful active-CodePage write still invalidated/redecoded the old block.
Exact NormalCPU/Wasm state parity rules out the former double-commit hazard.

Together with 343/344, this closes the MRGF4 warmed compiled SMC
invalidation/redecode fixture. The runtime-zero MOVSD candidate remains
unpublished: it still requires its own isolated candidate build, cache-OFF
visible real-game render-integrity gate, then only a permitted performance
measurement. No accepted replay/cache/FPS asset changed here.
