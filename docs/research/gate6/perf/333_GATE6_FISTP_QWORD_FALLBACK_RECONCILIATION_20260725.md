# Gate 6 FISTP qword fallback reconciliation (2026-07-25)

Status: **VERIFIED static/dynamic-evidence audit / candidate NOT OPENED**

## Question

EOC1 recorded `FISTP_QWORD_INTEGER` 783,192 times in 22.337 seconds
(11.24% of `fn_8`).  This audit determines whether that count authorizes a
new generated-Wasm optimization card.

## Direct evidence

- **VERIFIED dynamic:** EOC1 writes opcode tag 631 immediately before
  `wasmHelper_emulateSingleOp`; the helper then invokes `jitRunSingleOp()`
  once.  Thus `783,192` is an exact cache-OFF canonical-fallback *entry*
  count (invalid tag 0), not a completion count, CPU-time measurement,
  Present-correlated rate, module/EIP attribution, or FISTP operand-pair
  census.  Its mutex snapshot records none of EA shape/segment base, x87 CW,
  TOP/tag/cache state, page-fault/unwind outcome, or phase.
- **VERIFIED static:** Wasm JitFPU already emits the cached-ST0 arm: RC-aware
  rounding, NaN/range handling and 64-bit store followed by FPOP.  Only an
  uncached ST0 takes the base one-op emulation arm
  (`source/emulation/cpu/wasm/jitFPU.cpp:1220-1236`, `9645-9695`).
- **VERIFIED static:** `FPU::FLD_I64` deliberately leaves the register
  uncached to preserve exact m64 round trips
  (`source/emulation/cpu/common/fpu.cpp:332-338`).  The ordinary operation is
  `FST_I64`/destination write followed by FPOP; a write fault must therefore
  retain the pre-pop FPU state (`common_fpu.cpp:1356-1364`).  The fallback
  boundary also synchronizes EIP/dirty state and handles SMC/bailout before
  returning to generated execution.
- **VERIFIED prior direct measurement:** The historical hot FISTP samples in
  261 belonged to Wine `win32u`/`wineserver`, not Acknex, and its narrow
  exact-i64 pass-through was implemented, showed no gain, and was reverted.
  That old sample cannot attribute the newer EOC1 count to the same game
  sites, but it closes the same uncached exact-i64 specialization rather than
  authorizing a duplicate retry.

## Decision

**REJECTED as a new optimization candidate.**  No FISTP implementation,
artifact, replay/cache generation, or FPS A-B-A was started.  This preserves
the accepted stem and avoids turning an opcode-only total into an inferred
performance result.

## Conditional future evidence (not queued)

Reopen only if a separately justified private cache-OFF FQ1 diagnostic first
proves an Acknex-relevant exact `FILD m64 -> FISTP m64` pair with a shared
epoch/Present record, partitions entry/return/unwind by EA16/EA32,
segment/base/page-crossing, CW rounding, cached state and completion/pop, and
does not use untrusted post-only state after a fault.  Before any candidate,
NormalCPU-to-Wasm differential fixtures must cover RC all four modes,
NaN/Inf/overflow, destination write-PF with no pop, same/different m64
round-trip, SMC and mixed-block EIP.  Until then the generic fallback remains
the fail-closed path.
