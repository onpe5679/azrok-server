# 412 -- Gate 6 logical-composite32 private cache-OFF render (2026-07-26)

## Status

**VERIFIED build/cache-OFF browser render integrity. No record, replay cache,
or FPS decision has occurred.**

The isolated private target completed with only pre-existing source and
Emscripten warnings.  Its JS/Wasm were staged under the private stem; build
and staged SHA-256 matched exactly:

```text
JS   7b271767ceed48bf6de74b3e08e44b0dbfdaa2a08ac0a8f8c195b3be496eef61
Wasm 387bf8210f9af2122c7262e626d42b15e464e6b89118d960ad644d69f08558d9
```

The sole visible CDP page loaded only the private
`runtimeLogicComposite32=1`, `runtimeStem=...logiccomposite321`,
`jitCacheUrl=off` URL and was started by a CDP pointer click on the enabled
run button.  It directly reported private ABI `1`, a first JIT block, focused
visible 1024x768 canvas and eventually 4,733 direct Presents.  The final
async ring window has `submitted=120`, `reaped=120`, `ring_full=0`,
`sync_drains=0`, `errors=0`.

This is an integrity/liveness gate only.  The output's transient Wine RPC
exception trace preceded normal rendering and is not a candidate failure.
No 30-second capture was started or interpreted as FPS.

## Next gate

Make a fresh private record from this generation, transform it with the exact
runtime logical-composite32 raw identity and descriptor, fill final archive /
grouped-manifest pins, then prove pinned replay render before any A-B-A.
Accepted, census, fixture, parity and MRG artifacts remain ineligible.
