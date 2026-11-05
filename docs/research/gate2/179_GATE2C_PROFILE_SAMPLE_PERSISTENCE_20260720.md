# 179 Gate 2c profile-sample persistence (2026-07-20)

## Scope

This document closes an evidence-retention gap before the next one-scene
PatHouse performance measurement. It does not claim a frame-rate result.

## VERIFIED

1. The fresh 1 GiB partial-upload browser run did not leave
   `D3D9WEB_BRIDGE_PROFILE` or `D3D9WEB_CPU_PROFILE` samples in the persisted
   runtime/packet artifacts. Its exact PatHouse frame rate, upload size, and
   sustained memory state therefore cannot be reconstructed from disk.
2. The host `report()` path already writes bounded diagnostics both to the
   browser console and to BoxedWine's output textarea through `Module.print`.
3. The renderer now additionally retains only the low-frequency
   `D3D9WEB_BRIDGE_PROFILE` and `D3D9WEB_INDEXED_CACHE` lines in a bounded
   page-runtime array, capped at 64 samples. This does not add work to
   per-command render tracing or access browser user storage.
4. The PatHouse page now imports the host runtime with cache key
   `perfprobe11`, ensuring the next fresh browser page cannot reuse the
   pre-cache implementation from the previous module URL.

## NOT VERIFIED

- Whether the indexed vertex/index upload cache yields cache hits or improves
  screenshot-confirmed PatHouse FPS. The next run must collect both persisted
  counters and a visible scene before this is promoted.
