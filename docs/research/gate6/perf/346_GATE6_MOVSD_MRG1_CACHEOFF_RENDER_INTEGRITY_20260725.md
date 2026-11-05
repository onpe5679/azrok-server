# Gate 6 MRG1 runtime-zero MOVSD cache-OFF render integrity (2026-07-25)

Status: **VERIFIED isolated build, served artifact, and visible real-game render integrity; NOT a performance verdict**

This closes the candidate-specific gate left by 345.  It does not change the
accepted `boxedwine.upstreamjit64fn6inlineabi2` asset, its replay ZIP, or any
FPS conclusion.

## Build and public-ABI gate

**VERIFIED:** static review found no runtime P0.  It did find one build P1:
`Build/MRG1` supplied `boxedwine-wasm-jit-module-broker.js` through `--pre-js`
but was absent from the link prerequisite allow-list.  The makefile now puts
`Build/MRG1` in that list, so a broker pre-JS update forces an MRG1 relink.
The candidate was then force rebuilt from the current sources.

`verify-abi2-freeze-glue.mjs` passed against the accepted freeze glue and the
rebuilt MRG1 glue: 32 explicit legacy bindings, 33 public bindings including
proxy-main, and no forbidden dual-entry binding.  A direct MRG1 target-line
check also confirmed `ABI2_LEGACY_EXPORTED_FUNCTIONS` and no pair/register-GP
export leakage.  `WebAssembly.validate` passed.

The rebuilt bytes were staged only under the private stem
`boxedwine.upstreamjit64fn6inlineabi2movsdruntimezero1`:

| asset | SHA-256 | served-byte match |
| --- | --- | --- |
| JS | `80195DB565C5000935130E534F4724EC1570DFE9F6D6FAB85C02665739DB0572` | yes |
| Wasm | `BF47108D49A2C217475833E3CF8466023F79685315571F83DB2EAFF1CCEF5D39` | yes |

This private stem maps its JS and Wasm as a pair through the page's existing
`runtimeStem` loader.  The accepted Freeze1 Wasm and the accepted cache ZIP
were not overwritten.

## Direct single-tab browser gate

**VERIFIED:** the one existing CDP page target was cache-disabled through
`Network.setCacheDisabled` and navigated, not replaced by a new tab, to the
private stem with `jitCacheUrl=off`.  The URL omitted `jit-record` and
`presentCapture`.  The page fetched the staged JS/Wasm through 8765, booted
the candidate, and output the first JIT-block and direct-chain-ABI witnesses.

The new isolated Edge profile first presented Wine's optional Mono installer;
the guest `Cancel` button was selected (not Install), after which Wine completed
its one-time configuration.  This is first-profile guest setup, not a runtime
candidate failure.

The direct visible screenshot subsequently showed the existing `Azrok1`
character-selection scene, and after the normal in-canvas Continue input it
showed the PatHouse interior with the player model, room furniture, HUD, and
normal UI.  A direct CDP state snapshot at that point showed:

```
visibility=visible
runtimeStem=boxedwine.upstreamjit64fn6inlineabi2movsdruntimezero1
jitCacheUrl=off
presentSnapshot=5376
Module.wasmJitCache.size=0
recordActive=false
```

The present value is only a liveness snapshot, not a timed sample; no A-B-A or
FPS adoption claim was made.  The cache-off/no-record state and the visible
PatHouse scene establish render integrity for this private candidate.  The
distinct EA16 and worker-table scope decisions are still NOT VERIFIED, so MRG2
counters, cache/replay publication, and any performance measurement remain
closed despite this successful candidate render gate.
