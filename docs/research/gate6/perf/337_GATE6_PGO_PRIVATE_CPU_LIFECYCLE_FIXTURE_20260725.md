# Gate 6 PGO private CPU lifecycle fixture (2026-07-25)

Status: **VERIFIED implementation/static syntax; runtime and browser proof NOT VERIFIED**

## Scope and isolation

This slice wires only guest CPU pthread lifecycle into the private quiesce
coordinator.  It does **not** wire MainLoop, audio, socket work, LLVM raw
buffers, exports, cache/replay, or any accepted ABI2 asset.  Browser sockets
remain MainLoop work under 336; no `NativeSocket` production participant was
added.

All new lifecycle code and the `KThread` token field are gated by
`BOXEDWINE_WASM_PGO_QUIESCE_CPU_FIXTURE`.  The coordinator's declaration and
definition gate now also recognizes that macro, so a standalone private
fixture build cannot accidentally compile the lifecycle calls without their
coordinator.  The accepted Emscripten make target defines neither PGO macro.

## Implemented lifecycle

- **VERIFIED static:** `KThread` owns an opaque `U64` token, not a `CPU*` or
  pthread address.  This prevents CPU reset/reuse from being mistaken for a
  frozen participant.
- **VERIFIED static:** `scheduleThread()` registers the guest CPU before
  `platformStartThread()`.  A start failure unregisters and clears the token
  before the existing JIT cancellation/count rollback.
- **VERIFIED static:** each successful `cpu->run()` is bracketed by
  `SetActive(true/false)`.  The exception route clears active then rethrows;
  it never calls `Poll`, because an exception is not a post-run safe point.
- **VERIFIED static:** normal nonterminal returns call `Poll` only after
  active has cleared.  Terminal/TestEnd returns skip Poll and unregister,
  which invalidates a freeze and wakes any parker fail-closed.
- **VERIFIED static:** unregister occurs before cleanup/delete and also before
  the existing `__TEST` TestEnd early return.
- **VERIFIED static:** that TestEnd return now decrements `platformThreadCount`
  exactly once before leaving its manually owned `KThread`; otherwise a
  two-child lifecycle fixture would leak worker accounting.

## Validation and remaining gates

Emscripten 6.0.3 `-fsyntax-only` passed all three required arrangements:

1. `__TEST + BOXEDWINE_MULTI_THREADED + CPU_FIXTURE` with coordinator, unit
   fixture, and lifecycle source;
2. `BOXEDWINE_MULTI_THREADED + CPU_FIXTURE` without `__TEST` (the previously
   missing coordinator-gate combination);
3. accepted-equivalent multi-threaded lifecycle source with the fixture off.

Only pre-existing SIMDe deprecated-Emscripten-version warnings appeared.

**NOT VERIFIED:** existing coordinator tests call `Poll` from direct
`std::thread` workers; they do not yet prove
`scheduleThread -> platformThreadRun -> unregister` using two real guest CPUs.
The required next test is a macro-gated deterministic two-CPU post-run probe:
after two nonterminal `cpu->run()` returns it must admit one Poll at a time,
reject capture at the 1/2 quorum, succeed exactly once at 2/2, then
release/join with `registered=parked=0`.  Timeout, termination/unregister
during freeze, and exception-after-active-clear also need runtime proof.  WSL
native execution remains blocked by missing SDL/OpenGL/curl/SSL/zlib development
packages; no system packages were installed.

No PGO-generation build, raw capture, browser run, cache/replay, or FPS card
is authorized by this document.
