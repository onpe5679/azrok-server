# 425. INT 0x9A direct helper: production async per-terminal route-mask runtime

Date: 2026-07-26  
Status: **VERIFIED private build/cache-OFF runtime; P1 all-route row NOT VERIFIED**

## Scope

424 correctly left the index-2..5 async ordering row open: I9F1 is a synchronous `__TEST` fixture and 420's aggregate counters cannot associate a route with the same terminal async slot. This card adds only a separately named production telemetry build. It does not add a direct INT helper, change the accepted stem, create a cache, or collect an FPS sample.

```text
make -j1 azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeInt9ASequenceCensus
Build/AzrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeInt9ASequenceCensus1
boxedwine.upstreamjit64fn6inlineabi2int9asequencecensus1
```

Its macro is `BOXEDWINE_WASM_JIT_INT9A_SEQUENCE_CENSUS`. The source rejects `__TEST`, the joined census and I9F1 direct fixture, and requires exactly MT Wasm-JIT plus D3D9Web async-ring. The page accepts only `int9aSequenceCensus=1`, this stem and `jitCacheUrl=off`; record, replay, capture, audio suppression and all other private diagnostic modes reject before guest execution.

## Per-slot association contract

**VERIFIED static and build.** `AsyncBatchSlot` has a private `routeMask` only in this target. Successful index 3/4/5 appends set the pending bit; a terminal Present (`index 2`, opcode 11) sets bit 2 inside `submitAsyncPresentBatch`, copies the complete mask to that exact slot, and resets the pending mask. Any non-Present synchronous drain resets the pending mask, so prior routes cannot be attributed to a later Present.

`reapNextAsyncBatch` reads that slot's mask before freeing the slot. The snapshot seals only after 120 contiguous terminal submissions have been drained, so a qualifying count is evidence of the callback-written `COMPLETED` state, not merely publication. Its 15 U64 ABI is ABI/words/epoch/state; submitted/first/last/reaped sequence/reaped slot count; then required mask, qualifying count/first/last/mask and terminal opcode. The required mask is `60` (`(1<<2)|(1<<3)|(1<<4)|(1<<5)`).

The page reader requires ABI 1, 15 words, state 1, 120 contiguous submissions/reaps, terminal opcode 11 and mask 60; if any qualifying record exists it additionally requires the exact required bits. A zero qualifying count is a valid *coverage-negative* snapshot, never a P1 pass.

## Build, staging and served identity

**VERIFIED.** A serial build succeeded (only existing compiler warnings), and `make -q` then returned 0. The response-file link path includes this build directory. Generated JS exports exactly the three reader functions `GetAbiVersion`, `GetSnapshotBytes`, and `CopySnapshot`. The Wasm magic and generated JS parse passed. Wasm was staged first and JS second under a new asset name. Disk, stage and HTTP bytes agree:

```text
JS   A10F1665106F84972558EEB3A125398270C3EA848F6AD51686A15EA3899E0D21
Wasm E2671CA7999B5CBF052ACFD5CB1D809356E84FF39B01663EB91BF241E47AA8E3
```

## Cache-OFF sole-page runtime

**VERIFIED.** The existing single CDP page was navigated directly to the exact private URL with no new tab. It used only `runtimeStem=boxedwine.upstreamjit64fn6inlineabi2int9asequencecensus1`, `int9aSequenceCensus=1`, and `jitCacheUrl=off`. The page was `document.visibilityState=visible`; CSS canvas reached 1024x768. The run control and existing page input-pulse control were activated by CDP pointer press/release. This run occurred after the user moved Edge to primary DISPLAY1, but no FPS value is used or reported by this card.

Before the first seal the page-owned reader correctly rejected the all-zero record. After scene entry it directly observed 6,849 direct Presents and async debug callbacks 6,852 with errors/gaps/reorders all zero. The sealed epoch-65 record was read directly from the module:

```text
[1,15,65,1,120,7681,7800,7800,120,60,0,0,0,0,11]
```

This proves 120 contiguous Present submissions, exact callback completion and reaping through sequence 7800 with no async failure. It also proves that none of those 120 terminal slots contained all route bits 2/3/4/5: `qualifying=0`. It is consistent with 420's independent PatHouse aggregate index-5 count of zero. Neither result implies index 5 is globally dead.

## Decision

The production per-terminal mechanism is now verified, but the required all-route P1 witness is still absent. Therefore the INT 0x9A direct helper remains prohibited from production/cache/replay/FPS paths. A future dedicated private guest-batch fixture or real game flow that yields a reaped mask 60 is required; synthetic I9F1 route calls and aggregate-count inference remain invalid evidence.
