# 432. INT 0x9A rebuilt private cache-OFF bootstrap and accepted control

Date: 2026-07-26  
> **SUPERSEDED in part by 433.** The bounded 0-Present interval below was later shown to be a common delayed bootstrap, not a persistent guest stop.  The rebuilt-ABI and no-record facts remain valid.

Status: **VERIFIED ABI/bootstrap facts; cache-OFF render, record/replay/FPS NOT VERIFIED**

## Rebuilt private bootstrap

The rebuilt private artifact from 431 was launched in a fresh watcher-created sole visible primary-display Edge process.  The page served the exact private JS/Wasm hashes from 431 and the run was cache-OFF (`jitCacheUrl=off`, no record, no replay, no Present capture).

The first page hook placement was wrong: an existing later generic pre-run installer replaced `Module.onRuntimeInitialized`, leaving the exported ABI functions present but the private status/counter hook unpublished.  Direct CDP inspection proved the final callback was the fetch-next census wrapper, not the INT9A wrapper.  The repair installs the private wrapper at the beginning of `prepareAzrokJitReplay`, after all generic callback installers and before the async runtime script is appended.  It also restores the intended three allowed private modes: cache-OFF, record cache-OFF, or the exact private replay URL.  Both executable inline scripts parse and the served no-store page contains the repaired logic.

On the next fresh private run, direct CDP facts were:

```text
visibility                         visible
CSS canvas                         1024 x 768
private runtime ABI                1
private direct/fallback/fault      0 / 0 / 0
first generated JIT                tableIdx 9060
async Presents/callbacks/errors    0 / 0 / 0
```

This directly proves the rebuilt private runtime and final page hook match.  It does **not** prove execution of the specialized helper: no live Int9A reached it before the guest stopped progressing.

## Bootstrap hold and control

The private output reached `Showing Window` then remained 0-Present/0-counter.  It later emitted:

```text
err:environ:run_wineboot boot event wait timed out
```

Physical run activation and three existing input-pulse clicks were used; no synthetic DOM click, cache generation or FPS timing occurred.

To distinguish a private helper failure from fresh guest startup, a new watcher-created accepted-stem cache-OFF control used the same root, app zip, command and visible primary window.  It reproduced the same early path:

```text
first generated JIT                tableIdx 9057
WASM JIT simd enabled
Showing Window
setupapi wineusb copy error 1812
Presents/callbacks/errors          0 / 0 / 0
```

At the time of this bounded observation the control had not yet reached Present.  The temporal interpretation is superseded by 433: the same control later completed its paced eight-heartbeat auto-select and entered rendering.

## Decision

No private record was emitted and no generic raw archive was touched.  The candidate remains fail-closed: it needs a fresh cache-OFF real-game render with nonzero specialized direct witness before the 430 service reload and private record/transform/replay sequence may proceed.  The primary-display baseline and all FPS decisions remain untouched.
