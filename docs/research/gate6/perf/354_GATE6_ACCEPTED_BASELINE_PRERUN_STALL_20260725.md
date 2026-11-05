# 354 — accepted ABI2 baseline preRun stall (2026-07-25)

## Scope

This is a measurement-environment P0 discovered while beginning the required
accepted → MRG2 → accepted A-B-A after 353. No FPS result is recorded here.

## VERIFIED — the accepted grouped-cache contract is not the failing row

The accepted `azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2.zip`
has a valid legacy-v2 MT contract: 134 manifest groups match 134 ZIP group
paths, with 41,625 entries and 32,439 patches. Its source declares one-token
publication (`pfnJitCodeOffset=12`). The page fetches and inflates all 134
groups (43,762,106 bytes) and stages them as page-owned replay groups.

The visible sole CDP page then remains at `JIT 그룹 캐시 준비 중`, with
`jitReplay=staged`, `jitReplayGroups=134`, zero registered/installed modules,
and an installed `Module.onRuntimeInitialized` wrapper. The page's registration
loop is synchronous; therefore it has not started. Main JS/Wasm and the
grouped ZIP each returned HTTP 200. The ordinary automatic app JIT ZIP returned
404 as expected and did not replace the page-owned groups.

## VERIFIED — boundary is before the page callback

The served Emscripten JS executes `preRun()`, waits run dependencies, then
calls `initRuntime()` and `onRuntimeInitialized`. The actual served shell adds
`wasm-jit-cache` and `setupBoxedWine` dependencies. Its `loadFile()` and IDBFS
sync error paths may fail to invoke their callbacks, so a preRun wait can be
unbounded. Independently, the 32-worker pool exists while the callback is not
entered.

The page status is only a staging marker, not proof that ZIP loading itself
is stalled. The served shell, not the project build-copy shell, is the
authoritative loader artifact for this result.

## VERIFIED — current environment facts

The renderer process has been alive since 06:04 and uses 10.26GiB working set
(dynamic CDP observed 10.59GiB WS / 11.88GiB private). It is idle during the
stalled state; 32 unattached worker targets exist. Host physical memory is not
exhausted: 189.64GiB total, 122.85GiB free at observation.

## VERIFIED — stale HTTP asset hypothesis rejected

The same sole tab was navigated to an otherwise identical accepted URL with a
new `build=accepted-inlinefetch2-baselinefresh1` query, forcing fresh accepted
JS/Wasm worker-bootstrap URLs. D3D runtime readiness was waited for explicitly
before the start click. The result reproduced exactly: 134 staged groups,
zero registered groups, and 32 pool workers after 35 seconds. This rules out a
stale main JS/Wasm HTTP-cache artifact; it does not establish a root cause.

## INFERRED — next action

The direct cause is a preRun dependency / worker-bootstrap state in this
long-lived renderer, not a replay manifest mismatch. It is not yet proven
whether a fresh renderer is required or which dependency never resolves.
Do not record any A-B-A number from this state. Preserve the single-tab rule;
obtain a clean renderer only with explicit user direction if tab/process
replacement is required.
