# 418 -- INT 0x9A joined-census: existing-route static audit

Date: 2026-07-26  
Status: **VERIFIED static route audit; joined dynamic measurement NOT YET MADE.**

## Relationship to the logical-composite Amdahl proposal

The proposed denominator check was already closed before the logical-composite
fixture work in `407`.  `401`'s 11.29% is `Int9A / fn_8` entries in EOC1,
whereas `402`/`405` are separate condition-helper processes and epochs.
The reproducible cross-run entry-rate proxy was only `1,021.35/s / 311,817.45/s
= 0.32755%`; it is **not** a worker-time or frame-time fraction.  Therefore it
could not authorize a pre-fixture performance rejection.  The subsequently
measured logical-composite32 deployment is independently closed as rejected in
`417`; this audit does not reopen it.

## Existing INT and bridge targets are separate (VERIFIED)

The current Emscripten targets are distinct:

| Target | Build directory | Compile macro |
| --- | --- | --- |
| EOC1 | `Build/EOC1` | `BOXEDWINE_WASM_JIT_EMULATE_OPCODE_CENSUS` |
| `azrokMultiThreadedJitAudioO3IntCensus` | `Build/AzrokMultiThreadedJitAudioO3IntCensus1` | `BOXEDWINE_D3D9WEB_INT_CENSUS` |
| `azrokMultiThreadedJitAudioO3BridgeProfile` | `Build/AzrokMultiThreadedJitAudioO3BridgeProfile5` | `BOXEDWINE_D3D9WEB_BRIDGE_PROFILE` |

EOC1 carries only its own mutex-protected cumulative opcode snapshot.  Its
`fn_8` reader can be sampled at arbitrary page times, not at a D3D Present
boundary.  The other two target flags at
`project/emscripten/makefile:477-495` never compile together, and neither link
export list exposes an INT/bridge census ABI getter or snapshot-copy function.
The current Azrok page likewise has no INT/bridge census URL switch, required
export set, or reader.  Thus no existing artifact can supply the `401` joined
record through CDP or a page snapshot, and loading old targets cannot
manufacture a missing counter or common epoch.

## Same nominal cadence is not a join key (VERIFIED)

`IntCensus` is a `thread_local` accumulator.  On the generic Present route it
increments and logs/resets internally when `presents == 120`
(`source/opengl/d3d9web.cpp:750-793`).  It publishes only `klog_fmt` text.

`BridgeFrameProfile` is another `thread_local` accumulator.  Its Present
clock begins by initializing `lastPresentMs`, then subsequent Presents advance
`frames`; it logs/resets at `frames == 120`
(`d3d9web.cpp:850-917`).  Its first observed Present is initialization rather
than a frame increment.  The two windows therefore have no shared sequence,
sealed record, mutex, snapshot interface, or proof that their independently
emitted 120-Present lines cover identical commands.  Joining nearby log lines
would be an inference and fails the requirement in `401`.

The counters themselves are useful inputs: INT records index calls/bytes,
generic opcodes, batch and pending state (`d3d9web.cpp:248-269,458-792`);
bridge records per-index calls/callMicros, worker kernel/wall deltas and
main-thread wait partitions (`d3d9web.cpp:344-372,801-917`).  But no current
copy export exists for either structure.

## Async-ring completion is a further distinct boundary (VERIFIED)

The accepted-equivalent D3D9Web route has `BOXEDWINE_D3D9WEB_ASYNC_RING`.
Present-side `flushBatch(11)` submits an asynchronous ring slot and returns
success before the JavaScript dispatch is known complete
(`d3d9web.cpp:128-244,450-473`).  Existing INT increments after that guest-side
submission (`d3d9web.cpp:750-793`), and existing bridge timing is also taken
on the guest call tail (`d3d9web.cpp:850-917`).  Neither is proof of a
completed JS Present.

The JavaScript runtime increments `D3D9WebDebug.presents` while processing the
actual `COMMAND.PRESENT` (`tools/boxedwine_local/web_backend/host/d3d9web-runtime.js:167-185`),
but it has no separate diagnostic binding to the C++ async-slot sequence.
However, `submitAsyncPresentBatch` marks the slot `COMPLETED` only after its
main-thread callback returns from `runtime.dispatchBatch`, and the callback
stores a non-OK result on order/runtime/dispatch errors.  A private reader may
therefore call a window **completed dispatch** only when the exact terminal
slot sequence has been reaped with `result == D3D9WEB_OK`; it must not infer
completion from `D3D9WebDebug.presents`, nor call this GPU completion.

## Minimal private diagnostic design (NOT YET IMPLEMENTED)

Create one new cache-OFF-only private target whose single macro owns the EOC,
INT and bridge data in a **single shared 120-submit epoch**.  At one ordered
guest-side boundary it must wait until the final exact async sequence is
reaped with an OK result, then seal a fixed-layout record under a mutex and
increment a monotonic sequence.  A main-thread export copies only that sealed
record; it must never read a worker `thread_local` accumulator directly.

The ABI must include: sequence; exact submit count; EOC total/invalid and
Int9A delta; all six index call/byte pairs; generic opcode/guest-batch/pending
partitions; all six bridge call/callMicro pairs; bridge wall/kernel time;
main-roundtrip/wait and reason partitions; and explicit validity/partition
status.  It must reject an owner/TID change, duplicate/missing sequence,
invalid index/tag, a non-OK guest result, or incomplete carry-over.

The exact `ASYNC_SLOT_COMPLETED`/result/sequence reaping check is the
main-thread completion acknowledgement; it must prove 120 consecutive
sequences with no gap, reorder, or error.  The page must not merge it with
`D3D9WebDebug.presents`.  It must require the exact private stem and
cache-OFF/no-record/no-replay/no-capture mode, ABI/layout agreement, a new
sealed sequence, and every accounting equation before exposing a read.  Any
mode mix, sequence gap, missing export, stale layout or partition mismatch
rejects before data is used.

This is a diagnostic only.  Visible PatHouse/direct Present proves integrity,
not FPS; cache generation, replay, and performance comparison remain
forbidden.  A CPU-time ranking remains **NOT VERIFIED** unless a later
same-worker-TID/same-epoch CPU sample is added; `callMicros` is synchronous
wall residence, not CPU-exclusive cost.

## Decision

**VERIFIED:** existing INT and bridge artifacts cannot answer the open
question.  The next authorized work is the isolated private joined-census
implementation followed by static checks, build/served-byte proof and one
cache-OFF visible 120-Present **completed-dispatch** read.  No GPU-completion,
direct INT helper or FPS claim is open.
