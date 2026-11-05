# 428. INT 0x9A specialized helper: first cache-OFF bootstrap observation

Date: 2026-07-26  
Status: **VERIFIED served identity/getter; cache-OFF render NOT VERIFIED**

## Fresh-process admission

The human-owned watcher was requested through `RESTART_REQUEST` before this run.  Its completion record reports one `about:blank` page, the primary-display rectangle `(710,20)-(1800,1590)`, all three anti-throttling flags, and a 719 MB fresh Edge working set.  The one page was then navigated directly to the strict private URL with `int9aSpecialized=1`, the private stem, `jitCacheUrl=off` and the real guest-batch app; no tab was created.

The staged and HTTP-served JS/Wasm SHA-256 values match 427, generated JS parses, `document.visibilityState` is `visible`, and the page reader directly reports specialized ABI `1` and initial counters `[0,0,0]`.

## Bootstrap observation

**VERIFIED observation, NOT a render pass.** The ordinary pointer start control was used and BoxedWine reached the first JIT block, ABI-depth log, SIMD enable and `Showing Window`.  After two successive 60-second readiness observations, direct Presents remain `0`, async ring is absent, and the private counters remain `[0,0,0]`.  The textarea has no additional fault or failure line beyond the pre-existing Wine setup warning.

The renderer process is not idle: a direct 30-second process sample added `42.703` CPU seconds, while working set rose only from about `3231` to `3293` MiB.  This supports ongoing cache-OFF guest/JIT bootstrap rather than a quiescent page, but is not itself a readiness or correctness pass.

This is not a performance measurement and does not establish that the specialized direct arm executed.  Nor is it a candidate rejection: cache-OFF bootstrap can be materially longer than the old readiness window and the zero counters do not identify a failure boundary.  Cache recording, replay and FPS remain prohibited.

## Next action

First diagnose the pre-Present bootstrap stall using the same fresh private URL and direct runtime state/log evidence.  Do not substitute an accepted cache, change the accepted stem, or treat the current `[0,0,0]` counters as a helper-semantic failure.  Only a visible real-game render with a nonzero direct count can close the cache-OFF admission.
