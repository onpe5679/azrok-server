# 279. Gate 6 typed `return_call_ref` dispatcher

Date: 2026-07-23 KST

## Status

- **VERIFIED static:** The baseline dispatcher reads the same worker table slot twice: `table.get/ref.is_null` for readiness, then `return_call_indirect` for dispatch. V8 does not fuse those operations.
- **VERIFIED static/runtime feature:** A raw `funcref` cannot feed `return_call_ref`; V8 rejects it. The implemented candidate performs `table.get -> ref.cast (ref null $blockType) -> typed-ref local -> null check -> return_call_ref`. Minimal same-module and cross-module tests validate, instantiate, and execute; null keeps the existing fallback and a wrong signature traps before the call.
- **VERIFIED static:** A/B validate 134/134. All 41,625 ordinary function bodies, 32,439 patches, imports, exports, and non-code sections are exact. Only each final dispatcher and matching size metadata differ.
- **VERIFIED browser:** The typed-ref cache links in the real worker and preserves the reference 1024x768 PatHouse render, Korean UI, protocol transition, and resource state.
- **VERIFIED / REJECTED:** Extended A-B-A-B gives typed-ref effects -19.04% and -11.85%, median -15.45%. The candidate consumes essentially the same renderer CPU in 30 seconds but produces fewer frames. It is not adopted.

## Why the direct form is invalid

The imported worker table is `funcref`, while each compiled block has exact type `(i32 cpu, i32 relocBase) -> void`. `return_call_ref typeidx` requires a reference compatible with that exact function type, not a generic `funcref`.

The valid dispatcher form therefore uses:

1. `table.get` on the published slot;
2. `ref.cast (ref null $blockType)`;
3. a nullable typed-reference local;
4. `ref.is_null` and the same fallback return on null;
5. `cpu`, relocation base, typed ref, then `return_call_ref $blockType`.

For the live groups the dispatcher type index is 1. The exact added encodings are:

- typed local: `63 01`
- nullable cast: `fb 17 01`
- typed tail call: `15 01`

The generic recorded-body local parser assumes one-byte value types, so the newly created dispatcher local vector is deliberately built directly rather than fed back through that parser. CLI validation also rejects combining call-ref with the already rejected worker bitmap mode.

## Artifacts and structural proof

| condition | artifact | SHA-256 |
|---|---|---|
| A table-slot | `profiles/azrok-jit-grouped-commonfast64-depthlocal-workerbitmaprt1.zip` | `D485F664CC9A772A654A7E5D6292C1B85223ED7A9BF1CE64E6A287695E7C0299` |
| B typed-ref | `profiles/azrok-jit-grouped-commonfast64-depthlocal-callref1.zip` | `EF29A3225CC7150B8692885B0A46A12EB2C9CF23FD4209C8EC30D314F70068A4` |

- ZIP entries: 135/135 exact names
- `WebAssembly.validate`: A/B 134/134
- ordinary function bodies: 41,625/41,625 byte-exact
- direct patches: 32,439/32,439 exact
- non-code/import/export: 134/134 exact
- B dispatcher local declaration: `01 03 7f` -> `02 03 7f 01 63 01`
- B readiness sequence adds `fb 17 01 22 05`
- B tail replaces `20 03 13 01 00` with `20 05 15 01`
- reverse-normalizing those three patterns reproduces A 134/134 exactly
- each group grows by 7 bytes; merged Wasm grows by 938 bytes
- semantic manifest addition: `runtimeGenericIndirect.dispatchCall = typed-ref-v1`

The page loader now accepts only the known typed-ref dispatch marker and rejects typed-ref combined with worker-byte visibility before enabling replay. Missing `dispatchCall` retains the established table-slot path.

## Adaptive browser measurement

All retained legs were visible, used the same one-tab PatHouse path, and recorded a 30-second/31-endpoint renderer covariate window. Foreground was `WindowsTerminal` throughout the retained windows.

| leg | dispatch | mean FPS | median | min--max | renderer CPU / frame |
|---|---|---:|---:|---:|---:|
| A1 | table slot | 47.0233 | 46.8000 | 43.1--49.2 | 44.66 ms |
| B1 | typed ref | 38.0700 | 37.9000 | 36.5--41.0 | 58.03 ms |
| A2 | table slot | 43.6133 | 43.9000 | 40.2--46.5 | 50.65 ms |
| B2 | typed ref | 38.4433 | 38.5000 | 36.0--40.8 | 57.54 ms |

- B1 / A1: -19.040%
- B2 / A2: -11.854%
- two-pair median: -15.447%
- B drift: +0.981%, so the slow result itself is reproducible

B1 and A2 each consumed exactly 66.28125 renderer CPU-seconds in their 30-second windows, but B produced 12.71% fewer frames. This directly identifies lower work throughput rather than a renderer CPU-allocation artifact. V8's optimized `call_indirect` dispatch-table path is materially faster here than the typed reference cast/object path.

## Next gate

The visible browser was returned to the accepted table-slot/depth-local chain64 cache. A future single-lookup candidate must keep V8's fast `return_call_indirect`, for example by treating its own null/bounds trap as a rare lazy-install slow path. Such a design is admissible only if the outer call boundary can identify a current-worker missing slot without swallowing unrelated Wasm/guest traps, restore dispatcher depth, perform the existing install, and retry fail-closed.
