# 277. Gate 6 — worker-local generic slot readiness bitmap

Date: 2026-07-23 KST

## Status

- **VERIFIED static:** A shared readiness byte row is unsafe because each JS Worker owns a distinct `wasmTable`. The implemented row is instead allocated and retained per JS Worker/table lifetime, and its pointer is rebound into the current CPU before compiled entry.
- **VERIFIED static/runtime:** A byte becomes one only after the same worker's final positive slot check; runtime-group rollback, broker purge, and test clear reset the byte before clearing the table entry. Allocation, pointer, capacity, or ABI mismatch fails closed.
- **VERIFIED static:** A/B have identical 41,625 ordinary functions, 32,439 direct-call patches, non-code sections, imports, and exports. The only generated-code difference is the last generic dispatcher in each of 134 groups.
- **VERIFIED browser:** Exact live ABI is relocation map `12964392`, bitmap pointer offset `1664`, capacity `262144`. Deliberately wrong map and bitmap-offset manifests were rejected by the loader before game execution.
- **VERIFIED browser:** The bitmap build preserves the reference 1024x768 PatHouse walls, carpet, furniture, character face, Korean UI, protocol, and async-ring ordering with no runtime error.
- **VERIFIED / REJECTED:** Adaptive A-B-A-B measured adjacent mean effects of -20.43% and -13.67%, median -17.05%. Replacing `table.get/ref.is_null` with pointer/nested-byte guards is decisively slower and is not adopted.

## Safety design

The shared `DecodedOp::pfnJitCode` publication cannot prove that another worker's local table has installed the slot. Therefore a single shared slot bitmap would create false positives and possible `call_indirect` traps.

The accepted safety model for this experiment was:

1. Each JS Worker allocates one 262,144-byte row and retains it for the lifetime of that Worker's `wasmTable`.
2. `CPU::wasmJitWorkerReadyBitmap` is appended after all established raw-Wasm CPU fields, preserving every old embedded offset.
3. `wasmJitSlotReadyForWorker()` binds the current Worker's row before all ready fast paths.
4. A zero pointer, allocation failure, capacity mismatch, table-grow failure, failed slot check, or failed lazy install returns false before compiled entry.
5. Only the final positive same-worker slot check publishes byte 1.
6. Partial group rollback, broker purge, and test clear set byte 0 before `wasmTable.set(slot, null)`.
7. Slots remain monotonic and are not reused; pfn unpublication and quiescence still precede broker purge.

The page requires the exact new capability export and matches live pointer offset and capacity against the manifest before enabling generic dispatch. Older/unknown slot-visibility modes fail closed or retain the existing table-reference path.

## Artifacts and direct ABI proof

Runtime:

- stem: `boxedwine.upstreamjit62workerbitmap1`
- JS SHA-256: `3952689655A20E4E1082EA5C698793E79BE948AE6B799F0936E43C2490BAC346`
- Wasm SHA-256: `02F18F84EE4E5A1AC3ED96430879FD1988CE4DD0D4E6E87B47444E2F7357754B`

Caches:

| Condition | Artifact | SHA-256 | slot visibility |
|---|---|---|---|
| A | `profiles/azrok-jit-grouped-commonfast64-depthlocal-workerbitmaprt1.zip` | `D485F664CC9A772A654A7E5D6292C1B85223ED7A9BF1CE64E6A287695E7C0299` | `table-ref-v1` |
| B | `profiles/azrok-jit-grouped-commonfast64-workerbitmap1.zip` | `89E2293CDFD8EC86B77BB80F6143DC4D9D8A46FC632472ADF912D199FC2479CC` | `worker-byte-map-v1` |

Both retain `tableBounds=dispatcher-checked`; the previously rejected bounds removal is not mixed into this comparison. The live loader was first given a stale map manifest and reported `12964392/12963560`, then a correct-map/wrong-offset manifest and reported `1664/4`. Both stopped before game execution.

## Structural A/B proof

- ZIP entries: 135/135, identical names
- groups: 134/134
- ordinary function bodies: 41,625/41,625 byte-identical; aggregate body SHA `AB968B758B470C3B53306E59AF3BD26D12AF6BCD3EA7BEAC2D0394215685895B`
- direct-call patches: 32,439/32,439 exact
- non-code/import/export sections: 134/134 exact
- `WebAssembly.validate`: A 134/134, B 134/134
- dispatcher difference only: A keeps `table.size` plus `table.get/ref.is_null`; B keeps the same `table.size` and replaces only the reference guard with `cpu[1664]`, nonzero-pointer nested guard, and `i32.load8_u` installed-byte nested guard
- reverse-normalization: 134/134 B dispatchers reproduce A exactly; failures 0

B dispatchers are 132 bytes versus A's 119 bytes. The pointer load, two nested branches, and byte load add 13 body bytes; the body-size ULEB adds one more group byte.

## Adaptive A-B-A-B result

Each leg used one clean visible tab, the same runtime, 30 one-second HUD reads, and the same PatHouse reference scene. Foreground changes were recorded but not used to discard samples. No page was hidden or fully occluded.

| Leg | mean FPS | median FPS | min--max | renderer CPU / 30 s | foreground samples |
|---|---:|---:|---:|---:|---|
| A1 table ref | 52.5033 | 52.3000 | 49.6--55.8 | 95.219 s | WindowsTerminal 30 |
| B1 bitmap | 41.7767 | 42.3000 | 38.2--44.9 | 111.594 s | WindowsTerminal 30 |
| A2 table ref | 46.6833 | 47.2000 | 43.6--49.2 | 105.000 s | WindowsTerminal 30 |
| B2 bitmap | 40.3033 | 40.9000 | 36.8--43.3 | 125.109 s | mspaint 22, SearchHost 3, SnippingTool 3, msedge 2 |

A drift is -11.08%, so extension to B2 was mandatory. Adjacent mean effects are:

- B1 versus A1: `-20.43%`
- B2 versus A2: `-13.67%`
- two-pair median: approximately `-17.05%`

Renderer CPU also increases in both B legs. This is not a marginal/noise result: V8's table reference check is materially cheaper than the fail-closed bitmap sequence in this workload. The bitmap cache remains an opt-in diagnostic artifact only; the table-reference depth-local cache remains accepted.

## 50-FPS gate

A1 directly exceeded the target with a 52.50-FPS 30-second mean, but A2 measured 46.68 FPS and A drift was 11.08%. Therefore stable 50 FPS is **NOT VERIFIED**. The next optimization must preserve the A dispatcher and target another repeat cost; one high A leg is evidence that the current implementation can cross 50 under favorable scheduling, not proof that the final gate is complete.
