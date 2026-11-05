# 422. INT 0x9A direct fixture P0 runtime

## Status

**VERIFIED — P0 direct-helper fixture gate passed.** This is a test-only
semantic result. It authorizes neither a production stem nor cache/record/
replay/FPS work.

## Scope and isolation

`421` established that a pure Wasm/JS D3D replacement is forbidden. The new
fixture is isolated behind
`BOXEDWINE_WASM_JIT_INT9A_DIRECT_FIXTURE`, requiring `__TEST`, multi-threaded
Wasm JIT, and `BOXEDWINE_D3D9WEB`; its compile gate rejects profile, joined
census, opcode census, logical-composite, MOVSD and FISTP fixture mixtures.

The target is `testMultiThreadedJitInt9ADirectFixture`, with unique output
`Build/I9F1`. It does not stage, replace, or load an accepted/private game
asset, and has no persistence/cache identity branch.

The fixture override exists only in `JitWasmCodeGen::dynamic_int9A`. Its
generated boundary retains the ordinary current-EIP store, all dirty GP
writeback, SMC arm, post-helper GP/segment invalidation, bailout check and
lazy-flags reset. It imports an append-only test helper (existing helper
numbers unchanged). The C++ helper live-redecodes the current operation:

- exact `Int9A`: copies the decoded op and calls `normal_int9A`, retaining the
  normal stack index read, `callD3D9Web`'s arg1/arg2 reads and index-specific
  EAX behavior;
- decode failure/non-`Int9A`: increments the fallback witness and calls the
  existing `runNextSingleOp()` path;
- exception: records a distinct fault witness while preserving the generic
  boundary's catch-and-bailout behavior.

## Static and build verification

**VERIFIED.** `cpu.cpp`, `jitWasmCodeGen.cpp`, and `testCPU.cpp` each pass
Emscripten C++20 syntax-only compilation under the exact I9F1 macro set.
Serial `make -j1 testMultiThreadedJitInt9ADirectFixture` completed; a
target-local `make -q` returns current (`0`). The test artifact hashes are:

| artifact | SHA-256 |
|---|---|
| `Build/I9F1/boxedwine.js` | `AA75F5A06D5779B89205B14591761069A8395A5B3E9791193A285121B412A451` |
| `Build/I9F1/boxedwine.wasm` | `D91D93AFF827FD0E5077E5880E957494ECC3165B894E18AEB58CF00CA312331E` |

## Direct browser P0

**VERIFIED.** CDP `9222` had exactly one visible page target. The existing
sole page was navigated (no new tab) to the private fixture URL:

```text
http://127.0.0.1:8765/bwujit_threaded_abi/project/emscripten/Build/I9F1/boxedwine.html?646&1&1
```

`646` is the appended final entry in the exact preprocessed I9F1 test array
(`647` entries). The page had `document.visibilityState = visible`; its
`textarea#output` directly reported:

```text
Running 1 Test tests with 1 threads starting at 646
[WASM JIT] first JIT block executed, tableIdx: 8194
[WASM JIT] direct chain ABI depthOffset=1660 bailoutOffset=132
INT9A direct fixture index0/index1 OK
Test WASM JIT INT9A direct fixture ... OK
0 tests FAILED in 0s
```

The two generated Int9A rows seed all non-EAX GP registers with sentinels and
exercise D3D9Web indices 0 and 1. Their direct helper witnesses are exactly
`direct=1, fallback=0, fault=0`; normal D3D9Web returns EAX `0x1234` and
`0x3001` respectively, while the seeded non-EAX GP registers remain equal.
The test would fail if the generated operation used generic fallback, faulted,
or leaked a GP change.

## Boundary

This P0 result proves only the narrow direct re-decode/NormalCPU arm and the
two synchronous return-index rows. It does **not** prove re-decode mismatch
after SMC, any protected stack-word fault, D3D indices 2--5/async ordering,
range behavior, SMC active-block exit, or cross-block segment/lazy-flags
equivalence. Those are mandatory P1 fixture rows from `421`; no performance
candidate is authorized until they pass.
