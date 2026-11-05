# 423. INT 0x9A direct-fixture P1: range, successor state, and SMC re-decode

Date: 2026-07-26  
Status: **PARTIALLY VERIFIED** — this closes only the P1 rows stated below.  Asynchronous D3D indices remain open.  No production candidate, cache, replay, or FPS sampling is authorized.

## Scope and isolation

- `Build/I9F1` remains a test-only `__TEST + BOXEDWINE_MULTI_THREADED + BOXEDWINE_WASM_JIT + BOXEDWINE_D3D9WEB + BOXEDWINE_WASM_JIT_INT9A_DIRECT_FIXTURE` target.
- The direct arm remains private to `JitWasmCodeGen::dynamic_int9A`; the normal `jitOther.h` route still uses `emulateSingleOp()`.
- The new one-shot SMC arm is compiled only under the same I9F1 macro and is absent from every production/cache/replay target.

## Static boundary: why ordinary guest SMC cannot reach the later direct helper

**VERIFIED.** A generated write to a JIT CodePage enters the checked write helper, invalidates the active decoded block, and sets `cpu->wasmJitBailout=1` when that active block is among the invalidated operations (`source/emulation/cpu/wasm/jitWasmCodeGen.cpp:12193-12198`, `12516-12521`, `16306-16314`).  Its immediately following `emitBailoutCheck()` exits before a later INT 0x9A boundary can run.  Thus a fixture that merely puts a guest CodePage write immediately before INT 0x9A would prove the existing SMC bailout, not the direct helper's re-decode fallback.

The fixture therefore performs exactly one **test-only** `KMemory::writew` inside `runNextSingleInt9ADirectFixture`, immediately before its already-required fresh `getNextOp()`.  It changes the live bytes from `CD 9A` to same-length `89 C0` (`mov eax,eax`) through the real CodePage invalidation path.  The helper then sees a fresh non-`Int9A` decode and invokes the existing `CPU::runNextSingleOp()` fallback; it never calls `normal_int9A` on stale bytes.  No invalidated `DecodedOp*` is dereferenced after this write.

## Added P1 rows

### D3D dispatch-range rejection

**VERIFIED.** Generated direct-boundary rows pass both `D3D9WEB_INDEX_BASE - 1` and `D3D9WEB_INDEX_BASE + 6`.  Each asserts `direct/fallback/fault = 1/0/0` and unchanged `EAX=0xA5A50000`.  This matches `callD3D9Web`'s early range return before `peek32(1)`/`peek32(2)` (`source/opengl/d3d9web.cpp:983-990`).  Valid index-0 and index-1 rows remain present.

### Dirty GP, segment and lazy-flag successor state

**VERIFIED.** The direct path is entered after `mov ds,stack-selector` and `inc ecx` (`ECX=0xffffffff`, hence lazy `ZF=1`).  Its successor reads `DS:[0x20]` with `moffs8`, then materializes flags with `pushfd/pop esi`.  The fixture asserts:

- `direct/fallback/fault = 1/0/0`;
- `DS.value` and `DS.address` equal the stack segment after the boundary;
- `ECX=0`, `EAX=0x125A` after index-0's EAX result plus the DS read; and
- materialized `ZF` remains set in `ESI`.

This exercises the boundary's full GP commit and subsequent GP/segment/lazy-cache invalidation rather than just a helper-local state check.

### Re-decode mismatch fallback after a real CodePage mutation

**VERIFIED.** The fixture first warms and proves a generated direct-INT9A root.  It then arms the one-shot CodePage mutation, resets witnesses, and runs that published root.  After the write it obtains only a fresh decoded operation and asserts:

- bytes are exactly `89 C0` and the fresh operation is non-`Int9A`, length 2;
- `direct/fallback/fault = 0/1/0`;
- `EAX` remains the generic index-0 result `0x1234`; and
- `wasmJitActiveBlock == nullptr` and `wasmJitBailout == 0` once the execution returns.

This is specifically a direct-helper pre-re-decode mutation proof.  It does **not** claim that an ordinary preceding guest SMC instruction reaches that helper; the verified bailout ordering above prevents that path.

### `peek32(0..2)` stack-fault delivery

**VERIFIED.** The fixture now runs three protected-stack rows for the three actual reads made by `normal_int9A`/`callD3D9Web`.  The target stack word begins at the first protected page byte in every row while the signal frame remains in the preceding writable page:

| Fault row | `ESP` | Reads before the fault | Expected protected address |
|---|---:|---|---:|
| `peek32(0)` | `0x1000` | none | `SS.base + 0x1000` |
| `peek32(1)` | `0x0ffc` | index | `SS.base + 0x1000` |
| `peek32(2)` | `0x0ff8` | index, arg1 | `SS.base + 0x1000` |

For each row the fixture first runs a NormalCPU oracle, then a separately published generated direct root, with the same `SIGSEGV` handler.  It compares saved handler EIP, signal number/code/address, handler completion, and handler-written EAX.  The direct row additionally requires `direct/fallback/fault = 0/0/1`.

The direct helper's caught-fault path now sets test-private `wasmJitBailout=2`; I9F1 consumes that marker before ordinary SMC bailout handling, clears active-block state, and returns to CPU dispatch with the delivered handler EIP intact.  This is necessary for equivalence because the generic SMC arm otherwise writes the generated successor EIP.  The marker and emitter arm are isolated to I9F1.

## Build and served-asset evidence

The serial exact target command was:

```powershell
$env:Path='C:\Program Files\Git\usr\bin;'+$env:Path
$env:EM_FORCE_RESPONSE_FILES='1'
Set-Location tools\boxedwine_local\bwujit_threaded_abi\project\emscripten
make -j1 testMultiThreadedJitInt9ADirectFixture
make -q testMultiThreadedJitInt9ADirectFixture   # exit 0
```

| Asset | SHA-256 disk | SHA-256 served over 8765 | Result |
|---|---|---|---|
| `boxedwine.js` | `9EA0243847812120C510326AB681B902CA4724900415BB9CA99F9E077E405DE7` | same | VERIFIED |
| `boxedwine.wasm` | `36F73259CE4AAA21221D2BA735E491131256CB1D9A6194340806CD1B210C8498` | same | VERIFIED |

## Browser runtime

**VERIFIED.** The sole CDP page was navigated, without creating a tab, to:

```text
http://127.0.0.1:8765/bwujit_threaded_abi/project/emscripten/Build/I9F1/boxedwine.html?646&1&1&i9f1p2=1
```

`document.visibilityState` was `visible`.  `textarea#output` directly reported:

```text
Running 1 Test tests with 1 threads starting at 646
[WASM JIT] first JIT block executed, tableIdx: 8194
[WASM JIT] direct chain ABI depthOffset=1660 bailoutOffset=132
INT9A direct fixture index/range/segment-lazy OK
Test WASM JIT INT9A direct fixture ... OK
0 tests FAILED in 0s
```

The test's success includes the internal SMC fallback assertions above.  This is a fixture runtime result, not a Present/FPS sample.

## Remaining closure matrix

1. **NOT VERIFIED:** all three stack-word fault positions (`peek32(0..2)`) and delivered signal/EIP equivalence.
1. **NOT VERIFIED:** D3D indices 2..5 asynchronous bridge ordering/completion behavior.
2. **NOT VERIFIED:** production private candidate, cache-OFF real-game integrity, record/replay, and A-B-A performance.
