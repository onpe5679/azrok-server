# 366 -- FISTP FQ1 outcome census reopen boundary (2026-07-25)

Status: **VERIFIED static/dynamic design -- FQF2 generated-helper gate required**

## New direct boundary evidence

365 directly proves the private NormalCPU FISTP-qword protected-destination
row: exact saved EIP, `SIGSEGV/SEGV_ACCERR`, unchanged destination and no pop
are observable before the fixture runs its handler.  That closes the fault
semantic prerequisite from 364, but it is not evidence for the generated
Wasm fallback path because FQF1 deliberately pins its operations to
`NormalCPU::getFunctionForOp`.

## Verified execution route and outcome boundary

- **VERIFIED static:** the actual uncached route is
  `JitFPU::dynamic_FISTP_QWORD_INTEGER` -> generic `JitCodeGen` fallback ->
  `JitWasmCodeGen::emulateSingleOp` -> `wasmHelper_emulateSingleOp` ->
  `jitRunSingleOp` -> `CPU::runNextSingleOp`.
- **VERIFIED static:** `CPU::runNextSingleOp` catches all exceptions around
  `o.pfn(this, &o)` and then returns after selecting `nextOp`.  Therefore the
  Wasm helper sees normal return for both a completed FISTP and a protected
  destination write fault.  A helper-level catch/rethrow or post-helper FPU
  observation is invalid evidence.
- **VERIFIED static:** `common_FISTP_QWORD_INTEGER` performs `FST_I64` then
  `FPOP`; fault delivery is the only no-pop classification.  The first
  `getNextOp` catch is a decode/fetch path and must not count as a FISTP
  outcome.

## Required private FQF2 gate

Before any FQ1 runtime snapshot, build an isolated test-only FQF2 target that
does **not** use direct NormalCPU dispatch and proves the generated fallback
itself.  It needs a generated-helper-hit witness and two rows:

1. protected destination: `entry=1`, `fault-delivery=1`,
   `normal-completed=0`, unchanged guard, exact saved EIP, retained ST0/tag,
   handler reaches TestEnd;
2. writable destination: `entry=1`, `normal-completed=1`,
   `fault-delivery=0`, completed store/pop.

At the `CPU::runNextSingleOp` operation-local boundary, copy the exact
private-FQ1 predicate before calling `o.pfn`; record normal result immediately
after its return or fault-delivery inside that same catch before `getNextOp`.
The ticket must be consumed once and reject stale/double/unknown outcomes.
No result may be inferred after helper return.

Pre-helper fields may use a macro-isolated ticket and codegen-private prior-op
state, or the established scratch fields only if every generic helper call
overwrites them and their exclusive ownership is statically proved.  The
former is preferred for FQF2/FQ1 because current private census families also
use `tmpReg`, `memHelperAddr` and `memHelperValue`.  Pair classification needs
codegen-private prior-op/EIP continuity; `DecodedOp` has no previous link.
EA must come from `calculateEaa`, not reimplemented segment arithmetic.

Only after FQF2 passes may FQ1 add a unique cache-off ABI/snapshot layout,
served-byte checks, browser loader fail-closed gates and two visible real-game
snapshot deltas.  Its bucket equations must reconcile entry with normal-pop,
normal-no-pop and fault-delivery; cache/replay/FPS remain forbidden.
