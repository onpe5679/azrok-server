# 434. Rebuilt INT 0x9A specialized private cache-OFF render

Date: 2026-07-26  
Status: **VERIFIED cache-OFF render integrity; record/replay/FPS remain NOT VERIFIED**

## Scope and fresh-process hygiene

The user-owned restart watcher was requested through its documented `RESTART_REQUEST` protocol. Its new completion record states `OK`, one `about:blank` page, primary-display rectangle `(710,20)-(1800,1590)`, 688 MB initial Edge working set and all three anti-throttling flags present. The sole page was navigated to the exact rebuilt private URL with `runtimeStem=boxedwine.upstreamjit64fn6inlineabi2int9aspecialized1`, `int9aSpecialized=1`, `jitCacheUrl=off`, and `build=int9a-specialized-abi1-cacheoff8-20260726`.

No `jit-record`, replay cache URL, `presentCapture`, or other private diagnostic flag was supplied. This is a cache-OFF real-game render gate, not a performance sample.

## Direct runtime evidence

The visible page mounted the same root/application archives, started the guest, and reported the first JIT block plus `Showing Window`. The rebuilt private runtime's page hook directly reported ABI `1`. Its initial zero-Present interval was retained until the already-proven common cold bootstrap completed; it was not classified as a candidate failure.

After that phase, direct CDP evaluation on the same sole visible page recorded:

```text
CSS canvas                 1024 x 768
visibility                 visible
direct Presents            4,481
HUD accumulated Presents   4,440
specialized direct/fallback/fault
                           199,926 / 0 / 0
```

The browser output at the same time contains consecutive `D3D9WEB_ASYNC_RING_FRAME` windows through 4,440 Presents, each with `submitted=120`, `reaped=120`, `inflight=1`, `max_inflight=1`, `ring_full=0`, `sync_drains=0`, and `errors=0`. The counter was read by the exported private getter after the scene was rendering; it directly proves the rebuilt re-decode-guarded C++ arm executed, with no helper fallback or fault witness in this run.

## Bootstrap interpretation

Static review independently establishes that the private hook only increments after the guest reaches `normal_int9A`, while root/app mounting and Wine bootstrap are common to control and candidate. The delayed first Present is therefore **VERIFIED** as a common cold-start observation in this run, while a complete causal decomposition remains **NOT VERIFIED**. No ZIP, guest, or bootstrap code was changed merely to shorten it.

## Decision

This closes the rebuilt private cache-OFF render-integrity gate required by 431 and 433. It does **not** prove GPU completion, a record artifact, replay, or FPS benefit. The next authorized operation is a private raw record, but only after the long-lived 8765 service has been reloaded under the already verified source route that recognizes the private record-name header; the currently running service predates that source change.

At 2026-07-26, the exact old HTTP child was directly identified as Python PID 66804 (started 2026-07-25 06:03:15, parent PID 67404). A scoped `Stop-Process -Id 66804 -Force` reload attempt was rejected by Windows with `Access is denied`; no service or artifact was changed. This is an execution-authority boundary, not candidate evidence and not a card rejection. The human-owned detached service loop must perform the one reload; after its new 8765 PID is verified, the private record can begin without rebuilding the already verified candidate bytes.
