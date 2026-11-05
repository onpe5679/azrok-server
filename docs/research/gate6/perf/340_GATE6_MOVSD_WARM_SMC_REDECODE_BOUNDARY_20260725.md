# Gate 6 MOVSD warmed SMC re-decode boundary (2026-07-25)

> **SUPERSEDED in part by 341.** The original unprefixed `F3 A5` bytes decode
> with base ES and cannot prove the intended source-only sticky-DS guard. The
> corrected shared fixture uses `3E F3 A5` and successor offset +3.

Status: **VERIFIED static/dynamic design; implementation NOT VERIFIED**

## Why the next row is a successor mutation

MRGF3 closes generated inline MOVSD EIP and partial-fault correctness only.
The remaining required MOVSD-first row is warmed compiled self-modifying code.
It must not overwrite the MOVSD start byte: the expected active-block bailout
resumes at B5+2, so a start-byte mutation cannot prove that successor execution
was re-decoded rather than continued through a stale compiled tail.

The private MRGF4 row must compile source-only-sticky DS B5 from:

```text
F3 A5 41 CD 97 90     ; REP MOVSD; old successor INC ECX; TestEnd; NOP
```

with live DS=ES=0, ECX=1, source four bytes `40 CD 97 90`, and destination
`TEST_CODE_ADDRESS+2`.  The generated MOVSD checked CodePage write replaces the
old successor with `INC EAX; TestEnd; NOP` while the B5 block is active.
Stale execution would retain ECX=1; correct invalidate/bailout/re-decode gives
ECX=0 and EAX incremented at the new successor.

## Required fail-closed oracle

- **VERIFIED static:** prepare all source/code bytes before publication; warm
  the exact B5 root, require `blockOpCount >= 2` and confirm the original
  successor belongs to that root.
- **VERIFIED static:** invoke the warmed root exactly once through the normal
  Wasm entry.  The generated checked write must cause active-block invalidation
  and `emitBailoutCheck()` at B5+2.
- **VERIFIED static:** after invalidation, never dereference the old
  `DecodedOp*`; reacquire the successor via live `memory->getDecodedOp(B5+2)`.
  Check mutated bytes, ESI/EDI +4, ECX=0, EIP=B5+2, fresh next-op, no active
  block and cleared bailout state.
- **REQUIRED implementation:** MRGF4-only bailout-taken counter at the actual
  taken arm. The global bailout flag is cleared by its handler and cannot alone
  prove the arm executed.
- **REQUIRED runtime:** dispatch the fresh successor and compare all GP state,
  flags, EIP/next-op, code bytes and guest memory against a separately measured
  private `BOXEDWINE_DIRECT_NORMAL_DISPATCH` NormalCPU browser oracle. Do not
  hardcode an inferred oracle.

## Isolation and ordering

Use new macro `BOXEDWINE_WASM_JIT_MOVSD_MRG_SMC_FIXTURE`, dedicated
`Build/MRGF4`, a dedicated test entry and explicit broker-JS relink prerequisite.
MRGF3, accepted assets/ABI/exports, MRG1/MRG2/cache/replay/FPS remain untouched.

Only a passing NormalCPU oracle, static audit, MRGF4 browser row, then any
separate EA16/worker-table decision may open MRG2. MOVSB/MBS1 is independent
and remains deferred.
