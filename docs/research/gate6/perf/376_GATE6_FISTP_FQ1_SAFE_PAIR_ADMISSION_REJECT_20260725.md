# 376 -- FISTP FQ1 safe-pair admission rejection (2026-07-25)

Status: **VERIFIED static/census rejection; no candidate build, cache, replay or FPS**

## What the completed census proves

FQ1's cache-OFF PatHouse snapshot S2 (369) records `7,276,007` fn8 helper entries, including `961,929` FISTP qword contexts (13.221%). All observed FISTP outcomes are normal-pop; normal-no-pop and fault are zero in that bounded scene. Its two independent post-input intervals contain 146,300 and 208,424 FISTP contexts respectively (4,876.67 and 6,947.47 per second).

This is real broad fallback hotness, not safe inline admission. The existing FQ1 layout carries source segment, EA16, pair, route, page-cross, rounding control and cached-ST0 axes. However 369 intentionally published only four sparse aggregate records (`956,803`, `6`, `22`, `5,098`), not per-tuple pair values. In particular, it does not directly prove any nonzero production coverage for an immediately preceding FILD m64 to same/different-address FISTP m64 pair. The cached axis cannot fill that gap: 369 retains it as context, not an inline/helper route witness.

## Why the broad candidate is unsafe

**VERIFIED source:** the ordinary JIT fast path is deliberately conditional. `JitFPU::dynamic_FISTP_QWORD_INTEGER` routes an uncached ST0 to `JitCodeGen::dynamic_FISTP_QWORD_INTEGER`; only cached ST0 uses its direct store-plus-pop arm (`source/emulation/cpu/jit/jitFPU.cpp`, around 1220). The matching FILD m64 path constructs ext80 state and marks it uncached (`jitFPU.cpp`, around 1179). The common FPU implementation documents the uncached representation as necessary for exact m64 round trips and uses the rounding-aware ext80-to-i64 conversion (`source/emulation/cpu/common/fpu.cpp`, around 332 and 441). Normal FISTP order is store first, then FPOP (`source/emulation/cpu/common/common_fpu.cpp`, around 1356).

Consequently, replacing the broad uncached Wasm helper with a Wasm f64/i64 conversion would not be semantic preservation: it would newly own x87 rounding control, NaN/Inf/overflow and ext80 behavior as well as destination-write fault ordering. FQF1/FQF2 prove the NormalCPU/generated-helper fault boundary, not a new inline implementation.

## Narrow design considered, and why it is not opened

The only plausible narrow design is an adjacent FILD m64 -> FISTP m64 pair: after a successful direct FILD read, retain the original i64 in private Wasm-local state; on the immediately following FISTP use the existing checked b64 write, and commit FPOP only after that write succeeds. Any read miss, helper call, block boundary, branch/redecode, non-pair, or destination fault must fall through to the existing helper. FQ1's compile-order pair detection (`wasm/jitWasmCodeGen.cpp`, around 14842 and 15391) is machinery for observing such pairs, not proof that they occur in the scene.

Because no nonzero pair admission is directly quantified, this narrow design cannot be assigned a production benefit. The historical exact-i64 pass-through observation also supplies no accepted gain. Opening a private build/cache/replay/FPS card would therefore be speculative and is rejected.

## Decision and reopening gate

**REJECTED before implementation:** no FISTP source, artifact, cache or browser route changed. The completed FQ1 broad-hotness census remains valid, but does not authorize an inline candidate.

To reopen only this narrow pair design, first expose the existing FQ1 per-tuple pair counts for a visible Present interval without rebuilding it and directly demonstrate nonzero, material same/different pair coverage. Then a new isolated candidate must prove: values `-2^63,-1,0,1,2^63-1` across all four rounding controls; source and destination protected-fault rows with saved EIP/handler/top/tag/guard; EA16/EA32, segment-base and page-cross addresses; SMC post-store FPOP/redecode; ticket clearing over helper, branch, block split and redecode; and non-pair ext80 NaN/Inf/overflow helper fallback. Only after those gates may the normal cache-OFF integrity -> record/replay -> visible 30-second A-B-A performance path open.
