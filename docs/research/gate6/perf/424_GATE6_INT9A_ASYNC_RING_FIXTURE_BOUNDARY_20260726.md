# 424. INT 0x9A direct helper: asynchronous-ring fixture boundary

Date: 2026-07-26  
Status: **VERIFIED static boundary / NOT VERIFIED runtime**

## Finding

`Build/I9F1` cannot prove the remaining index-2..5 asynchronous ordering row, by design:

- its exact target flags in `project/emscripten/Makefile:118-121` include `__TEST`, MT Wasm JIT, D3D9Web and `BOXEDWINE_WASM_JIT_INT9A_DIRECT_FIXTURE`, but **not** `BOXEDWINE_D3D9WEB_ASYNC_RING`;
- it uses `shelltest.html`, not the served game shell/runtime route; and
- async submission exists only under `BOXEDWINE_D3D9WEB_ASYNC_RING && BOXEDWINE_MULTI_THREADED` in `source/opengl/d3d9web.cpp:183-377`.

Therefore forcing synthetic index-2..5 calls through I9F1 would exercise the synchronous test bridge or a missing runtime, not the production asynchronous order contract.  Such a result must not close P1.

## Current real-scene coverage is insufficient

**VERIFIED.** The already-closed cache-OFF production joined-census snapshot in 420 is the correct runtime topology and proves 120 terminal slots reaped after main-thread `dispatchBatch` acknowledgement.  Its epoch-63 index/bridge partition is `[0, 0, 17645, 119, 3427, 0]` for indices 0..5.  Thus this real PatHouse observation contains generic (2), direct upload (3), and draw-UP (4), but **no guest batch (5)**.

It cannot be used to infer index-5 semantics or same-terminal ordering.  The zero is a scene-coverage fact, not an assertion that index 5 is dead in every game path.

## Actual production ordering contract

**VERIFIED static.** `callD3D9Web` reads all three stack words and dispatches:

| index | Route | Async relevance |
|---:|---|---|
| 2 | `dispatchGeneric` | Generic opcode 11 (Present) batches then calls `flushBatch(11)`; async-ring builds submit a numbered present batch. |
| 3 | `enqueueDirectUpload` | Appends opcode-14 upload data to the pending batch. |
| 4 | `enqueueDirectDrawPrimitiveUP` | Appends opcode-10 draw data to the pending batch. |
| 5 | `enqueueGuestBatch` | Validates and appends only non-terminal batchable records. |

`flushBatch(11)` alone reaches `submitAsyncPresentBatch`; it assigns the next sequence, publishes the slot, schedules `MAIN_THREAD_ASYNC_EM_ASM`, and advances `asyncSubmittedSequence`.  The JS callback independently rejects a sequence gap/reorder and records result/state before reaping (`d3d9web.cpp:258-377`).  Non-present flush reasons synchronously drain first (`579-617`, `813-900`).

## Required next fixture shape

The remaining test must be a separately named, private, **async-ring enabled served-game route**, not an extension of I9F1's `shelltest` CPU suite.  It must:

1. retain the I9F1 direct-helper isolation and all 423 gates;
2. use the accepted async-ring/runtime-shell topology with a private fail-closed stem;
3. record an index bitmask at each terminal submission and retain it until that exact main-thread callback has reaped the matching sequence;
4. prove a material reaped terminal sequence containing generic (2), upload (3), draw-UP (4), guest batch (5), then Present (2/opcode 11), with zero sequence gaps/reorders/errors and matching terminal EAX/return state; and
5. remain cache-OFF/private until this P1 row closes.

No source target is created by this document.  Production direct-helper, cache/replay and FPS work remain prohibited.
