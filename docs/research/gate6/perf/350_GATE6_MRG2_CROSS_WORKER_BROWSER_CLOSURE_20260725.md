# 350 MRG2 cross-worker browser closure

Date: 2026-07-25  
Scope: private MRG2 correctness fixture and existing MRGF5 entry-21 control
only. The accepted runtime stem, cache ZIP, replay path, and FPS candidate were
not changed.

## Result

**VERIFIED.** The MRG2 parent-published two-slot runtime group was preloaded
and executed by a different guest worker in the browser. The child executed
the selected EA32, REP, runtime-zero `MOVSD` generated RAM-store arm exactly
once. This closes the cross-worker table/broker witness required by 347.

Direct CDP `Runtime.evaluate` of the only page target's `textarea#output`,
with cache disabled and no new tab, returned:

```text
Running 1 Test tests with 1 threads starting at 21
[WASM JIT] first JIT block executed, tableIdx: 8187
[WASM JIT] direct chain ABI depthOffset=1660 bailoutOffset=132
MRG2 cross-worker zero-arm parent=0 child=1
Test MT WASM JIT scheduleThread preload ... OK
0 tests FAILED in 0s
```

The fixture's non-printing assertions additionally require the child to finish
with EAX=0, ECX=0, ESI/EDI advanced by four, preserved flags, and the exact
copied destination dword. It retains the pre-existing broker assertions: one
preload before one run, one broker hit, no local compile, one selected physical
worker, and one grouped instance creation plus reuse.

## Root cause of 349 and control

**VERIFIED.** The original 349 pre-child barrier failure was not an MRG2 or
MOVSD failure. All 19 test C++-to-main relays still emitted the removed string
form `cmd: 'callHandler'`; three MRG2 test-only codegen relays used the same
form. The active Emscripten worker dispatcher accepts numeric `cmd: 9`, which
the production broker already used. The isolated mechanical repair changed
only those 22 test relays to `cmd: 9`; no handlers, payloads, or production
execution branch were changed. Static audit found P0=0/P1=0 and no remaining
legacy test relay.

Fresh MRGF5 entry 21 was the direct regression control after that repair:

```text
Running 1 Test tests with 1 threads starting at 21
[WASM JIT] first JIT block executed, tableIdx: 8187
[WASM JIT] direct chain ABI depthOffset=1660 bailoutOffset=132
Test MT WASM JIT scheduleThread preload ... OK
0 tests FAILED in 0s
```

Thus 349's matched MRGF5/MRG2 pre-child failure was correctly fail-closed at
the time, and is now attributed to the stale test transport encoding.

## Generated-store witness and parent warm correction

**VERIFIED static and dynamic.** MRG2 adds a private CPU-local counter only
under `BOXEDWINE_WASM_JIT_MOVSD_MRG_CROSS_WORKER_FIXTURE`. The increment is
emitted immediately before the `write()` RAM fast `i32.store`, gated by the
selected inline runtime-zero MOVSD body, EA32, REP, and 32-bit width. It cannot
count source reads, helper/CodePage writes, EA16, nonzero-base emulation, or
ordinary MOVSD.

The parent explicitly resets the counter and runs ECX=0, requiring zero store
events. The cloned child explicitly resets it and runs ECX=1, requiring one;
the parent remains zero after the child. The output pair `parent=0 child=1` is
therefore direct evidence of generated destination-store execution, excluding
the NormalCPU fallback explanation.

The first MRG2 browser pass exposed a test-expectation P0, not a runtime
failure: the MT chain limit is one, so the parent `CPU::run()` returns after
the first JIT block's E9 at the distinct successor NOP (EIP `+8`) rather than
running the following TestEnd. The predicate was corrected to require that
exact successor and EIP. Independent static review then found P0=0/P1=0.

## Artifact and serving gate

**VERIFIED.** The final forced MRG2 build used
`testMultiThreadedJitMovsdRuntimeZeroGuardCrossWorkerFixture`; it selects
`Build/MRG2`, test-JIT sources, the exclusive MRG2 macro, and the broker
pre-JS dependency. The final assets were:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `boxedwine.js` | 228,439 | `687BDD51BBF7C636C1661D4B28F5BAE6CDFEBB63E6D8BC874B883678DCF437E4` |
| `boxedwine.wasm` | 2,446,276 | `5D2B16BE7929B09E9C3BD9F20D88985AA67637A104288A34ACBA176C162C5D9F` |

The MRG2 served Wasm SHA-256 matched the disk artifact exactly and
`WebAssembly.validate` returned `true`. The regenerated JS contains zero
legacy `callHandler` relays and 26 numeric `cmd: 9` messages (the 22 repaired
test relays plus pre-existing production messages).

## Boundary

**VERIFIED closure:** MRGF4 DF0/DF1/helper SMC, MRGF5 EA16 helper SMC, and now
MRG2 cross-worker generated-store/broker execution are all browser witnesses.
The MOVSD runtime-zero correctness card is complete.

**NOT VERIFIED:** this is not a cache/replay or performance measurement, and
does not publish the private fixture or alter the accepted stem. Per the active
queue, resume the dual-entry register-threaded ABI browser gate and its A-B-A
performance decision next; do not mix parity or runtime-lazy Z/NZ work into
that candidate.
