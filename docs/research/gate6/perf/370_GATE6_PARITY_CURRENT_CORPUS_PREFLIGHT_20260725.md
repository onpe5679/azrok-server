# 370 -- Parity current-corpus remeasurement preflight (2026-07-25)

Status: **VERIFIED static and dynamic; old parity candidate is not measurable**

## Measurement first

No FPS sample was taken. The purpose was to determine whether the retained
parity67 artifact can be compared to the current accepted control after the
old environment-drift result was discarded.

## Direct asset and live checks

The current accepted control is
`azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-currentabi1.zip`:

```text
94 groups / 30,550 modules / 28,944 patches
generic-indirect relocMapBase = 12,968,408
```

The retained parity67 artifact is physically present but is a different
corpus:

```text
135 groups / 41,792 modules / 32,433 patches
generic-indirect relocMapBase = 12,964,392
```

The 4,016-byte map-base difference is an exact fail-closed ABI boundary
(355), not a presentation-only difference. It also changes both corpus and
runtime generation, so old parity67 cannot be B against the 94-group control.
No A-B-A or A-B-A-B may use it.

`verify-abi2-freeze-cache.mjs` accepts each archive only with its own map and
rejects the parity archive at `12,968,408` with `generic relocMapBase`.
Compared with current control, the old archive also has 11,242 more entries
(36.80%), confirming that transforming its old raw would not repair the
corpus confound.

The existing sole CDP page was left on FQ1. Read-only dynamic checks found
one visible page target, CSS 1024x768, advancing Present, and 8765/9200/9201/
9300 plus CDP 9222 listening. CIM did not expose the main Edge command line;
therefore the next performance run must let the 357 harness itself record the
full anti-throttling/overlap contract rather than infer it here.

## Required next gate

`azrokMultiThreadedJitAudioO3AsyncRingFn6InlineParity` proves the source
candidate macro exists, but its retained make stanza had only target-specific
variables and no recipe, so it cannot execute.  A new private
`azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiFreezeParityCurrent` target
uses isolated `Build/ParityCurrent1`, the ABI2 legacy export set, and only
`BOXEDWINE_WASM_JIT_INLINE_PARITY` beyond the accepted production flags.  Its
dry-run expands the expected `-O3`/SIMD/pthread command line into that private
directory; historical parity assets remain untouched. `verify-paritycurrent-build-gate.mjs`
checks that build directory, recipe, ABI2 exports, parity production branch,
and no-mixed-card macro set. No current-map parity
raw record or grouped replay exists yet. Required order is the private
current-ABI build, cache-OFF
fresh record, immutable raw, current-map (`12,968,408`) transform/group,
manifest/loader exact-identity gate, cache-OFF visible render integrity, then
the harness-recorded A-B-A (extend to A-B-A-B if required). Runtime-lazy Z/NZ
remains excluded until parity is decided.
