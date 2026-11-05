# 348 — MOVSD EA16 helper SMC browser closure

Date: 2026-07-25  
Scope: private `MRGF5` only; no accepted runtime stem, cache ZIP, replay path, or
performance candidate was modified.

## Result

**VERIFIED.** The isolated EA16 `REP MOVSD` row completed in the browser on the
sole visible CDP page.  It proves the pre-existing EA16 helper route performs
the active-code-page SMC bailout/re-decode correctly, with the intended
negative witness that it did **not** enter the EA32 runtime-zero inline write
arm.

Direct CDP `Runtime.evaluate` of `textarea#output` returned:

```text
Running 1 Test tests with 1 threads starting at 391
[WASM JIT] first JIT block executed, tableIdx: 8187
[WASM JIT] direct chain ABI depthOffset=1660 bailoutOffset=132
Movsd SMC MRGF5 EA16 helper checked-write=0 bailout-taken=1 ... OK
Test Movsd runtime-zero guard SMC re-decode ... OK
0 tests FAILED in 0s
```

The page also reported `visibility="visible"`.  This is a correctness witness,
not an FPS sample.

## Private fixture and static gate

**VERIFIED static.** `Build/MRGF5` is selected by the dedicated
`testMultiThreadedJitMovsdRuntimeZeroGuardEa16SmcFixture` target.  Its macro is
`BOXEDWINE_WASM_JIT_MOVSD_MRG_EA16_SMC_FIXTURE`; it is mutually exclusive with
MRGN4/MRGF3/MRGF4, uses the test-JIT source set, and has the broker pre-JS
relink prerequisite. `make -n` emitted all of those properties; an independent
static audit found P0=0 and P1=0.

The guest bytes are:

```text
3E 67 F3 A5 41 CD 97 90  ->  3E 67 F3 A5 40 CD 97 90
```

The root is DS-overridden, EA16, REP MOVSD, length 4.  With DS base
`F0000000`, ES base `D0000000`, SI low16 `0180`, and DI low16 `0004`, the
helper copies source `F0000180` to code `D0000004`, changing the warmed
successor's `41` to `40`.  The fixture asserts 16-bit CX/SI/DI updates while
their high halves remain `A55A`/`A55A`/`D000` respectively.

`dynamic_movsd_op` explicitly guards the runtime-zero inline arm with
`!op->ea16`; EA16 REP therefore goes through the generic single-op helper.  The
expected counter pair is consequently `checked-write=0` and
`bailout-taken=1`.  The old successor is used only for ownership validation
before the write and is not dereferenced after invalidation; the fixture
reacquires the fresh successor at `+4`.

## Artifact and browser gate

**VERIFIED.** The fresh MRGF5 build produced:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `boxedwine.js` | 228,703 | `47630C10338463C09B6B42A54746B85B50EA28127D3A8905ADE403242FD41A2C` |
| `boxedwine.wasm` | 2,446,124 | `0EE33739871DF28D585C69F6C7154F33C5C68BBB6BE8FB00707614C34E98549E` |

The 8765-served bytes matched the build bytes exactly for both files, and
`WebAssembly.validate` returned true.  With CDP cache disabled, the existing
single page target was navigated (no new tab) to:

```text
http://127.0.0.1:8765/bwujit_threaded_abi/project/emscripten/Build/MRGF5/boxedwine.html?391&1&1
```

## Boundary

**NOT VERIFIED:** MRG2 remains required for parent-published table slot/broker
preload execution on a different guest worker.  This MRGF5 result covers only
EA16 helper SMC/re-decode on its creating worker.  It does not prove
cross-worker table visibility, cache/replay compatibility, publication of the
candidate, or any performance change.  MRG2 remains the next MOVSD card;
MOVSB and all FPS work stay closed until that witness passes.
