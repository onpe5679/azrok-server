# 223 Gate 2c material-latch fast guard and native microbenchmark

Date: 2026-07-21

## Scope

This is a native Test/x64 verification and microbenchmark pass for the
`acknex.dll+0x8E0A0` production helper after its exact per-hit code guard was
changed to allocation-free `wasmMemoryTryMatchBytes`. It does not modify or
launch browser assets, and it does not change production dispatcher policy.

## VERIFIED -- exact guard mutation rejection

The production helper remains directly compared with the relocated NormalCPU
interpreter across document 221's complete resident and side-exit matrix. The
fixture now additionally mutates and restores three representative positions
of the exact nine-byte block after the containing-function signature has
already been accepted:

- byte 0: first opcode byte (`INC EDI`);
- byte 4: middle displacement byte of `CMP EDI,[ESI+0x264]`;
- byte 8: last branch displacement byte (`JC`).

Each mutation makes `d3d9WebRunMaterialLatch` return `false` while preserving
the complete CPU/FPU/SIMD snapshot and the existing `nextOp`. Thus the new
matcher does not weaken the full nine-byte fail-closed guard.

## VERIFIED -- cross-page byte matching

A separate nine-byte sequence starts at guest page offset `0xFFC`, placing
four bytes on the first resident page and five on the second. The new matcher
accepts the exact sequence, rejects a last-byte mutation on the second page,
and succeeds again after restoration. This covers the two-page path separately
from document 221's cross-page four-byte material-count read.

The same-entry/different-`KMemory` negative fixture also continues to pass,
proving the containing-signature cache remains keyed by both numeric entry and
memory identity.

## VERIFIED -- focused native integration

The Test/x64 target rebuilds successfully. The existing focused set retains
its first 13 entries; the new benchmark is a separate entry at index 13.

```text
BoxedWine.exe 0 13 1
Test D3D9Web Hot AOT Material Latch Fixture ... OK
...
Test DSP Audio Write Math ... OK
0 tests FAILED
```

This run covers the material-latch interpreter/test-only/production
differential, runtime-WASM guards and tiers, both SSE helpers, the x87 fixture
and benchmark, and DSP audio math.

## VERIFIED -- native single-call microbenchmark

The benchmark uses one fixed resident taken case. Every timing pair prepares
and decodes state before the clock starts, then measures only:

- reference: one NormalCPU basic-block dispatch executing the three decoded
  instructions `INC/CMP/JC`;
- helper: one accepted `d3d9WebRunMaterialLatch` call, including its exact
  nine-byte match, allocation-free dword read, commit, and successor lookup.

Setup and snapshots are excluded. Both entry and successor DecodedOps are
primed before each timer, matching a steady resident/code-cached loop. Because
Windows `steady_clock` quantizes these sub-100-ns calls, the final timer uses
serialized TSC deltas, subtracts the median empty-bracket cost, and calibrates
cycles to nanoseconds against a 100-ms steady-clock interval. There are 257
warm-up pairs followed by 8,193 measured pairs per process. Five independent
Test/x64 processes report:

| Process | Interpreter median ns/call | Helper median ns/call | Ratio |
|---:|---:|---:|---:|
| 1 | 70.0 | 30.0 | 2.333x |
| 2 | 70.0 | 30.0 | 2.333x |
| 3 | 70.0 | 20.0 | 3.500x |
| 4 | 70.0 | 20.0 | 3.500x |
| 5 | 70.0 | 20.0 | 3.500x |

The process-median values are **70.0 ns/call reference**, **20.0 ns/call
helper**, and **3.500x median per-process ratio**. This is a native
steady-code-cache single-block advantage, not browser FPS evidence. In
particular, it does not
measure the Wasm implementation of the matcher/MMU helpers or the browser's
entry frequency and frame interaction.

## Status

- **VERIFIED native dynamic:** full differential 13 passes with the new
  matcher; first/middle/last mutations and cross-page exact matching pass.
- **VERIFIED native performance:** production helper is about 3.5x faster than
  the three-op NormalCPU block in this isolated resident Test/x64 measurement.
- **NOT VERIFIED browser performance:** only a counter-free browser release A/B
  can decide whether this helper is beneficial in the target environment.
