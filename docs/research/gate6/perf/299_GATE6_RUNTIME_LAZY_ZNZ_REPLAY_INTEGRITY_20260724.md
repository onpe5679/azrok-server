# 299 runtime-lazy Z/NZ fresh replay integrity and counter gap (2026-07-24)

**VERIFIED live replay/integrity; actual `fn_16/fn_17=0/0` and performance
NOT VERIFIED.**

## Live fresh-cache replay

The isolated candidate stem `boxedwine.upstreamjit68runtimeznz1` registered
the fresh 111-group cache from 298.  The live page status reported:

```text
jitReplay=registered
jitReplayEntries=34799
jitReplayGroups=111
jitReplayPatches=28215
jitReplayPair=legacy-v2
jitReplayRuntimeLazyZNZ=1:96:108:328:329:64
visible=visible
```

After the normal selection pulses it rendered a complete, visible 1024x768
PatHouse with the player/HUD intact.  The latest async-ring reports had
`gaps=0`, `reorders=0`, and `errors=0`; candidate-script console inspection
had no error; and the management API on port 9300 (not HTTP probing port 9200)
showed one `Azrok1` client in PatHouse with a recent heartbeat and healthy
capture.  These facts verify loader registration and rendering integrity, not
performance.

## Exact fallback counter gap

`fn_16` and `fn_17` are the 0-based helper-table entries for
`wasmHelper_cond_Z` and `wasmHelper_cond_NZ`, respectively.  The normal
multi-thread runtime-lazy candidate has no exported exact counter for those
helper-body entries.  The existing helper-call statistics are compiled only
when `!BOXEDWINE_MULTI_THREADED` and aggregate conditional-helper families;
the existing profile build samples conditional calls at 1/1024 and has a
different profile configuration.  Therefore neither can establish actual
runtime Z/NZ fallback calls as `0/0`.

Static grouped-module inspection can establish the fresh cache's direct
fn16/fn17 import/call-site count as 0/0, but that is not a substitute for
observing real execution, including invalid lazy-flag fallback branches.

## Next fail-closed diagnostic gate

Before any candidate FPS sample, build an isolated diagnostic-only runtime
that adds exact atomic entry counters at the start of `wasmHelper_cond_Z/NZ`
and exposes a read-only snapshot.  Its manifest/loader must identify a
diagnostic-counter version and reject a normal/diagnostic artifact mix.  A
fresh cache replay must report a start-to-end delta of `0/0`.  This diagnostic
artifact is integrity proof only and must not be used for the uninstrumented
release candidate's A-B-A performance result.
