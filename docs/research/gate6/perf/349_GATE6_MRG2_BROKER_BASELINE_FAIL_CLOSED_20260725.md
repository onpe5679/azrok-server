# 349 — MRG2 broker baseline fail-closed

> **SUPERSEDED in part by 350.** The recorded pre-child failure was real, but
> its cause was the stale test-only `cmd: 'callHandler'` relay encoding. MRG2
> cross-worker execution later passed after the numeric Emscripten relay repair;
> this document remains the fail-closed record captured before that repair.

Date: 2026-07-25  
Scope: private MRG2 cross-worker fixture; no accepted artifact or performance
path was changed.

## Result

**VERIFIED FAIL-CLOSED.** MRG2 cannot yet make a cross-worker claim.  Its
browser test failed before `scheduleThread(child)` and before any child guest
state or worker-delta assertion.  Both published slots already pointed at the
same grouped module/memory/incarnation, but the broker publication barrier did
not complete.

The private MRG2 diagnostic emitted:

```text
MRG2 publication first=1/001BA220/1 second=1/001BA220/1 memory=001BA220 published=0 slots=8187/8188 groups=1 modules=1
Test MT WASM JIT scheduleThread preload ... FAILED
  MT WASM scheduleThread publishes one exact grouped broker module
1 tests FAILED in 5s
```

This is not an MRG2/MOVSD attribution.  As a direct control, the unmodified
MRGF5 build was navigated on the same sole visible CDP page to the same existing
test entry (`?21&1&1`) and produced the **identical** pre-child failure:

```text
Test MT WASM JIT scheduleThread preload ... FAILED
  MT WASM scheduleThread publishes one exact grouped broker module
1 tests FAILED in 5s
```

Thus the restored browser environment currently fails the pre-existing broker
baseline too.  The MRG2 guest body was not reached and no assertion about its
MOVSD runtime-zero arm, table install, child execution, cache, replay, or FPS
is valid.

## MRG2 implementation gate reached

**VERIFIED static/build.** The private target uses `Build/MRG2`, an exclusive
cross-worker macro, test-JIT sources, and an explicit broker pre-JS relink
dependency.  Its `MOVSD; JMP` first block and separate `NOP; TestEnd` second
block preserve a two-slot runtime group; the child contract is exact MOVSD
state (ECX=0, ESI/EDI +4, copied destination dword, flags preserved) plus the
existing broker preload/hit/no-local-compile deltas.  Independent static audit
found and corrected an initial flags/`INC ECX` P0 before build.  Served MRG2
JS/Wasm matched disk exactly and Wasm validation passed.

The publication diagnostic is macro-gated and preserves the pre-existing
short-circuit: it calls the publication barrier only after the two refs and
memory incarnation match.  It may be retained solely while resolving this
baseline.

## Next required measurement

**NOT VERIFIED:** diagnose why
`bwWasmJitBrokerPublicationBarrier` does not set its completion word despite
the local 2-slot group/ref being valid.  The minimum next measurement is the
barrier's main-registry presence and callback completion state for module 1,
followed by the same control build.  Only after that existing baseline passes
may MRG2 be rerun; otherwise it remains fail-closed.  No cache/replay,
candidate publication, MOVSB, parity, runtime-lazy Z/NZ, or FPS work opens.
