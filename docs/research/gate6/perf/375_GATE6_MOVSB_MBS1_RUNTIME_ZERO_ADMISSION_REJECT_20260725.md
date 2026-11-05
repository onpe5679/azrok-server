# 375 -- MOVSB MBS1 runtime-zero admission rejection (2026-07-25)

Status: **VERIFIED static/census rejection; no candidate build or FPS**

## Candidate considered

MBS4 census (362) found 248,972 of 254,457 production MOVSB calls in the
EA32+REP sticky-segment shape: source DS, source-only sticky history, live
ES and DS bases both zero, DF=0.  A tempting extension is the MOVSD MRG
runtime-zero pattern: retain a nonzero-base helper arm and use `movsr(b8,1,b32)`
when both live bases are zero.

## Why it is not admitted

**VERIFIED source:** `Jit::dynamic_movsb_op` sends every EA32 REP whose
`Process::hasSetSeg[ES] || hasSetSeg[op->base]` is true to `emulateSingleOp()`
(`source/emulation/cpu/jit/jitStrings.h`).  That process bit is sticky route
history, not a live-base proof.  The existing MOVSD runtime-zero implementation
retains the exact first-run traced-stub policy, tests both CPU-local bases,
uses the helper for nonzero bases, and only compiles the scalar `movsr` body on
the later warm path; it also writes successful EIP explicitly because the
inline body lacks interpreter `NEXT()` semantics
(`source/emulation/cpu/wasm/jitWasmCodeGen.cpp`, `dynamic_movsd_op`).

The same minimum safety policy would be required for MOVSB.  However 362's
complete valid B5 context has **warm=0** for all 248,972 relevant calls.
Consequently the safe MOVSB zero-base arm has **zero observed admission** and
would preserve every measured call as the existing helper/traced stub.  Moving
the arm into the cold path is not licensed: it would newly take responsibility
for REP ECX/ESI/EDI/DF updates, source-before-destination overlap, read/write
partial faults, saved EIP/handler delivery, SMC checked-write bailout and
stale-block re-decode before the first proven helper execution.

## Decision

**REJECTED before implementation:** This MBS1 runtime-zero candidate has no
safe production coverage, so it cannot plausibly improve FPS and must not
consume a private build/cache/replay/FPS cycle.  No source, accepted artifact,
record, cache or browser tab was changed for this rejected candidate.

Existing generic string/SMC tests do not close that missing generated-cold
boundary; a future MOVSB card would first require a private compiled sticky
fixture covering DF0/DF1, ECX boundaries/overflow, overlap, page read/write
faults with saved EIP, and an SMC checked-write bailout/redecode witness.

Per the census order, proceed to the already-open FISTP outcome results as the
next non-duplicate analysis card.  This does not alter 369's diagnostic-only
status or authorize a FISTP FPS candidate without its own design and gates.
