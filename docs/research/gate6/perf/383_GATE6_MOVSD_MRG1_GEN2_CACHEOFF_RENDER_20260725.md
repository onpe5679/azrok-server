# 383 ??MRG1 generation-2 cache-off render closure

Date: 2026-07-25  
Status: **VERIFIED** ??real-game render integrity only; not an FPS result.

## Fresh-process procedure

The human-started restart watcher created a new isolated Edge process with one
`about:blank` page, 721 MiB initial tree working set, and all three required
anti-throttling flags. The page was navigated once to the rebuilt private MRG1
stem with `jitCacheUrl=off` and `startupDependencyTrace=1`. Startup used an
actual CDP mouse press/release on the visible audio/run button; no synthetic
`element.click()` was used for the gesture.

## Direct browser evidence

The initial cache-off stage was deliberately not treated as a failure. Its
dependency trace resolved `1 -> 2 -> 3 -> 2 -> 1 -> 0` after about 80.8 s,
then Wine/audio/FFP bootstrap continued. A later same-page read directly
observed all of:

- sole, focused, `document.visibilityState=visible` page and CSS/backing
  canvas `1024x768`;
- MRG1 runtime guard ABI `1`, `jitCacheUrl=off`, first JIT block and no replay
  registration path;
- `D3D9WebDebug.presents=1,190` (later independently observed above 1,500);
- async ring `callbacks=1,190`, `errors=0`, no gaps or reorders, plus
  submitted/reaped 120-frame telemetry with `ring_full=0` and
  `sync_drains=0`; and
- established renderer -> local 9201 bridge -> local 9200 game-service TCP
  links.

This proves the rebuilt generation-2 MRG1 body reaches actual PatHouse render
with cache disabled. The long first-run bootstrap means dependency count zero,
`Showing Window`, or a bounded zero-Present snapshot alone is not a readiness
criterion; subsequent MRG1 record/replay gates must require advancing direct
Present and an error-free async ring rather than infer readiness early.

## Boundary

No 30-second Present capture was invoked, so this document makes no FPS or
adoption claim. The stale generation-1 raw/archive pins remain forbidden.
Next is a fresh immutable generation-2 MRG1 cache-off record, followed by its
private no-direct transform/identity pins and replay-render proof before the
fresh-process accepted-vs-MRG1 A-B-A(B) comparison.
