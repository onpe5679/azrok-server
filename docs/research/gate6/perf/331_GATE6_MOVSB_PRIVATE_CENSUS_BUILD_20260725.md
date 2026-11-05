# 331 MOVSB private reason×shape census build

## Status

**VERIFIED implementation/build/static artifact and private staging;
runtime/browser NOT VERIFIED.** MBS1 is available only under its dedicated
private stem, not the accepted stem. No browser launch, cache, record/replay,
or FPS sample was performed.

## Contract and isolation

The new `BOXEDWINE_WASM_JIT_MOVSB_SEGMENTED_REP_CENSUS` records generated
`fn_8` fallback only. It stores all eight compile-time shape combinations
`[REP, EA16, sticky-segment]`; for EA32+REP+sticky shape 5 it additionally
records source segment, ES/source sticky cause, live zero-base pair, DF,
first-run/warm state, and pre-interpreter ECX bins/overflow bytes. Snapshot
layout is 558 U64 / 4,464 bytes:

```
header[4] + shape[8] + context[6][3][4][2][2] + ecx[256] + overflow[2]
```

The record and copy use the same mutex. The page requires an exact private
stem, `jitCacheUrl=off`, ABI 1, the four exports, exact word/byte sizes, and
partitions `fn8 = other + invalid + sum(shape)`,
`shape5 = invalidMetadata + contexts`, and
`contexts = ecxBins + overflowCalls`. Any invalid metadata also rejects the
snapshot, so it cannot be used as optimization coverage.

C++ rejects MBS composition with EOC/MOC/MOC3/profile, helper/fetch/condition/
runtime counters, threaded-tail, MRG, and runtime-ZNZ macros. The page rejects
the corresponding URL-mode mixture. Accepted ABI2 sources and assets have no
MBS binding.

## Build and static results

The isolated target
`azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeMovsbSegmentedRepCensus`
built as single-job nice-19 `Build/MBS1` with `-O3 -msimd128 -pthread`; only
the pre-existing compiler warnings and Emscripten's standard pthread/memory
growth warning occurred. No compiler/linker error or undefined symbol appears
in the build log.

`WebAssembly.validate` accepts `boxedwine.wasm` (3,049,423 bytes, SHA-256
`3D94AE28B414453EF212CA1D41429612238EEED8BFC998052D53F8066238DCA6`).
Its JS SHA-256 is
`3E509825B4AF27E7E1C7A1434A6B2B894BDFB3F6DAB5A48D9E16B91960FE263F`.
The Wasm export count is 58: accepted legacy ABI2's 54 plus exactly the four
MBS snapshot APIs. Generated JS contains all four MBS bindings and no pair
register-thread ABI or prior census binding.

The dedicated Node loader-gate and isolated page-hook parse pass. These are
static/build gates only; they do not prove the browser pthread/broker runtime,
visible PatHouse integrity, or any MOVSB coverage.

## Private serving stage

Only `boxedwine.js` and `boxedwine.wasm` were copied under the unique served
names `boxedwine.upstreamjit64fn6inlineabi2movsbsegcensus1.{js,wasm}`. Their
source-to-served SHA-256 values match exactly, the staged Wasm again validates,
and localhost:8765 returns 200 for both exact files. The common shell/CSS are
byte-identical to the already served common files and were not replaced. The
accepted ABI2 asset names remain unchanged, and no MBS request/browser
transcript exists. This is private test availability only, not a runtime or
rendering result.

## Next gate

Do not use MBS1 until browser execution is permitted. Then run one tab,
visible 1024x768, cache-OFF, no record/replay/present capture, with
URL/runtime/layout gates before guest start. Require full PatHouse and zero
ring errors, then take named coverage snapshots only. A nonzero
invalid-metadata read or any partition failure is hard rejection. No
optimization candidate, cache, or FPS A-B-A opens from this build alone.
