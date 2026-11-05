# 328 Browser PGO toolchain and quiesce audit

## Status

**VERIFIED static/tool audit; PGO remains NOT READY.** No PGO build, browser
profile capture, raw export, merge, cache, replay, or FPS sample was run.

## Toolchain boundary

Emscripten 6.0.3 source tests directly demonstrate the LLVM instrumentation
and sparse-merge route: `-fprofile-instr-generate` creates a `.profraw`, then
the bundled `llvm-profdata merge -sparse` consumes it. The Emscripten `-sPGO`
setting is explicitly unsupported/deprecated and is rejected as a route.

`-fprofile-instr-use` has no local successful compilation witness: direct
compiler invocation is permission-blocked and no workspace PGO-use artifact
exists. Treat profile-use as **NOT VERIFIED**, rather than inferring it from
the instrumentation/merge test or the adjacent clang binary version.

## Browser lifecycle boundary

The SDK has the buffer APIs `__llvm_profile_reset_counters`,
`__llvm_profile_get_size_for_buffer`, and `__llvm_profile_write_buffer`, but
the workspace has no PGO Make target, private capture export, profile raw,
profdata, raw-hash manifest, capture download, immutable storage endpoint or
merge pipeline. Current IDBFS mounts and JIT ZIP persistence do not prove PGO
raw recovery; the existing JIT cache upload path may overwrite generic raw
names and is forbidden for PGO.

## Required next gate

Before a private PGO-generation build, prove an all-participating-worker
quiesce epoch: each instrumentation-writing execution thread must park at a
defined safe point and acknowledge the same epoch before buffer size/write is
allowed. The JIT's local `quiescent` wording and `PTHREAD_POOL_SIZE=32` do not
prove this global condition. Only after that static/dynamic coordinator proof
may a private 32-export-freeze generation target expose the buffer bridge.

The subsequent immutable lifecycle is: raw bytes plus sidecar identity ->
verified input-list -> `llvm-profdata merge -sparse` plus nonempty-show witness
-> private PGO-use build with compile/link profile flags and out-of-date or
unprofiled diagnostics promoted to errors. The accepted stem remains untouched.
