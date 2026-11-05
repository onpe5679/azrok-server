# 293 — typed direct-tail `nextOp` repair: render restored, performance rejected

> **SUPERSEDED in part by 351.** The R2 performance rejection remains
> verified. The earlier assertion that the loader compared live
> `nextOp:pfnJitCode` offsets was not true of the retained source; 351 adds
> that comparison and records the correction.

## Status

**VERIFIED static / fixture / build / browser / A-B-A: REJECTED for
performance.** The corrected typed direct-tail artifact renders a complete
visible 1024x768 PatHouse and preserves the pair replay contract, but it is
materially slower than the accepted ABI2 cache. It is not a default/runtime
candidate.

## Direct-state repair and fail-closed admission

The store-sunk typed success arm had removed the legacy terminal
`helpers.fn_6` call, leaving `CPU::nextOp` stale. The repaired arm now stores
the publication-checked target relocation slot 0 into `CPU::nextOp` (offset
740) immediately before its typed `return_call`. This avoids re-entering the
decoder while preserving the original state transition.

**VERIFIED static:** slot 0 is the target block-start `DecodedOp*` only when
the target has at least one relocation slot. A subsequent audit found 757 of
the original 3,472 tails targeted `relocCount=0` blocks; their slot 0 is a
publication token, not an op pointer. The pipeline therefore now rejects such
targets from typed direct-tail admission and leaves their original 8-GP-store
+ `fn_6` fallback unchanged. This gate is deliberately before marker
allocation, so no accidental loader patch can make the path live.

The candidate manifest additionally carries `runtimeThreadedTail` and the
PatHouse page rejects replay unless its live `CPU::nextOp` and
`DecodedOp::pfnJitCode` offsets are exactly `740:12` with two publication
tokens. This is independent from generic-indirect ABI declarations.

## Offline regressions

**VERIFIED:** regenerated six-entry fixture and loader/page regressions pass.
The fixture proves all of the following in one emitted typed edge:

- success calls no `fn_6`, writes EIP `0x2000` and `nextOp=0x20000`, preserves
  all eight architectural GP words, and returns target EDI `0x4427`;
- uninstalled, invalidated, typed-unpublished, typed-mismatched, bailout,
  yield, and depth guards retain the original committing `fn_6` fallback;
- partial/wrong-base GP-store shapes remain fallback; and
- a zero-reloc target is not admitted and executes the helper fallback.

The exact pipeline output is
`azrok-jit-grouped-threadedtailabi2-nextopfix-r2.zip`, SHA-256
`11E76D21108404C6DEF6510602E14F66B4834FE61393D511C4E8449B2BF64543`.
It has 147 groups, 34,322 entries, 2,715 typed direct tails, and 21,720
patch operands. A manifest audit found zero patch target with
`relocCount=0`, exactly matching `2,715 * 8`.

The earlier R1 output is retained only as a rejected intermediate: it omitted
the zero-reloc admission gate and was never loaded in a browser.

## Browser render integrity

**VERIFIED dynamic/browser:** R2 reported pair replay registration with
147 groups, 34,322 entries, 21,720 patches, and live threaded-tail ABI
`740:12`. After the normal startup pulse and the visible saved-character
connect action, it rendered the loading scene and then the complete PatHouse
3D room (pet, room geometry, HUD and furniture) at CSS 1024x768. The former
black-frame regression did not recur.

## Visible 30-second A-B-A

No cache generation/build process was active during samples. Each leg used
the visible loaded PatHouse room, direct page-realm `D3D9WebDebug.presents`,
and the strict 30-second control.

| leg | cache | result |
| --- | --- | --- |
| A1 | R2 typed direct-tail | 901 / 30.001 s = **30.03 FPS** |
| B | accepted `boxedwine.upstreamjit64fn6inlineabi2` | 1,500 / 30.001 s = **50.00 FPS** |
| A2 | R2 typed direct-tail | 932 / 30.001 s = **31.07 FPS** |

The two adjacent candidate effects are -39.94% and -37.86%, far outside the
project's +/-3% noise band. Thus the state repair is correctness-accepted,
but the typed direct-tail implementation is decisively performance-rejected.
Keep the accepted ABI2 runtime/cache unchanged; do not spend a further A-B
cycle on R2.

## Next

Return to the accepted stem and move to a different measured guest-worker CPU
candidate. The queued runtime-lazy Z/NZ Wasm inlining remains blocked behind
the separately inconclusive parity A-B-A; this rejected tail path must not be
mixed into that experiment.
