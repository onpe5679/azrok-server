# Gate 6 MOVSD warmed SMC fixture implementation (2026-07-25)

> **SUPERSEDED by 342.** The later browser gate established the decode-publication P0 and the generated-path architectural-state P0.

Status: **VERIFIED source isolation/static review; build and browser runtime NOT VERIFIED**

## Scope and isolation

MRGN4 and MRGF4 remain distinct private targets.  MRGN4 combines
`BOXEDWINE_DIRECT_NORMAL_DISPATCH` with the NormalCPU oracle macro.  MRGF4
combines the existing runtime-zero MOVSD guard with only
`BOXEDWINE_WASM_JIT_MOVSD_MRG_SMC_FIXTURE`.  The source rejects Oracle+Fixture
and MRGF4+MRGF3-census macro mixtures.  Neither target alters accepted assets,
exports, cache, replay or FPS paths.

The private MRGF4 CPU layout adds two generated-body witnesses:

- `wasmJitMovsdSmcCheckedWriteCount`, incremented only in the generated REP
  MOVSD checked-write slow arm; and
- `wasmJitMovsdSmcBailoutTakenCount`, incremented only inside the taken
  `emitBailoutCheck()` arm.

The second counter is required because the generated arm clears
`wasmJitBailout` before return.  It is not a helper-side proxy.

## Fixture row

Both targets publish exactly `3E F3 A5 41 CD 97 90` before any decode and
write the source dword `0x9097CD40` before publication. `3E` is mandatory:
without it A5 decodes with base ES, so DS-sticky-only cannot select the
runtime-zero guard. They make DS sticky by nonzero-to-zero transition without
touching ES, therefore the actual row has live DS=ES=0 and decoded base DS.
MRGF4 warms the root using ECX=0, then proves the original successor at B5+3
is the root's `next` and belongs to the root before mutation.

The one mutation has ECX=1, ESI=source and EDI=B5+3.  Post-write logic never
dereferences the old root or successor.  It obtains only a new successor with
`memory->getDecodedOp(B5+3)`, requires generated checked-write=1 and
bailout-taken=1, then requires the pre-successor state ECX=0,
ESI=source+4, EDI=B5+7 and EIP=B5+3.  It dispatches that fresh successor to
TestEnd and emits a complete architectural snapshot.

MRGN4 executes the mutating MOVSD through `CPU::runNextSingleOp()`: direct
NormalCPU `NEXT()` cannot use the old root tail because invalidating B5+3
replaces it with `Done`.  `runNextSingleOp()` executes a private live-op copy,
then obtains a fresh next op.  MRGN4 separately dispatches the re-decoded
successor and emits the same final snapshot.  The browser gate must compare
both snapshots externally; no MRGF4 expected state is copied from an inferred
NormalCPU value.

The first MRGN4 browser attempt reached the right entry but failed before
execution. Static audit found the actual cause: unprefixed A5 decodes with
base ES in both targets, so removing the DS check only from MRGN4 would make
the oracle and candidate exercise different routes. The common `3E` prefix
restores the required base DS; all successor offsets and state checks are
shifted by one. Both private assets must be rebuilt before the oracle is
re-run.

## Current build boundary

`make -n` through the portable make parser resolves both private target flag
sets and the broker prerequisite.  After the user-reported Windows logout,
WSL creation returns `E_ACCESSDENIED` and direct Emscripten `clang++.exe`
execution returns `permission denied`; neither is a source compile result.
No MRGN4/MRGF4 artifact, CDP navigation, browser result, MRG2, MOVSB, cache,
replay or performance claim is made from this implementation.

The next required evidence remains: recover a working compiler execution
surface, build the two dedicated assets, obtain MRGN4 browser oracle output,
then navigate the same single CDP page to MRGF4 and compare all snapshot
fields plus the two MRGF4-only counters.

The raw source array places this test at 399, but eight conditionally excluded
entries precede it in these MT private builds.  The browser-proven runtime
entry is therefore zero-based **391** (query `?391&1&1`); require both that
query and textarea `starting at 391`.  Re-derive it after any test-list macro
change; it is not a substitute for a fresh private build or browser result.
