# Gate 6 PGO two-CPU lifecycle fixture (2026-07-25)

Status: **VERIFIED implementation/static review; native runtime NOT VERIFIED**

## Fixture scope

`testWasmPgoQuiesceCpuLifecycle.cpp` is a private,
`__TEST + BOXEDWINE_MULTI_THREADED + BOXEDWINE_WASM_PGO_QUIESCE_CPU_FIXTURE`
fixture.  It starts two actual guest children through `scheduleThread()`, not
two direct coordinator `std::thread` calls.  It contains no MainLoop, audio,
socket, raw profile, export, asset, cache/replay, or accepted ABI2 change.

Each child executes `inc eax; jmp rel32 0` first.  The direct branch creates a
real nonterminal `cpu->run()` return, where the fixture-only post-run/pre-Poll
probe holds both children.  After the coordinator release, each continues
`inc edx; TestEnd`; the normal thread path unregisters before the test joins
and manually deletes its still test-owned `KThread`.

## Deterministic normal-row oracle

- **VERIFIED static:** both actual child tokens are registered before their
  pthread starts, then both reach the probe after active has cleared and before
  either has called `Poll` (`registered=2`, `active=arrived=parked=0`).
- **VERIFIED static:** parent begins one two-member epoch, releases exactly one
  probe permit, and waits for `arrived=parked=1`.  `Ready` and capture must be
  false at that 1/2 quorum.
- **VERIFIED static:** releasing the second permit requires 2/2/2 and active=0
  before the bounded non-reentrant callback can increment its capture counter.
  One successful release then lets both guest threads complete, unregister,
  join, and prove `registered=parked=0`, no release pending, EAX=EDX=1 and
  `TestEnd` next-op state.
- **VERIFIED static:** failure cleanup cancels a live epoch, releases every
  probe waiter, joins children, restores the main KThread, deletes test-owned
  children, then resets coordinator state.  The TestEnd worker-accounting path
  balances `platformThreadCount` before return.

Independent static and dynamic test-path reviews found no P0/P1 implementation
defect.  Emscripten syntax-only compilation passed with fixture ON and accepted
fixture OFF (only pre-existing SIMDe Emscripten-version deprecation warnings).

## Not yet proven

- **NOT VERIFIED runtime:** WSL native test binary cannot currently build because
  its SDL/OpenGL/curl/SSL/zlib development dependencies are absent.  No system
  package was installed without authorization.
- **NOT VERIFIED fixture rows:** terminal/unregister while another child is
  parked, and a real `cpu->run()` exception followed by active-clear/recovery.
  They remain mandatory before any MainLoop/raw/browser PGO gate.

The Linux default test makefile intentionally does not define the fixture
macro.  A future private execution must pass the macro explicitly and run this
test before browser work.  No PGO generation/capture/FPS result is opened.
