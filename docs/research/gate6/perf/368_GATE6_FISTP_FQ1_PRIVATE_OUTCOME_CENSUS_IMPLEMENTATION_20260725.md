# 368 -- FISTP FQ1 private outcome-census implementation (2026-07-25)

Status: **VERIFIED static / implementation stage; runtime result is recorded in 369**

## Scope and isolation

FQ1 is a new production, private cache-OFF diagnostic only. It is distinct from historical `fistpprofile`/`fistpsites`, FQF1 and FQF2. The target is `Build/FQ1` with `BOXEDWINE_WASM_JIT_FISTP_QWORD_CENSUS`; source-level gates reject test, direct-dispatch, FQF1/FQF2, all active census/profile cards and accepted runtime. Its private stem is `boxedwine.upstreamjit64fn6inlineabi2fistpqwordcensus1`.

The page hook requires exactly `fistpQwordCensus=1`, `jitCacheUrl=off`, that stem, and absence of record, Present capture, replay and every other diagnostic URL flag. It is installed both before normal startup and from `prepareAzrokJitRecord()`. Its XOR ABI gate rejects an FQ1 URL with a non-FQ1 module and an FQ1 module without the URL request. No asset has yet been built, staged, served, or loaded by a browser.

## Outcome boundary

**VERIFIED static:** generated `emulateSingleOp()` overwrites the FQ1 ticket on every generic helper call. For FISTP-qword it records the actual `calculateEaa()` linear destination, EA16, source segment and compile-order immediate FILD-qword pair relation; the helper completes runtime segment route, page-cross, RC and cached-ST0 context before the NormalCPU call.

`CPU::runNextSingleOp()` copies the validated ticket immediately before `o.pfn`, records normal-pop versus normal-no-pop immediately after return, and records fault delivery inside the same catch. It does not infer fault outcome from later helper return or post-handler FPU state. This is the operation-local boundary proven separately by FQF2 (367).

The fixed snapshot is 5,188 U64 / 41,504 B:

```text
fn8Total, otherOpcode, invalidTag, invalidMetadata,
context[segment 6][EA16 2][route 3][page-cross 2][RC 4]
       [cached 2][pair 3][outcome 3]
```

The reader requires `fn8Total = otherOpcode + invalidTag + invalidMetadata + sum(context)`, outcome partition equality, and `invalidTag=invalidMetadata=0`. `cached-ST0` remains a recorded two-way context axis, not a zero-only contract: source proves its value is sampled at the helper boundary, but does not make it a standalone dispatch-route witness. The initial zero-only page assertion was removed before the runtime result in 369 after direct cache-OFF data observed valid cached lanes while every partition equation held.

## P0 found and repaired before build result

The first static audit found that an FQ1 protected-destination fault could return through generic `emitBailoutCheck()` and rewrite the delivered handler EIP to the generated successor. Before allowing a private build result, the FQ1 ticket catch was changed to set private `wasmJitBailout=2`; generated code consumes only that marker, clears active-block/bailout and returns before generic successor-EIP rewrite. This is structurally the FQF2-proven handler-preservation route, but FQ1 build/runtime proof remains required.

The CPU-side exclusion list was also made identical to codegen's full diagnostic exclusion list. `verify-fistp-qword-census-loader-gate.mjs` passes after these repairs. The interrupted first build is invalid and must not be used; the replacement private build is still in progress.

## Next gate

The clean build/staging/runtime gate is completed in 369. This remains a diagnostic only; it does not authorize cache, replay or performance work.
