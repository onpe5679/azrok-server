# Gate 6 - low-priority compiler-flag build isolation

Date: 2026-07-24

## VERIFIED static audit

The accepted ABI2 target already applies `-O3 -msimd128` to both compilation
and link paths. Therefore `-msimd128` is a baseline property, not an additive
candidate; its meaningful independent comparison is a separately built
no-SIMD variant. A command-line `OPTIMIZATION_FLAGS` override against the
accepted build directory would reuse stale objects and is prohibited.

Two new isolated targets retain the same ABI2 runtime macros, bridge exports,
shell, assets, and JIT broker dependency while using independent directories:

| Target | build directory | flag delta |
|---|---|---|
| `...Fn6InlineAbiFlto` | `Build/AzrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFlto1` | `-O3 -flto` in compile and link flags |
| `...Fn6InlineAbiNoSimd` | `Build/AzrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiNoSimd1` | removes `-msimd128` from compile and link flags |

The target directories are explicitly included in the JIT broker dependency
gate, so the candidate cannot silently omit the broker pre-JS input.

## VERIFIED low-priority launch control

The old makefile unconditionally exported host-width `-j31`, defeating an
outer `make -j1`. It now honors `LOW_PRIORITY_JOBS` only when supplied; normal
build behavior is unchanged. A dry run produced `-O3 -flto`, preserved
`-msimd128`, and addressed only the new FLTO build directory.

The first launch exposed the old `-j31` behavior and was stopped before any
asset publication or performance measurement. The restarted FLTO build uses
`nice -n 19`, `LOW_PRIORITY_JOBS=1`, `-B`, and the isolated target. Live
process observation shows one `em++` compiler at a time; the active log starts
with `MAKEFLAGS ... -j1`. Its current warning is the pre-existing unused
lambda capture in `knativeinputSDL.cpp`; it is not an acceptance result.

## PGO status

**NOT STARTED.** This toolchain exposes instrumentation/use flags but has no
configured `llvm-profdata` on PATH and no verified browser profile-flush /
collection / merge contract. A PGO build before that contract would not be a
reproducible candidate. It remains behind the isolated FLTO and no-SIMD build
cards.

## Next

Wait for FLTO completion, statically validate output identity and exports, then
run the existing regression and cache-OFF visual gates before any A-B-A. Build
the no-SIMD target only after FLTO stops, preserving one low-priority compiler.
No candidate asset is publishable by this document.

## VERIFIED build result and publication gate

Both isolated `nice -n 19`, `LOW_PRIORITY_JOBS=1`, forced-rebuild jobs
completed without compiler/linker errors. `WebAssembly.validate` accepts FLTO
(3,549,999 bytes) and no-SIMD (3,039,250 bytes). Both generated JS glues
contain the required grouped-registration and inline-fetch ABI bindings.

They are nevertheless **not publishable**: the current source tree includes
the newer dual-entry pair-registration exports, while the accepted deployed
ABI2 artifact predates that shape. The candidate Wasm export counts are
FLTO 57 and no-SIMD 56 versus accepted ABI2 54; this is evidence of source
generation drift, not a compiler-flag performance comparison. Neither asset
was copied into `assets_d3d9web`, no cache was built, and no browser/runtime
or FPS gate was run. A future flag card must first freeze or separately prove
the exact accepted ABI2 export/loader contract, then rebuild both conditions
from that same source revision.
