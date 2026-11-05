# 419 -- INT 0x9A joined-census: private source and page route

Date: 2026-07-26  
Status: **VERIFIED static source/page route; build, served asset and browser measurement NOT YET MADE.**

## Scope

This is a new diagnostic-only route for the gap closed in `418`.  It does not
modify the accepted runtime stem, its cache, record/replay behavior, or any
performance candidate.  No FPS claim is permitted from this asset.

## Worker-side joined record (VERIFIED static)

Private macro `BOXEDWINE_WASM_JIT_INT9A_JOINED_CENSUS` is rejected at compile
time unless it is an isolated production multi-threaded, async-ring Wasm-JIT
build.  It also excludes the existing EOC and other private census/candidate
macros (`source/emulation/cpu/wasm/jitWasmCodeGen.cpp:179-181`).

The generated `fn_8` path writes the decoded opcode tag at the established
EOC-equivalent placement, then calls only the private
`d3d9WebInt9AJoinedCensusRecordGenerated` hook before NormalCPU executes the
instruction (`jitWasmCodeGen.cpp:5616-5621,15045-15054`).  The hook maintains
per-worker totals for fn_8, Int9A and invalid tags.  Once D3D9Web receives its
first call, that worker CPU becomes the window owner; a different CPU on that
worker marks the record invalid rather than blending counts.

`d3d9web.cpp` accumulates one owner-local window of:

- exact fn_8 total/Int9A/invalid deltas;
- index 0--5 call and byte counts;
- per-index D3D call wall residence;
- generic call/byte/opcode counts; and
- batch and guest-batch counters.

At 120 terminal Present submissions it synchronously drains the async ring
for this diagnostic only.  Seal is allowed only if the first/last submitted
sequence span exactly 120, the final sequence was reaped, and every slot
returned `D3D9WEB_OK`.  `ASYNC_SLOT_COMPLETED` is written after the
main-thread `runtime.dispatchBatch` returns, so the result is a completed JS
dispatch acknowledgement, not GPU completion.  Owner, sequence or async
error violations produce a non-valid snapshot state.

The sealed 68-U64 ABI-1 record is mutex-copied through three private exports:
`d3d9WebInt9AJoinedCensusGetAbiVersion`, `...GetSnapshotBytes`, and
`...CopySnapshot`.  The page cannot read the worker `thread_local` state.

## Private artifact/page route (VERIFIED static)

New target:

```text
azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeInt9AJoinedCensus
Build/AzrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeInt9AJoinedCensus1
```

It uses `-O3`, the accepted ABI2 legacy exports, async ring, hot WIS cache,
private macro and the three snapshot exports.  It is included in the existing
response-file linker path, avoiding the Windows command-line length failure
that affected prior private targets.

The page accepts only:

```text
runtimeStem=boxedwine.upstreamjit64fn6inlineabi2int9ajoinedcensus1
int9aJoinedCensus=1
jitCacheUrl=off
```

It rejects record, replay, Present capture, sound A/B and every other private
diagnostic/candidate mode.  On runtime initialization it requires ABI 1,
544 bytes/68 U64, all three exports, and publishes a reader only after the
private module is recognized.  Each reader invocation rejects unless the
sealed record is valid, epoch is nonzero, submission count is 120, sequences
are contiguous and reaped, invalid fn_8 tags are zero, index/bridge calls
reconcile one-for-one, and generic calls reconcile with the 25-opcode
partition.

## Static checks performed

- The page inline JavaScript parses with Node `--check` from UTF-8 source.
- `em++ -fsyntax-only` under the exact private macro/async-ring flags passes
  for `d3d9web.cpp` and `jitWasmCodeGen.cpp`.  Only existing Emscripten/SIMDe
  deprecation warnings were emitted.
- `make -n` resolves the private target, propagates the macro and selected
  exports, and selects the response-file link branch.  GNU make executes its
  `$(file ...)` response-file write even under `-n`; because the new Build
  directory is intentionally not created while user After Effects is present,
  that dry-run stops at the expected missing-directory write.  This is not a
  build or a source failure.

## Deferred work

At audit time `AfterFX` PID 41948 exists (about 4.0 GiB working set), so no
compile, cache generation, served deployment or browser navigation was
started.  After the user resource hold is lifted: perform one low-priority
build, stage under the exact private stem, verify build-to-served JS/Wasm
hashes plus exports, then run one cache-OFF visible PatHouse completed-dispatch
snapshot.  Only a materially concentrated result can open a separate direct
INT semantic design; cache/replay/FPS remain prohibited now.
