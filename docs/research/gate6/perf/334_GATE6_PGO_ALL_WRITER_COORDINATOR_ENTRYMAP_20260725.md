# Gate 6 PGO all-writer coordinator entry map (2026-07-25)

Status: **VERIFIED static/dynamic-evidence audit / coordinator NOT IMPLEMENTED**

> **PARTIALLY SUPERSEDED by 336.** The NativeSocket entry below is a native
> host-thread fact, not a browser participant.  In the Emscripten target its
> socket polling runs in MainLoop and must not be counted as a second writer.

## Purpose

Documents 328--329 correctly block a browser PGO-generation capture until all
LLVM instrumentation writers are quiescent.  This card maps the actual
production entry/exit and safe-point boundaries needed for that private
coordinator.  It is not a PGO build, raw capture, replay, or FPS card.

## Directly verified participant boundaries

- **VERIFIED -- guest CPUs:** `scheduleThread()` is the common CPU creation
  boundary (`source/emulation/cpu/normal/normalPlatformMultiThreaded.cpp:117-129`).
  A participant must register before its pthread may execute.  It must
  unregister in `platformThread()` before `cpu->thread->cleanup()` and
  `process->deleteThread()` (`:56-99`).  The only common cold safe point is
  immediately after `cpu->run()` returns and before the next call
  (`platformThreadRun`, `:50-54`).
- **VERIFIED -- main/application worker:** the accepted Emscripten target uses
  `-pthread -sPROXY_TO_PTHREAD=1 -sPTHREAD_POOL_SIZE=32`; its C++ main loop
  remains scheduled by `emscripten_set_main_loop`
  (`project/emscripten/makefile:160`, `source/sdl/emscripten/mainloop.cpp:54-82,206`).
  It is outside `platformThreadCount`, so it needs an explicit callback-boundary
  participant/safe point.
- **VERIFIED -- auxiliary native worker:** native socket polling starts a
  `KNativeThread::createAndStartThread()` worker
  (`source/kernel/knativesocket.cpp:456-469`).  It is also outside the guest
  CPU count and requires explicit registration and a loop safe point, or a
  directly proven stopped/joined condition.
- **INFERRED, not admissible for exclusion:** the current audio JS proxies
  browser-main audio operations and C++ queues audio, but this audit does not
  prove whether every audio callback stays out of instrumented Wasm.  A
  private PGO-gen identity witness must prove non-writer status before audio
  may be omitted from the participant set.

## Why existing mechanisms cannot substitute

- **VERIFIED:** `BOXEDWINE_WASM_JIT_MT_GROUP_WORKER_PAUSE` is test-only and
  parks one next group-worker statistics event under its statistics mutex.  Its
  fixture only proves a stats copy waits for release; it does not register,
  park, or count CPU/main/auxiliary instrumentation writers.
- **VERIFIED:** the browser broker `barrier` is message-delivery acknowledgement
  (`received++/notify`) over allocated worker-pool shapes.  It does not park at
  a guest-block boundary and does not establish a writer quorum.  Therefore
  broker ACK and JIT pause are not profile-capture quiescence witnesses.
- **VERIFIED:** production Emscripten CPU pthreads are detached; the join helper
  is test-only.  An unregister during a frozen epoch must therefore invalidate
  capture rather than be treated as a joined departure.

## Required private coordinator contract

Under one coordinator mutex, freeze a generation-specific participant set.
Each registered domain may acknowledge only from its stated safe point; CPU
acknowledgement must additionally prove it is outside `cpu->run()`.  Capture
is permitted only while all of the following are true:

```
expected == arrived == parked
active_guest_blocks == 0
membership_generation unchanged since freeze
same requested epoch at every acknowledgement
```

Only then may a private PGO-gen build call the LLVM buffer-size/write APIs.
JS copies the returned bytes before release.  Release requires every parked
member to depart, or an explicitly recorded completed unregister; no new
epoch/capture may overlap that release.

The mandatory fixture must produce one success record containing epoch,
frozen membership, arrivals/parks, buffer size and raw SHA, and reject with
no raw for: timeout/missing arrival, stale or duplicate epoch, registration or
unregistration during freeze, active guest block, write before quorum, and a
second epoch before all departures.  Existing JIT pause/release code may only
inspire that fixture's negative-test shape.

## Decision

The coordinator is the next PGO prerequisite, but is **NOT IMPLEMENTED** and
no PGO-generation build may start.  Documents 328--329 remain in force; the
accepted ABI2 stem is unchanged.
