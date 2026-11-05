# 155 — acknex.dll / Azrok.exe x87 Precision Control (PC field) — VERIFIED via decompile + call-chain trace

**Question**: does the game set the x87 control-word Precision-Control (PC, bits 9-8) to 80-bit
extended, 53-bit double, or 24-bit single — and is BoxedWine's fixed 53-bit native-`double`
x87 emulation path (see `147_WEB_A_WEBGL2_DESIGN`) therefore safe for this game?

**Method**: Ghidra MCP only (`analyzeHeadless`-backed GUI instance, project `azrok`), read-only.
No game execution, no binary edits. Used `run_ghidra_script`/inline Java scripts (via
`ghidra_scripts/*.java`) to (1) enumerate every `FLDCW`/`FNSTCW`/`FSTCW` instruction in both
`acknex.dll` and `Azrok.exe`, (2) for each `FLDCW` walk backward to the nearest register-destination
`OR`/`AND` immediately feeding it (filtering out unrelated memory-operand `OR`s that happened to sit
in between), (3) decompile every function that touches the PC field, and (4) trace true callers
through this binary's known incremental-link thunk table (`0x004d7000-0x004e2100`, see
`_img2011_symbol_mapping.md [16]`) since direct xref lookups miss callers that route through it.

## Result 1 — the omnipresent FLDCW/FNSTCW pattern (719 sites in acknex.dll, 72 in Azrok.exe) is NOT precision policy

**VERIFIED** (disassembly, e.g. `acknex.dll!file_var_read@100077e0`):
```
FNSTCW word ptr [ESP+8]      ; save current CW
MOVZX EAX, word ptr [ESP+8]
OR AH, 0xc                   ; = OR full-word CW with 0x0C00 -> RC field (bits 11-10) = 11 (truncate)
MOV [ESP], EAX
FLDCW [ESP]                  ; load modified CW
FISTP dword ptr [ESP]        ; float -> int, using truncation
MOV EAX, [ESP]
FLDCW [ESP+8]                ; restore ORIGINAL saved CW
```
This is the textbook MSVC/Borland-style "round-to-zero bracket" used at every `(int)float` cast
site. `AH` is bits 8-15 of the CW; `0xc` in `AH` = bits 2-3 of `AH` = bits 10-11 of the full
word = the **Rounding Control (RC)** field, not PC. It reads whatever PC bits are already active,
never touches them, and restores the exact original word afterward. Present in `vec`, `phent_*`,
`sin/cos/tan/asin/...`, `str_to_num`, physics getters, etc. — i.e. essentially every float→int
conversion in the engine. **Conclusion: none of these ~790 combined sites are a precision-policy
decision; they are RC-only, self-restoring, and orthogonal to PC.**

## Result 2 — the only PC-touching code is a narrow, self-restoring CRT fmod/remainder helper

**VERIFIED** (decompile): `acknex.dll!FUN_101e8d06`/`FUN_101e8f0c` (mirrored in `Azrok.exe` at
`FUN_0066ef96`/`FUN_0066f19c`) contain `AND EAX,0x100` / `OR EAX,0x300` / `OR EAX,0x33f`
immediately before their `FLDCW`. `0x300` = bits 9-8 = PC **11 (extended, 80-bit)**; `0x33f` = same
PC=11 plus all exception masks, RC=00. Decompiled body is a `float10`-typed (80-bit) argument-reduction
loop (`ABS`, ratio/quotient, `float10` intermediates) — this is the standard CRT technique of forcing
full 80-bit precision *just* for an extended-precision remainder/fmod core, then implicitly restoring
whatever PC was active on return (function-scoped, not global). `FUN_101e8f0c` has exactly **one**
caller in the whole DLL. **This is not the game's ambient precision — it's a rare, self-contained
exception to it.**

`acknex.dll`'s own statically-linked `__control87`/`__controlfp`/`__ctrlfp` (FLIRT-matched
"Visual Studio 2003 Release") are present but: `__control87`'s only caller is `__controlfp` (0 callers
found anywhere in the DLL — dead/unused), and `__ctrlfp` (a pure getter, `return in_FPUControlWord`)
is called only by `_fabs`, `_frexp`, `_ldexp`, `__modf_default`, `__umatherr`,
`__handle_qnan1/2`, `__87except` — all of which only **read** the CW to inspect exponent/exception
state, never write PC. **acknex.dll never calls anything that changes the ambient PC field.**

## Result 3 — Azrok.exe's CRT startup explicitly forces PC = 53-bit (double), VERIFIED end-to-end

Full call chain, each hop confirmed by decompilation (function bodies FLIRT-matched to
"Visual Studio 2005 Release" CRT object code) and by tracing real callers through the
incremental-link thunk table:

