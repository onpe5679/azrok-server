# Gate 6 private PGO coordinator fixture (2026-07-25)

Status: **VERIFIED implementation/static syntax; native runtime fixture NOT VERIFIED**

## Private implementation

`source/emulation/cpu/wasm/wasmPgoQuiesce.{h,cpp}` introduces a coordinator
only when `__TEST` or the future private `BOXEDWINE_WASM_PGO_QUIESCE` macro is
defined.  The accepted ABI2 build defines neither and has no coordinator call
site, export, cache, replay, or asset change.

The coordinator gives each participant an opaque token and snapshots registered
membership at `Begin`.  It has explicit GuestCpu/MainLoop/NativeSocket domain
tags, but has not yet connected those tags to production lifecycle hooks.
`Poll` is therefore a fixture safe-point API, not evidence that an Azrok worker
currently parks.

> **Browser correction (336):** `NativeSocket` remains a fixture enum value,
> but is not a separate browser participant.  The Emscripten socket path is
> polled by MainLoop; production must not double-count it.

The guarded state machine provides these fail-closed properties:

- ready requires matching epoch plus `expected == arrived == parked`, no active
  participant, and unchanged frozen membership;
- a successful private copy callback is recorded exactly once for the epoch;
  `Release` refuses before that record;
- timeout through `WaitReady`, false copy result, registration/unregistration
  while frozen, or explicit cancel marks the epoch failed, wakes parkers and
  makes their `Poll` return false;
- copy callback exceptions first fail/wake the epoch and then rethrow;
- release-pending blocks a following `Begin` until parked participants leave;
  lifecycle changes after an already successful release cannot retroactively
  change that capture result.

## Regression fixture

`source/test/testWasmPgoQuiesce.cpp` is registered only for
`__TEST && BOXEDWINE_MULTI_THREADED`.  It exercises partial quorum rejection,
duplicate poll/stale-ready rejection, pre-copy release rejection, one
successful capture/release, timeout cancellation, false-copy cancellation,
registration/unregistration during freeze, active GuestCpu rejection and empty
membership rejection.  Every spawned test thread has a cancel-or-release path
before join; a failed assertion cannot leave a parked test worker behind.

The deterministic native execution still needs a Linux MT test runner.  This
Windows workspace's Git-Bash `make test` invokes the installed Windows make and
stops at `project/linux/makefile:103: multiple target patterns`; no test binary
or test-row result is claimed.  The failure is a host make-path limitation, not
a coordinator pass/fail result.

## Static verification

Emscripten 6.0.3 syntax validation passed with
`em++ -std=c++20 -D__TEST -DBOXEDWINE_MULTI_THREADED -fsyntax-only` for the
coordinator and test, and passed separately for the `testMain.cpp`
registration.  Only six existing
SIMDe deprecated-Emscripten-version warnings were emitted per translation
unit; no new error or warning is attributed to this card.

## Remaining gates

Before PGO-gen can expose LLVM buffer APIs, run the native fixture under a
working MT test target, connect the three known domain lifecycle/safe points,
finish the complete auxiliary writer inventory (audio remains NOT VERIFIED),
then prove the same epoch and byte-copy contract in a private Emscripten
runtime.  No PGO generation, raw/profile export, merge, PGO-use build, replay,
or FPS measurement is authorized yet.
