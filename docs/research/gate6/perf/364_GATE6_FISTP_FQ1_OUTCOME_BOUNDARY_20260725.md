# 364 -- FISTP FQ1 outcome boundary (2026-07-25)

Status: **VERIFIED static / FQ1 browser census BLOCKED before build**

## Direct control-flow evidence

- **VERIFIED:** The uncached branch of
  `JitFPU::dynamic_FISTP_QWORD_INTEGER` calls the base
  `JitCodeGen::dynamic_FISTP_QWORD_INTEGER(op)`
  (`source/emulation/cpu/jit/jitFPU.cpp:1220-1236`).  In the Wasm backend
  this reaches `JitWasmCodeGen::emulateSingleOp()`, which synchronizes dirty
  state, records any diagnostic metadata before `fn_8`, and invokes
  `wasmHelper_emulateSingleOp`.
- **VERIFIED:** `wasmHelper_emulateSingleOp` calls `jitRunSingleOp(cpu)` once
  (`source/emulation/cpu/wasm/jitWasmCodeGen.cpp:5386-5414`).  The helper has
  no FISTP-specific completion or fault result today.
- **VERIFIED:** `jitRunSingleOp` is a one-line call to
  `CPU::runNextSingleOp()` (`source/emulation/cpu/jit/jitCodeGen.cpp:992-994`).
  `CPU::runNextSingleOp()` catches exceptions thrown while dispatching the
  copied NormalCPU op, deliberately suppresses them, then assigns
  `nextOp = getNextOp()` (`source/emulation/cpu/common/cpu.cpp:1294-1332`).
  Therefore a `try/catch/rethrow` around `jitRunSingleOp` in
  `wasmHelper_emulateSingleOp` cannot observe the ordinary destination-write
  fault path that FQ1 must distinguish.
- **VERIFIED:** Normal `common_FISTP_QWORD_INTEGER` performs `FST_I64` before
  `FPOP` (`source/emulation/cpu/common/common_fpu.cpp:1356-1364`).  A
  destination write fault must retain pre-pop state, so inferring an unwind
  outcome from state after `jitRunSingleOp` is invalid.
- **VERIFIED:** The dedicated Wasm JIT compilation rule already uses
  `-fwasm-exceptions`, but that makes a catch technically available; it does
  not bypass the explicit catch in `CPU::runNextSingleOp`
  (`project/emscripten/makefile:664-682`).

## Consequence

The FQ1 contract in 363 requires the exact partition
`entry = normal-pop + normal-no-pop + unwind`, without post-fault inference.
The proposed generic helper instrumentation cannot supply that partition:
the NormalCPU dispatcher consumes the relevant throw before the helper can
count or rethrow it.  Publishing a private asset with an apparent `unwind`
cell would therefore be misleading even if its ABI, reader and visible game
smoke all passed.

This is a **pre-build fail-closed stop**, not a claim that FISTP is cold or
that the fallback is safe to optimize.  No FQ1 macro, CPU-layout change,
asset, page hook, cache, replay, FPS sample or browser navigation was made.
The existing MBS4 cache-OFF tab remains the sole tab.

## Required reopening path

Before an FQ1 runtime build, add a private NormalCPU/Wasm fixture path that
observes the exact FISTP dispatch/fault delivery boundary *inside or below*
`CPU::runNextSingleOp`, preserving its existing catch behavior.  The fixture
must directly prove the write-PF/no-FPOP and saved-EIP/handler rows.  Only
after that proof may a FQ1 snapshot expose a separate outcome field; the
generated pre-helper metadata may then be joined to a witnessed result rather
than to post-fault CPU state.

The separate static prerequisites remain: record pre-call EA16/EA32,
segment, linear page-cross, RC, cached state, and immediate FILD-m64 pair
relation; use a private mutually-exclusive cache-OFF stem and fail-closed
loader; keep record/replay/Present capture/FPS disabled.  The historical
FISTP assets remain prohibited.