```
___tmainCRTStartup@006571e6                                  (VERIFIED disassembly)
  006572b3-b5: XOR EBX,EBX ; INC EBX        -> EBX = 1 (never clobbered after: all
                                                 intervening CALLs are __cdecl, EBX is
                                                 callee-saved)
  0065732a: PUSH EBX ; 0065732b: CALL __cinit   -> __cinit(1)
    -> __cinit(param_1=1)@0065c076              (VERIFIED decompile, matches real CRT source)
         if (PTR___fpmath != 0 && writable-check) (*PTR___fpmath)(param_1);
         -> __fpmath(1)@0065364d                (VERIFIED decompile)
              _cfltcvt_init(); _ms_p5_mp_test_fdiv();
              if (param_1 != 0) __setdefaultprecision();     // param_1==1, branch taken
              -> __setdefaultprecision()@00669367            (VERIFIED decompile)
                   __controlfp_s(NULL, 0x10000, 0x30000);
                   -> __controlfp_s(cur=NULL, NewValue=0x10000, Mask=0x30000)@004dcc85
                        (VERIFIED decompile: uVar1=Mask&0xfff7ffff=0x30000;
                         (NewValue & uVar1 & 0xfcf0fce0)==0 -> success path taken)
                        __control87(0x10000, 0x30000);
                        -> __control87(new=0x10000, mask=0x30000)@004d8aea
                             (VERIFIED decompile: return cur & ~mask | (new & mask))
```

`0x10000` / `0x30000` are the portable `<float.h>` constants **`_PC_53` / `_MCW_PC`**
(confirmed independently: `acknex.dll!___control87_2`'s decompiled bit-mapping shows raw CW
`0x300`(PC=11)->portable `0`(none of 0x10000/0x20000 set, i.e. `_PC_64`=0), raw `0x200`(PC=10)->
portable `0x10000`(`_PC_53`), raw `0x000`(PC=00)->portable `0x20000`(`_PC_24`) — the standard
MS CRT encoding). So `__control87(0x10000, 0x30000)` clears the PC field and sets it to
**`_PC_53` = raw CW bits 9-8 = "10" = 53-bit double precision** — unconditionally, every run,
before `main()`/game code ever executes. (`__set_controlfp`'s own `_NewValue` constant `0x9001f`
independently decodes to the classic CRT `_CW_DEFAULT = _RC_NEAR | _PC_53 | all-exceptions-masked`,
corroborating the same 53-bit policy from a second, structurally-identical code path — though this
particular routine's own caller was not found via direct or thunk xref, so treat that second
corroboration as supporting, not load-bearing.)

Separately, `Azrok.exe!__trandisp1`/`__trandisp2` (CRT transcendental-function stack-check helpers)
do `AND BH,0xfe` right before their own `FLDCW` — `BH` = CW bits 8-15, clearing bit 8 only. If PC
was 11 (extended) this downgrades it to 10 (double); if already 10 it's a no-op. This is a second,
independent piece of CRT internals reinforcing/never fighting the 53-bit ambient state — never
pushing toward extended.

## Conclusion

**PC field: lowered to 53-bit (double) — VERIFIED.** Not "left at 80-bit default", not mixed policy
for the parts that matter: Azrok.exe's own CRT startup (`_cinit(1)`→`__fpmath(1)`→
`__setdefaultprecision()`→`_controlfp_s(NULL,_PC_53,_MCW_PC)`→`__control87`) forces the x87 CW to
53-bit precision on the process's main thread before any game/engine code runs, and this is a
**per-thread hardware register** — `acknex.dll` executes on that same thread and never itself calls
anything that changes PC (verified: its own `__control87`/`__controlfp` have zero real callers, its
`__ctrlfp` uses are read-only). The two loose ends are (a) `__set_controlfp`'s caller was not located
(INFERRED/NOT VERIFIED that it fires — but it targets the identical `_PC_53` policy, so it cannot
contradict the finding even if dead code), and (b) whether some *other*, unfound call site later in
gameplay re-raises PC to extended — none was found in an exhaustive instruction-level sweep of both
binaries (791 combined FLDCW/FNSTCW/FSTCW sites fully enumerated and classified), so this is treated
as VERIFIED-complete for the static surface, not proof against a dynamic edge case never exercised.

**BoxedWine's fixed-53-bit-double x87 shortcut is SAFE for this game.** Because the game's own CRT
startup already restricts the x87 unit to 53-bit mantissa precision for essentially the entire
runtime (transform/lighting FADD/FMUL chains included — nothing in the hot path touches PC), a host
that computes x87 ops as native 53-bit `double` is bit-for-bit equivalent to real hardware here,
*provided* BoxedWine still honors the RC (rounding-control) field, which the mission brief already
confirmed it does. The only precision-sensitive divergence risk (the narrow 80-bit fmod-reduction
helper, `FUN_101e8d06`/`0066ef96`) is self-contained, restores its own CW, and executes once from a
single call site in each binary — a 53-bit shortcut there would only matter if that exact remainder
path is exercised with operands large enough to hit its "large exponent difference" branch, which
is a pre-existing narrow edge case independent of the emulator question.

**Evidence classification summary**:
- CRT call chain `_cinit→_fpmath→_setdefaultprecision→_controlfp_s→_control87` setting `_PC_53`: **VERIFIED** (decompiled every hop, FLIRT-matched to real MSVC CRT object code, thunk-aware caller trace to `___tmainCRTStartup` with the literal EBX=1 argument confirmed by disassembly).
- `acknex.dll` never itself changes PC: **VERIFIED** (exhaustive FLDCW/FNSTCW enumeration + caller trace of its `__control87`/`__controlfp`/`__ctrlfp`).
- `__set_controlfp` (second `_PC_53`-setting path) actually firing: **NOT VERIFIED** (no caller found; does not change the conclusion either way since it targets the same policy).
- No later re-raise of PC to extended anywhere in either binary's static code: **VERIFIED for the enumerated 791 sites**, not a dynamic proof.
