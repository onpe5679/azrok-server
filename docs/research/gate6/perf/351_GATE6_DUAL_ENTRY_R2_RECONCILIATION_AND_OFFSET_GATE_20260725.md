# 351 Gate 6 dual-entry R2 reconciliation and runtime-offset loader gate

## Status

**VERIFIED static/filesystem/loader regression; no browser or performance
measurement.** This closes a continuation-state discrepancy without reopening
the rejected R2 candidate.

## Current artifact identity

The retained `azrokMultiThreadedJitAudioO3AsyncRingThreadedBodyAbi` make target
uses `Build/AzrokMultiThreadedJitAudioO3AsyncRingThreadedTailAbi2` and enables
both `BOXEDWINE_WASM_JIT_THREADED_BODY_ABI` and
`BOXEDWINE_WASM_JIT_THREADED_TAIL_ABI`. Its forced 25 July output is therefore
the same direct-tail family rejected by 293, not a separately declared
safe-store-sinking candidate. The preserved R2 archive remains
`azrok-jit-grouped-threadedtailabi2-nextopfix-r2.zip` (147 groups, 34,322
entries, 2,715 admitted tails and 21,720 patches).

Accordingly no cache-off render, record/replay, or A-B-A was run against this
target. Repeating 293 would violate the no-duplicate-measurement rule.

## Corrected loader claim

The retained loader previously checked the pair/GP ABI versions but did not
read and compare the live `CPU::nextOp` and `DecodedOp::pfnJitCode` getters.
This contradicted the historical wording in 293, although it does not alter
293's directly measured R2 performance rejection. Document 293 is superseded
only for that loader-gate assertion.

`boxedwine-shell.js` now rejects a paired direct-tail manifest unless:

- `source.directCalls` and `source.tailCalls` are matching booleans;
- a direct manifest has a complete `runtimeThreadedTail` contract whose pfn
  value agrees with `runtimePublication`;
- the two live runtime getters exactly equal the manifest `nextOp` and pfn
  offsets; and
- a no-direct pair manifest carries no direct-tail metadata.

The separate `verify-threaded-gp-loader-gate.mjs` regression now has 12 cases
and directly verifies a moved nextOp offset rejection, missing direct-tail
contract rejection, and a valid no-direct pair shape. It completed with
`{"valid":true,"cases":12,"exportedFunctionRows":46}`. No runtime asset was
published; the accepted ABI2 path is unchanged.

## R2 fallback-versus-wrapper accounting

The requested runtime frequency discriminator already exists as the private
`ThreadedTailCensus`: cold wrapper, typed body, admitted tail and exact
zero-reloc eight-store-plus-`fn_6` fallback counters, with the delta invariant
`typedBody == wrapper + admittedTail`. The exact R2 fallback scope is 757
source tails / 6,056 operands / 42,392 retained terminal-store bytes. The
older 5,299 number is a pre-repair seven-operand static count, not a runtime
site count.

This diagnostic remains **BLOCKED fail-closed**, not unimplemented. Its
canonical 34,322-module R2 raw archive is absent; the only fresh census raw
has 34,226 modules. The fixed 34,322/2,715/757/21,720 pipeline gate correctly
emits no cache. A replacement corpus or relaxed count would not quantify the
rejected R2 shape and is prohibited. Therefore helper fallback time versus
wrapper overhead remains NOT VERIFIED.

## Decision

R2 remains disabled and must not receive another browser/FPS leg. Parity and
runtime-lazy Z/NZ are already independently closed by 295 and 301, as
reconciled in 326. The next active correctness path is the separately scoped
MOVSD candidate progression after the completed MRG2 witness (350), beginning
with its isolated candidate build and cache-off render gate; it must not mix
with direct-tail R2 or its census.
