> **SUPERSEDED by 314.** The original diagnosis was correct, but the first
> attempted source repair was placed in the optional S/NS `cond_Z` helper,
> rather than `wasmHelper_computeZF`. Its reported browser artifact therefore
> did not contain the intended correction. Retained as the discovery record.

# 312 - Wasm `getZF()` mask contract correction

## Scope

This is a correctness repair discovered while selecting the next Gate 4 optimization measurement. It is not a performance result and opens no FPS candidate.

## Static evidence - VERIFIED

- `JitCodeGen::getZF()` returns either `0` or the architectural `ZF` mask. `ZF` is `0x40`.
- The Wasm override routed `getZF()` through `wasmHelper_computeZF()`, which returned boolean `0`/`1` through `CPU::tmpReg`.
- The sole Wasm-codegen caller is `Jit::btStartFlags()` for BT/BTS/BTR/BTC when the following decoded instruction needs ZF. It clears `ZF` then ORs the returned value into `CPU::flags` to preserve ZF while the bit operation updates CF.
- Therefore a true Wasm helper result set `CF` (`0x01`) instead of restoring `ZF` (`0x40`). The generic JIT contract and Wasm implementation disagreed.

## Repair contract

`wasmHelper_computeZF()` now returns `ZF` or `0`, matching the base JIT contract. The repair changes no lazy-flag formula and does not inline any helper. A focused `CMP -> BT family -> SETZ` regression fixture covers both incoming ZF states; the old broad bit tests did not reach this preservation path.

## Build and browser integrity - VERIFIED

- The private ABI2-shaped repair artifact compiles at `-O3`, has the accepted 54 Wasm exports, and exposes no typed-pair/register-thread ABI binding. SHA-256 is JS `80195D...0572`, Wasm `83E538...D34A`.
- With `jitCacheUrl=off`, the private artifact completed normal selection and rendered the intact visible 1024x768 PatHouse 3D room. The observed async ring reported `gaps=0`, `reorders=0`, `errors=0`; steady transitions remained JIT-backed (`543,179,624 / 545,000,000` target-jit in the last logged snapshot). This is an integrity check, not an FPS result.
- The accepted ABI2 asset now uses the same hashes. The previous accepted JS/Wasm is retained as private `pregetzffix20260724` assets (JS `39FD86...DECD`, Wasm `F1C29C...CEEF0`) for rollback/audit; the public ABI remains exactly 54 exports.

## Fixture execution boundary - NOT VERIFIED

The new MT Wasm-JIT fixture is compiled into source but was not executed in this environment. Windows make converts the test source list to inaccessible `/mnt/c/...` paths; the available WSL make has no `em++` and reports an fstab mount failure. The production runtime build itself completed. Re-run `testMultiThreadedJit` in a toolchain with one consistent path mapper before claiming fixture execution.

## Next measurement

The correction is not an FPS card. Only after the fixture boundary is closed may an exact `getZF/getCF/fillFlags` or broader helper-family census decide whether a separate performance card is warranted.
