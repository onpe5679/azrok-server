# Gate 6 MOVSD EA16 and cross-worker scope (2026-07-25)

Status: **VERIFIED static scope; browser witnesses NOT VERIFIED**

346 closes the private MRG1 build and cache-OFF rendering gate.  It does not
prove either address-size-16 MOVSD behavior or execution of the guarded module
through another worker's local Wasm table.  Those are separate correctness
boundaries, not performance work.

## EA16 boundary

**VERIFIED:** the guarded runtime-zero arm has the explicit condition
`!op->ea16` in `jitWasmCodeGen.cpp`.  Thus EA16 REP MOVSD cannot enter the
zero-base inline MOVSR body or its special post-write commit marker; it falls
through to the pre-existing string dispatcher.  That dispatcher sends EA16
REP MOVSD to `emulateSingleOp()`.  The ordinary CPU helper uses CX and the
low 16 bits of SI/DI, preserving the high halves and wrapping by four bytes.

The existing MRGF4 byte stream is EA32, so it is not EA16 evidence.  A private
MRGF5-type browser fixture must decode and assert `3E 67 F3 A5`, `ea16=1`,
source base DS and length four; warm its root; mutate successor `+4`; then
prove fresh re-decode plus CX/SI/DI low-half semantics.  Its required counter
result is `generated checked-write=0, bailout-taken=1`: helper-made SMC write
and active-block bailout, not candidate inline-write execution.  This fixture
must remain separate from MRGF3/MRGF4 and accepted assets.

## Cross-worker table/broker boundary

**VERIFIED:** MRGF4 proves a generated block on its creating worker only.
Cross-worker use needs both shared `pfnJitCode` publication and a worker-local
Wasm-table installation.  A table-slot miss lazy-installs the module on that
worker; any validation/ownership/relocation failure disables JIT and falls
back to NormalCPU.  The broker additionally rejects unknown modules, wrong
owners and stale memory incarnations.

The minimum MRG2 browser witness is an isolated adaptation of
`testWasmJitMtScheduleThreadPreload`: parent worker warms and publishes a
source-only sticky-DS, live-zero-base REP MOVSD module; a `scheduleThread`
child executes the same shared decoded op.  Required evidence is the child's
exact guest state plus a new MRG2-only generated-zero-arm counter and the
existing broker delta contract: child broker hit/preload, no local compile,
and no owner/stale/unknown error.  MRGF4's checked-write counter is SMC-only
and must not be reused for this witness.

**NOT VERIFIED / still closed:** MRG2 implementation/build/browser, cache or
replay publication, and every performance test.  A future MRG2 make target
must add its build directory both to the test-source selection branch and to
the broker pre-JS relink prerequisite, otherwise Windows make can silently
build the wrong source set or stale glue.
