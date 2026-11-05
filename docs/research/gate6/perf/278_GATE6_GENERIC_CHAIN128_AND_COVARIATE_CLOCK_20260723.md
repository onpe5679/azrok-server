# 278. Gate 6 generic indirect chain 128 and covariate clock correction

Date: 2026-07-23 KST

## Status

- **VERIFIED static:** The 64 -> 128 candidate changes only the generic dispatcher depth constant and `source.mtGenericIndirectLimit`. All 41,625 ordinary functions, 32,439 direct patches, group layout, imports, exports, and runtime ABI are exact.
- **VERIFIED static:** Generic chaining uses `return_call`/`return_call_indirect`, so 128 does not create 128 native or Wasm stack frames. Target publication, capacity, yield, bailout, depth, table bounds, and non-null guards still execute before every taken dynamic edge.
- **INFERRED from verified counters:** The accepted common dispatcher reduced outer compiled-Wasm activations by 65.05196x. Treating removed outer entries as taken generic tails gives about 64.05196 tails per remaining outer activation, strong evidence that limit 64 is usually saturated. No direct limit-hit histogram exists.
- **VERIFIED / REJECTED:** Extended A-B-A-B-A measurement gives condition means A64 43.6367 FPS and B128 43.5117 FPS, B128 -0.286%. The closest late pair is B2 46.8100 versus A3 47.0233, -0.454%. Chain128 is not adopted.
- **VERIFIED measurement correction:** The old covariate script repeated a CIM renderer search inside every nominal one-second sample and stretched 30 rows to about 52 seconds. It now resolves the renderer once, uses an absolute stopwatch schedule, and records 31 endpoints spanning an actual 30.00 seconds.

## Static artifact proof

| condition | artifact | SHA-256 |
|---|---|---|
| A64 | `profiles/azrok-jit-grouped-commonfast64-depthlocal-workerbitmaprt1.zip` | `D485F664CC9A772A654A7E5D6292C1B85223ED7A9BF1CE64E6A287695E7C0299` |
| B128 | `profiles/azrok-jit-grouped-commonfast128-depthlocal-workerbitmaprt1.zip` | `5FCB7B31F8AD09720548AC68098513827174D6AC232008BFDA4883708A677353` |

- ZIP entries: 135/135 with exact names
- `WebAssembly.validate`: A/B 134/134
- ordinary bodies: 41,625/41,625 byte-identical; aggregate SHA `AB968B758B470C3B53306E59AF3BD26D12AF6BCD3EA7BEAC2D0394215685895B`
- direct patches and entry arrays: 32,439/32,439 exact
- non-code/import/export: 134/134 exact
- merged Wasm bytes: A/B both 44,721,653; every raw group size identical
- only dispatcher difference: 134 occurrences of `i32.const 64` (`41 c0 00`) become `i32.const 128` (`41 80 01`); reverse-normalization is exact 134/134
- manifest difference after removing `source.mtGenericIndirectLimit`: none

The pipeline generic limit validator was expanded from 64 to 256 while the unrelated MT cyclic limit remains capped at 64. The help text now states the exact semantics: N dynamic indirect edges, with the outer first block making up to N+1 blocks. This only enables experiments; 128/256 are not defaults.

## Adaptive browser measurement

All retained legs used one clean visible tab, the exact reference 1024x768 PatHouse scene, 30 one-second HUD reads, and a 31-endpoint/30-second renderer covariate window. No sample was hidden or fully occluded. Foreground changes are covariates only.

| leg | limit | mean FPS | median | min--max | renderer CPU / frame | foreground |
|---|---:|---:|---:|---:|---:|---|
| A1 | 64 | 42.7200 | 42.8000 | 38.7--44.6 | 49.75 ms | WindowsTerminal 31 |
| B1 | 128 | 40.2133 | 40.4000 | 37.3--43.3 | 56.85 ms | WindowsTerminal 28, powershell 3 |
| A2 | 64 | 41.1667 | 41.6500 | 37.2--43.2 | 53.97 ms | WindowsTerminal 31 |
| B2 | 128 | 46.8100 | 47.0000 | 42.8--50.5 | 43.83 ms | WindowsTerminal 31 |
| A3 | 64 | 47.0233 | 46.8000 | 43.1--49.2 | 44.66 ms | WindowsTerminal 31 |

Adjacent comparisons:

- B1 / A1: -5.868%
- B1 / A2: -2.316%
- B2 / A2: +13.709%
- B2 / A3: -0.454%

The first two-pair directions conflict because the environment accelerated late in the sequence. The immediate B2 -> A3 reversal directly controls that drift and shows no benefit. Across all retained legs, A64 mean is 43.6367 and B128 mean is 43.5117, or -0.286%. This candidate is therefore rejected, not retained as a marginal win.

An earlier preliminary A read of 42.1033 FPS is not used in the covariate table: its FPS samples were valid, but the pre-fix covariate process took roughly 52 seconds for 30 rows and could not be paired to the 30-second FPS window.

## Next gate

The accepted A64 dispatcher remains live in the visible browser. The next candidate should keep the 64-edge bound and remove a different per-tail duplication. In the checked path, `table.get/ref.is_null` proves a worker-local slot and `return_call_indirect` then looks up that same table slot again. A fail-closed local funcref plus `return_call_ref` is the next isolated candidate, subject first to exact browser/toolchain feature validation.
