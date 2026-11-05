# 314 - Wasm `getZF()` repair-placement correction

## Supersession

This record supersedes 312's build/browser claim. The original static diagnosis
remains valid, but the attempted edit was applied to the optional
`BOXEDWINE_WASM_JIT_RUNTIME_ZNZ_COUNTERS` implementation of
`wasmHelper_cond_Z()`. The normal ABI2 artifact did not compile that block, and
`wasmHelper_computeZF()` still returned boolean `0`/`1`.

## Corrected contract - VERIFIED static

- `Jit::btStartFlags()` clears architectural ZF then ORs the Wasm `getZF()`
  result into `CPU::flags`; it requires `0x40` or `0`, never boolean `1`.
- `wasmHelper_computeZF()` now writes `cpu->getZF() ? ZF : 0` to `tmpReg`.
- `wasmHelper_cond_Z()` remains a conditional helper and writes boolean
  `cpu->getZF() ? 1 : 0`; its result is consumed by generated Wasm comparison
  flow, not `btStartFlags`.
- The focused `CMP -> BT -> SETZ` fixture added in 312 remains the required
  functional regression test. Its multi-threaded execution is still NOT
  VERIFIED because the available Windows and WSL make environments cannot
  build that test target with one usable path/toolchain mapping.

## Deployment and integrity - VERIFIED build/browser

The previously reported private and accepted hashes are not evidence of this
correct repair. The private MT-helper-census build was the first artifact with
the fixed source and reached cache-OFF visible PatHouse. The accepted 54-export
stem was then rebuilt from the same source and deployed: JS SHA-256 remains
`80195DB565C5000935130E534F4724EC1570DFE9F6D6FAB85C02665739DB0572`, while
the corrected Wasm SHA-256 is `1D80EECEF4EED19F0BB8D047882F2D16185E2166DD960A2FC9AA710C18E122FD`.
The preceding erroneous Wasm (`83E538D97235714842E9D208C2F392132DD433A2B7CA36D7CB3A4A2A5AE4D34A`)
is retained as `pregetzfrepairplacement20260724` beside the accepted asset.

The accepted runtime was launched with `jitCacheUrl=off`, completed selection
and rendered the full visible 1024x768 PatHouse room. Its final async-ring
sample was `callbacks=120 first_seq=6001 last_seq=6120 next_seq=6121 gaps=0
reorders=0 errors=0`, and browser console errors were empty. This is render
integrity only; no Present/FPS score was captured. The focused MT fixture
execution remains NOT VERIFIED.
