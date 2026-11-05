# 440. Workload-fingerprint replay-init order repair

Date: 2026-07-26  
Status: **VERIFIED static repair; diagnostic browser runtime remains open**

## First runtime attempt

The first fresh accepted diagnostic page was intentionally not an FPS leg and
produced no FPS row. It reached replay staging, then failed closed with:

```text
workload fingerprint requires registered replay/lean-only diagnostic mode
```

This exposed a timing defect in the new observer, not a renderer or candidate
failure. `prepareAzrokJitReplay()` returns after staging its
`Module.onRuntimeInitialized` callback; actual group registration and
`dataset.jitReplay='registered'` occur later, when the BoxedWine module calls
that callback. The initial wrapper installed the observer immediately after
the async prepare returned, so its registered-replay guard correctly rejected
too early.

## Repair and audit

The wrapper now captures the replay-installed `Module.onRuntimeInitialized`
handler and chains it. It invokes that prior handler first, then installs the
fingerprint only after normal registration returns. If the prior hook throws,
the observer is not installed and guest startup remains fail-closed.

Static review directly verifies that the registration hook writes
`jitReplay='registered'` synchronously before the outer installer executes;
the wrapper has no recursive path and preserves prior-first chains used by
the existing specialized/census hooks. Node function extraction and the
attached sampler's PowerShell parse pass. The earlier `RESULT_OK=0x6001`
repair remains in place, and the sampler still rejects the diagnostic flag.

The failed fresh page is retained as a pre-FPS diagnostic failure. The next
authorized action is a new fresh accepted diagnostic run; no cache creation,
build, or performance sample is needed.
