# 395 -- MRG1 intentional resource hold

> **Execution hold SUPERSEDED by 396.** The historical hold evidence remains
> valid; AfterFX exit and restored watcher/browser allowed a fresh recovered
> DISPLAY6 baseline.

Date: 2026-07-25  
Status: **VERIFIED** user-directed hold; no performance conclusion.

## Hold state

The user intentionally terminated all ten measurement Edge processes, stopped
the restart watcher, and removed the pending restart request while After
Effects renders. The partly loaded A4 page is gone and produced no timing row.
Direct recheck finds zero `msedge` processes, CDP 9222 unavailable, one
AfterFX process at about 127,989 MiB working set, and about 18,509 MiB free
physical memory. No build process is present.

The restart request created for the provisional DISPLAY6 A2 was found still
present after the watcher stop and was removed without launching a browser.
This prevents a future watcher relaunch from accidentally starting a
measurement. No A2 navigation, pointer activation, readiness wait or FPS row
occurred.

## Disposition

The A1/A2/A3 `44.2917/36.8466/41.9950` values remain preserved solely as
memory-pressure observations and are **not eligible** for MRG1 performance
disposition. The DISPLAY6 relative-comparison policy in 394 remains valid but
its execution is deferred until the user confirms all of: After Effects exit,
memory recovery, watcher relaunch and a fresh browser.

Browser absence here is the user's intentional resource hold, not a card
blocker or MRG1 failure. Until that external condition changes, do not launch
a browser, create a cache, start a build, or collect FPS.
