# 329 PGO all-writer quiesce boundary

## Status

**VERIFIED static/fixture audit; browser PGO capture remains BLOCKED
fail-closed.** No implementation, build, browser capture, profile merge, replay,
or FPS sample was run for this card.

## Direct code evidence

`platformThread(CPU*)` initializes every guest CPU thread and repeatedly calls
`platformThreadRun(cpu)` (`source/emulation/cpu/normal/normalPlatformMultiThreaded.cpp:56-76`).
`platformThreadRun` returns only after `cpu->run()` returns (`:50-54`). This is
the one common cold CPU safe-point candidate: immediately after that return and
before the next guest run. It is not an existing barrier.

The apparent JIT quiesce/test primitive is deliberately narrower. The only
pause state is under `#ifdef __TEST`, pauses one next group-worker event while
holding its statistics mutex, and waits for its test release
(`source/emulation/cpu/wasm/jitWasmCodeGen.cpp:858-861,915-972`). Its fixture
only proves that a concurrent **statistics snapshot** blocks for 250 ms then
unblocks on release (`source/test/cpu/testWasmJitBatch.cpp:637-673`). This is a
useful pause/ack/release test shape, not a guest CPU or all-writer epoch.

The browser broker likewise has only message-delivery acknowledgement:
`allocatedWorkers()` deduplicates Emscripten worker-pool shapes
(`project/emscripten/boxedwine-wasm-jit-module-broker.js:269-301`), while the
`barrier` receiver increments `received` and notifies (`:1324-1337`) and the
purge call posts it to non-source allocated workers (`:1530-1551`). A receiver
does not park at a guest-block boundary. The source/main worker, renderer/audio
domain, and native helper workers are not thereby proved stopped.

Static lifecycle audit also finds CPU registration/counting is not a quorum:
guest CPU threads are scheduled/retired around `platformThread`, whereas the
generic `KNativeThread` path can create auxiliary work outside that guest CPU
set. Main-loop execution continues while CPU threads exist. Thus neither
`platformThreadCount`, the broker's allocated-worker count, nor
`PTHREAD_POOL_SIZE=32` identifies every LLVM instrumentation writer.

## Required private PGO-gen contract

Before exposing `__llvm_profile_write_buffer`, implement and prove a private
generation-only coordinator with these fail-closed conditions:

1. Register/unregister every instrumentation-writing execution domain with a
   generation; freeze membership for one requested epoch.
2. Each participant acknowledges only from its defined safe point and parks;
   CPU workers use the `cpu->run()` return boundary above. The main loop and
   every auxiliary worker require an explicit equivalent safe point, or a
   directly verified stopped/joined proof.
3. The coordinator requires `expected == arrived`, no participant in a guest
   block, and no membership change before calling the buffer-size/write APIs.
   Timeout, stale epoch, unregister during freeze, or incomplete acknowledgement
   rejects capture without emitting a raw.
4. JS must copy the returned bytes before release; release then requires
   departed/join acknowledgement. The existing test's bounded pause/release
   fixture can be adapted to prove these negative paths, but cannot itself be
   used as the production coordinator.

Only an independently verified epoch may open 328's immutable
`raw + sidecar -> verified merge list -> llvm-profdata -sparse -> PGO-use`
lifecycle. The accepted ABI2 stem remains untouched.
