# 330 MOVSB fallback shape boundary

## Status

**VERIFIED static/dynamic-evidence audit; no MOVSB candidate is open.** No
implementation, build, browser run, replay, cache generation, or FPS sample
was performed for this card.

### 2026-07-25 MOVSD gate correction

**VERIFIED:** MRGF3's direct browser proof closed the MOVSD generated-inline
EIP/partial-fault browser gate (339). It is not MOVSB coverage: MOVSB has
different shape routing, byte completion, and a separate generated EIP/NEXT
obligation. Therefore MBS1 does not advance on this evidence. Under the
requested MOVSD-first order, the next card is MOVSD warmed compiled SMC
invalidation/bailout and re-decode; only later may the independent MBS1
cache-OFF smoke be considered.

## What the existing measurement proves—and does not prove

EOC1's visible cache-OFF PatHouse delta records exactly 958,656 `Movsb`
opcode tags in 22.337 s: 13.76% of `fn_8`, about 42,918/s
([317](317_GATE6_EMULATE_OPCODE_CENSUS_20260724.md)). Its instrumentation
writes only `tmpReg = inst` at generated `emulateSingleOp` and aggregates a
single opcode bucket (`source/emulation/cpu/wasm/jitWasmCodeGen.cpp:14442-14531,
5270-5278,5311-5318`). It has no direct evidence of callsite/address, phase,
EA16, REP, segment condition, live base, DF, ECX, partial fault, or completed
byte count. No surviving EOC1 output provides that split.

Therefore the MOVSD MOC3 both-live-zero result must **not** be projected onto
MOVSB.

## Static boundary

`dynamic_movsb_op` has three materially different routes
(`source/emulation/cpu/jit/jitStrings.h:244-262`):

- EA16 with REP immediately uses `emulateSingleOp`.
- EA32 with REP and either sticky `hasSetSeg[ES]` or
  `hasSetSeg[op->base]` also uses `emulateSingleOp`.
- Only the no-segment EA32 REP route reaches existing b8 `movsr`; unrep forms
  use a separate `movs` path.

`hasSetSeg` is compilation history, not a live-base predicate. A warm b8
`movsr` already contains byte-wise direct read/write loops, both DF directions,
and a partial-fault handoff which synchronizes ESI/EDI/ECX before the canonical
single-op emulation (`jitStrings.h:67-124`). First run is deliberately a
traced-stub `emulateSingleOp` (`:68-71`). The canonical generated fallback
also owns EIP/dirty-state synchronization, SMC arm/bailout, cache invalidation,
and lazy-flag reset, so generic helper deletion is unsafe.

Normal REP MOVSB uses source/ES segment bases, DF, ECX, byte read/write, and
one-byte register updates (`source/emulation/cpu/normal/normal_strings.cpp:49-63`).
Any later generated route must prove EIP/NEXT, both DF directions, zero/count
and REP behavior, source-before-destination overlap, partial read/write faults,
live segment base, SMC, and bailout. Existing generic string tests are not a
runtime witness for a new route.

In particular, Normal MOVSB reaches `NEXT()` after its loop, but generated
`movsr` emits the loop body only. The successful MOVSD MRGF2 path previously
demonstrated the resulting EIP=0 defect when a generated zero arm relied on
that assumption. A MOVSB route therefore needs its own compiled EIP/NEXT
fixture even if its b8 data loop is otherwise reused.

## Only permitted next measurement

A private **cache-OFF coverage-only** diagnostic may be opened later, separate
from EOC/MOC/MOC3/profile and mutually exclusive at compile time. It must
record at generated fallback, then snapshot under a mutex:

1. MOVSB shape `[REP, EA16, hasSetSeg]` for all eight combinations.
2. For EA32+REP+sticky-segment shape only: source segment ID, compile-time
   cause (ES-only/source-only/both), live ES/source zero state, DF, ECX bins
   0..255 plus overflow calls and requested bytes; first-run/traced-stub versus
   warm execution must be separately identifiable.
3. `fn8Total`, invalid tag, other opcode, MOVSB total, and invalid metadata.

Required fail-closed invariants are
`fn8Total = invalidTag + otherOpcode + movsbTotal`,
`movsbTotal = sum(shape)`, and the sticky EA32+REP bucket equals its valid
context partition plus invalid metadata and equals its ECX-call partition.
Requested bytes must match the ECX-weighted total. ABI/version/count/byte-size
or partition mismatch rejects before guest start and at every read. An
`invalidMetadata` observation is itself rejected at read time: it remains in
the raw partition equation for diagnosis but cannot become optimization
coverage evidence.

The private runtime may only reach a full visible 1024x768 PatHouse with ring
errors zero; it must use `jitCacheUrl=off`, no record/replay/cache generation,
and no FPS claim. Until that evidence exists, a runtime-zero b8 MOVSB route is
not a candidate and MRG/MOVSD remains wholly independent.
