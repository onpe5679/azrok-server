# 399 -- Dual-entry store-sinking-only: no independent candidate

Date: 2026-07-25  
Status: **VERIFIED static/artifact audit; REJECTED before implementation or measurement**.

## Decision boundary

After the completed MOVSD, MOVSB and FISTP cards, the requested separate
`store-sinking-only` follow-up was checked without reopening the rejected R2
direct-tail candidate.  It is not an independently representable optimization
in the retained implementation, so no build, record, cache, browser render or
FPS sample is authorized.

R2's directly measured whole-candidate result remains closed: 30.03 / 50.00
/ 31.07 FPS, with adjacent effects -39.94% / -37.86% (293).  Repeating that
A-B-A would be duplicate measurement and is prohibited.

## Why no separate store-sinking mode exists

**VERIFIED static:** the retained `ThreadedBodyAbi` target is
`Build/AzrokMultiThreadedJitAudioO3AsyncRingThreadedTailAbi2` and forcibly
enables both `BOXEDWINE_WASM_JIT_THREADED_BODY_ABI` and
`BOXEDWINE_WASM_JIT_THREADED_TAIL_ABI`
(`project/emscripten/makefile:325-330`).  It is therefore the R2 combined
direct-tail family, not a body-only/store-only target.

The exact eight-GP-store removal is structurally conditional on a direct tail:
the pipeline creates eligible edges/targets only when `options.directCalls`
is active (`boxedwine-wasm-jit-cache-pipeline.mjs:2086-2126`), and only that
path recognizes the strict eight-store suffix, trims it, and appends the
guarded typed `return_call` tail (`:1821-1887`).  With `directCalls=false`,
the target map is empty and no rewrite runs: zero sunk tails and zero patches.

That is semantically necessary, not a missed flag.  A body enters with all GP
locals dirty (`jitWasmCodeGen.cpp:8114-8121`); an ordinary dispatcher exit
synchronizes them and calls `fn_6` (`:14381-14390`), and the cold wrapper
returns the tuple to CPU memory (`:8039-8071`).  The direct-return/next1/next2
paths may instead carry an unsynchronized tuple (`:8179-8196`, `:14238-14265`,
`:14416-14505`).  Removing the wrapper's stores without that publication-safe
tail would erase the only architectural commit; retaining them means no
store-sinking benefit.

Current identity rules make the same conclusion fail closed.  The pipeline
still declares `threadedGpAbi.storeSinking:true` even for `direct=false`
(`boxedwine-wasm-jit-cache-pipeline.mjs:3390-3404`); the loader requires it
(`boxedwine-shell.js:518-534`) while only allowing no direct-tail metadata for
the no-direct shape (`:538-568`).  The runtime GP ABI getter is tied to the
TAIL macro (`jitWasmCodeGen.cpp:4543-4552`).  Thus a no-direct pair cache cannot
truthfully advertise a standalone store-sinking contract.

## Existing cost evidence remains unavailable

The 757 zero-reloc fallback tails (the old `5,299 = 757 x 7` static number;
R2's repaired form is 6,056 operands) cannot supply an independent rationale.
Their 42,392 retained writeback bytes are static accounting only (294).  The
private four-counter discriminator exists, but its fixed 34,322-entry raw is
absent; the available 34,226-entry record is correctly rejected before cache,
replay or runtime counters (308, 351).  Consequently helper-fallback time
versus wrapper overhead is **NOT VERIFIED**, and must not be inferred from the
whole-R2 slowdown.

## Reopening condition

Only a genuinely new private design could reopen this subject: a
`direct=false`, patch=0, store-sunk=0 manifest/loader identity that reports
`storeSinking:false`; explicit cross-rejection of direct-tail metadata and GP
ABI; and provenance fixtures proving exactly one CPU commit across ordinary
block exit, direct return, fault, bailout, SMC and yield.  It would then need
its own cache-OFF render, fresh record/replay and A-B-A path.  That is a new
candidate, not a repair or remeasurement of R2.
