# 363 -- FISTP qword FQ1 reopen boundary (2026-07-25)

## VERIFIED -- old FISTP evidence cannot be reused

The only retained `fistpprofile`/`fistpsites` assets are old private binaries;
the current page has no FISTP URL hook, reader, ABI exports or FQ1 build
directory.  Replaying them would reuse the rejected Wine-oriented profile,
not produce an Azrok cache-OFF witness.  The current sole MBS4 page and all
four services remain healthy and were not navigated by this inspection.

The 333 rejection remains true: EOC1's FISTP tag is entry-only.  It does not
prove an Acknex pair, completion, FPOP, fault/unwind, EA shape, RC, cached
state, or present phase.  FQ1 is reopened only as a private **diagnostic**;
it does not reopen a performance candidate.

## VERIFIED FQ1 minimal evidence contract

`JitFPU::dynamic_FISTP_QWORD_INTEGER` already inlines cached ST0, but uncached
ST0 routes to generated `emulateSingleOp`, then `wasmHelper_emulateSingleOp`,
then Normal `common_FISTP_QWORD_INTEGER` (`FST_I64` write, then `FPOP`).
`FLD_I64` deliberately marks its result uncached.  FQ1 must capture exact
pre-call shape before `fn_8`, never infer it from post-fault state, and record
under a mutex:

- EA16/EA32, source segment/base, page crossing, RC, ST0 cached state and
  decoded immediate FILD-m64 predecessor/pair destination relation;
- entry, normal-return-with-pop, normal-return-without-pop and unwind as
  separate outcomes;
- exact fixed snapshot ABI with partition equations, invalid-metadata hard
  rejection and independent pair rows.

The record site is after generated dirty-register synchronization and before
the SMC bailout/helper call.  The helper must preserve unwinding: record entry
from the stored pre-state, call `jitRunSingleOp`, record the normal outcome,
and on exception record unwind then rethrow.  A later optimization remains
blocked by a NormalCPU-vs-Wasm matrix covering all RC modes, NaN/Inf/overflow,
same/different m64, EA16/EA32, destination write-PF/no-pop, SMC and EIP.

## Next gate

Implement a new mutually-exclusive `BOXEDWINE_WASM_JIT_FISTP_QWORD_CENSUS`
asset and FQ1 page hook with cache-off/no-record/no-replay/no-capture URL and
exact ABI/word/byte gates.  Only after static audit, private build, fixture
rows and visible cache-OFF integrity may its snapshot be read.  No cache,
replay or FPS A-B-A is authorized.
