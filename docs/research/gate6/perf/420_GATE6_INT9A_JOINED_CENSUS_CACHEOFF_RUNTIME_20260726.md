# 420 -- Gate 6 INT 0x9A joined census: private build and cache-OFF runtime (2026-07-26)

## Status

**VERIFIED private diagnostic build, served-byte identity and cache-OFF runtime snapshot. This is not an INT optimization, replay/cache artifact, GPU-complete claim, or FPS measurement.**

419's resource hold ended only after direct recheck found `AfterFX=0`, about 135.9 GiB free physical memory, no compiler/linker process, four service ports listening and the human-owned watcher available. The first private build stopped before source compilation because the make environment did not resolve POSIX `grep`; adding the already-installed Git `usr\\bin` only to that build process restored the established 380 host-tool path. A second accidental same-target make tree was stopped before artifacts were accepted. The final build was one serial `-j1` target only; `make -q` subsequently reported it current.

## Correctness repairs before the accepted build

**VERIFIED:** Static review found that `int9AJoinedResetWindow()` saved the generated `fn_8` totals as start values but then zeroed the live totals. The second seal would consequently calculate zero/underflow deltas. The reset now restores all three live cumulative totals as well as their start coordinates; two later sealed epochs below directly exercise the repaired multi-window path.

**VERIFIED:** The page reader now rejects a zero owner word, and the source compile gate additionally requires Emscripten/Wasm-JIT/D3D9Web/MT/async-ring and rejects the known private profile/census/fixture/candidate macro families. An exact private syntax compile passes; the deliberate addition of `BOXEDWINE_WASM_JIT_CONDITION_HELPER_CENSUS` fails at the isolation `#error`.

## Private build and served assets

The only target built was:

```text
make -j1 azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeInt9AJoinedCensus
```

It produced the following unique private pair, staged Wasm first and JS second under `assets_d3d9web` so no existing page could begin a mixed pair:

```text
runtime stem: boxedwine.upstreamjit64fn6inlineabi2int9ajoinedcensus1
JS   FF475D63314172DCD429ED23CCCB5D3185A9F6C13FC86BC59358A8751933334B
Wasm 48FC4927002B54A8F6E900B291F9756F5C796E00FD45E9E7F89DBB09DB78CE73
```

**VERIFIED:** Build-to-stage hashes match for both files. HTTP `200` byte hashes from `127.0.0.1:8765/assets_d3d9web/<stem>.{js,wasm}` match the same two values. `make -q` marks the target current; Wasm parses successfully and generated JS binds exactly the three required named Module exports: `_d3d9WebInt9AJoinedCensusGetAbiVersion`, `_d3d9WebInt9AJoinedCensusGetSnapshotBytes`, and `_d3d9WebInt9AJoinedCensusCopySnapshot`.

## Direct single-page runtime proof

A watcher-fresh Edge had exactly one `about:blank` page, a new isolated profile, all three anti-throttling flags and no build process. Its one page was navigated through CDP to the exact private URL with only:

```text
runtimeStem=boxedwine.upstreamjit64fn6inlineabi2int9ajoinedcensus1
int9aJoinedCensus=1
jitCacheUrl=off
```

The button was activated by a CDP pointer press/release after the document was visible and focused; it was not started by a DOM `.click()`. Direct runtime evidence then showed ABI `1`, `68` words, first Wasm JIT block, visible/focused CSS canvas `1024x768`, continuing direct Presents, and repeated async windows with `submitted=120`, `reaped=120`, `errors=0`.

The page-owned reader was invoked directly after rendering. It passed all reader invariants for both a sealed snapshot and a later sealed epoch:

| field | epoch 63 | epoch 69 |
| --- | ---: | ---: |
| state / owner | `1` / non-zero | `1` / non-zero |
| submitted / first / last / reaped | `120 / 7441 / 7560 / 7560` | `120 / 8161 / 8280 / 8280` |
| generated `fn_8` / Int9A / invalid | `261287 / 21191 / 0` | `758089 / 90360 / 0` |

For epoch 63, index calls exactly equal bridge calls as `[0,0,17645,119,3427,0]`; generic calls/runs and the complete 25-opcode partition all equal `17645`. The reader accepted the record, so all six per-index call partitions and the async sequence/owner checks passed.

**VERIFIED boundary:** reaping proves main-thread `dispatchBatch` returned the authenticated `D3D9WEB_OK` acknowledgement for each submitted sequence. It does **not** prove GPU completion. No `jit-record`, replay URL, cache write, `presentCapture`, attached sampler, or 30-second FPS calculation was used.

## Next decision

The census establishes material generated Int9A and its D3D bridge partition, but does not establish helper time share or a semantics-preserving direct replacement. A separate static semantic/equivalence card must first prove a minimal safe candidate (stack fault, index/EAX synchronicity, EIP/bailout and CPU state included); only then can a new private cache-OFF integrity path be opened. The user-noted private-corpus/tail-rewrite pipeline suspicion remains **INFERRED** and is not assigned as a cause by this diagnostic.
