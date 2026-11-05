# 280. Gate 6 worker-local last-ready-slot cache

Date: 2026-07-23 KST

## Status

- **VERIFIED static:** A per-group/per-worker mutable `i32` can remember one table slot only after the existing `table.size -> table.get -> ref.is_null` readiness proof succeeds. A hit skips only those readiness operations; publication, yield, bailout, depth, relocation, and `return_call_indirect` semantics remain unchanged.
- **VERIFIED static/build:** The candidate optimized all 41,625 blocks into 134 valid groups. A/B both validate 134/134. All 41,625 ordinary bodies are byte-identical, all 32,439 patch targets are identical, and their absolute offsets move by exactly +8 bytes because the new global section is inserted before code.
- **VERIFIED browser:** The candidate links in the real worker and preserves the reference 1024x768 PatHouse render: walls, carpet, table, chairs, character, Korean UI, and scene transition are intact.
- **VERIFIED / REJECTED:** Adaptive A-B-A-B measured condition means 45.1967 versus 44.6083 FPS (-1.302%). Adjacent effects were -2.786% and +0.232%, with a two-pair median of -1.277%. This is noise/no gain, so the candidate is not adopted.

## Design and safety boundary

The generic dispatcher already proves the target block's publication token and checks yield/bailout/depth before touching the worker table. The candidate adds one mutable global to each merged group module instance:

1. compare the current nonzero slot with the instance-local cached slot;
2. on equality, branch to the existing `return_call_indirect` call site;
3. on inequality, retain the complete table bounds and null-reference checks;
4. update the cached slot only after both checks succeed;
5. on a bounds/null miss, return to the existing C++ lazy-install path without caching it.

The cache is deliberately not stored in shared linear memory. `wasmTable` is JS-Worker-local, so a shared readiness value could incorrectly bless an uninstalled slot on another worker. A merged group module is instantiated against one worker table, which gives the required ownership. The loader fail-closes unless `readinessCache=instance-last-slot-v1` and `slotVisibility=table-ref-v1`, and refuses combinations with typed `return_call_ref` or the rejected worker-byte bitmap.

Trap-based fallback was rejected before implementation: a null/OOB indirect call becomes a JS `WebAssembly.RuntimeError` outside the current C++ RAII cleanup/retry contract, and cannot safely be distinguished from unrelated Wasm or guest traps by message text.

## Artifact and structural proof

| condition | artifact | SHA-256 |
|---|---|---|
| A accepted table-slot/depth-local chain64 | `profiles/azrok-jit-grouped-commonfast64-depthlocal-workerbitmaprt1.zip` | `D485F664CC9A772A654A7E5D6292C1B85223ED7A9BF1CE64E6A287695E7C0299` |
| B instance last-slot cache | `profiles/azrok-jit-grouped-commonfast64-depthlocal-lastslot1.zip` | `242C945AF8BD1B8DF2C201FFF61ABB525D6263B5A25252B7CDD474EC48DB77E0` |

- optimized blocks: 41,625/41,625
- groups and entries: 134 / 41,625 in both A and B
- `WebAssembly.validate`: 134/134 in both A and B
- ordinary function bodies: 41,625/41,625 exact
- direct-call patch targets: 32,439/32,439 exact
- patch absolute offset delta: +8 for every patch, exactly the new global-section size
- type/import/function/export sections: 134/134 exact
- B global section additions: 134/134
- total merged-Wasm growth: 3,082 bytes
- manifest marker: `runtimeGenericIndirect.readinessCache = instance-last-slot-v1`

## Adaptive browser measurement

All windows used the same visible in-app tab and the same original binary/PatHouse immediate-entry path. The covariate sampler pinned renderer PID 102836 once per window and recorded 31 endpoints over approximately 30 seconds. `WindowsTerminal` was foreground for all 124 endpoints. The HUD produced numeric FPS for every sample, so no hidden/fully throttled window was retained.

| leg | cache | mean FPS | median | min--max | renderer CPU/frame |
|---|---|---:|---:|---:|---:|
| A1 | checked table slot | 45.9467 | 47.0 | 42.3--49.7 | 48.33 ms |
| B1 | last-ready slot | 44.6667 | 45.0 | 41.9--47.3 | 48.28 ms |
| A2 | checked table slot | 44.4467 | 44.8 | 38.1--48.9 | 51.45 ms |
| B2 | last-ready slot | 44.5500 | 44.1 | 42.0--49.2 | 46.64 ms |

- B1/A1: -2.786%
- B2/A2: +0.232%
- adjacent-pair median: -1.277%
- condition means: A 45.1967, B 44.6083 FPS (-1.302%)
- A drift: -3.264%, so the user-defined adaptive rule required B2

The second pair reverses the first pair but remains within noise. CPU/frame also does not show a stable paired reduction. The comparison therefore says the added global compare/branch costs approximately as much as the avoided readiness operations at the real slot-repeat distribution.

## Decision

Keep the established chain64 table-slot/depth-local cache as the live default. The browser was returned to that cache after B2. Stable average 50 FPS remains **NOT VERIFIED**; an isolated prior window exceeded 50, but this controlled baseline averaged 44--46 FPS.

