# 638 — r10 renderer/D3D9Web next-10 source audit

Date: 2026-09-01 KST

## Conclusion

- **VERIFIED actual r10 renderer window:** this audit reuses #637's accepted
  35.030745-second actual-PatHouse window, 2,688 Presents, data-loss zero, and
  corrected owner wait identity. No projected r8/r10 denominator is used.
- **VERIFIED FFP pack rejection:** the three fixed-function pack leaves own
  4,854,630 us = **13.858198%** of marker wall. A full-coverage 3.45x packer
  saves only **9.841329%**; reaching 10% requires at least **3.591884x** before
  incomplete coverage, GL uploads, or cross-thread criticality are considered.
- **VERIFIED critical-path rejection:** pack inclusive time is 5,124,516 us,
  of which 5,070,353 us = **98.943061%** overlaps owner compute. The measured
  independent critical lower remains zero. The accepted artifact preserved no
  `D3D9WEB_ASYNC_RING_FRAME`, `ring_full`, or `sync_drains` count, so no
  backpressure claim is inferred.
- **VERIFIED marshalling/batching rejection:** a deliberately generous
  mutually-exclusive leaf envelope for JS command decode, DrawUP vertex
  swizzle, and unidentified callback/mailbox work is **3.136576%** wall.
  `bufferData` is 2.776784% and named GL draw is 0.065020%. Perfect removal of
  each coherent source-identified family cannot reach 10%.
- **VERIFIED source architecture:** the host creates one linked FFP uber-program,
  caches driver-reflected std140 layouts per program, but allocates fresh block
  buffers and fully packs the three base FFP blocks whenever the shared dirty
  bit reaches a draw. Shader/material-cache work therefore has no measured
  per-draw compile surface; persistent incremental packing is the only
  source-identified renderer design worth reopening, and it fails the current
  admission contract.
- **VERIFIED prior negative control:** `uboDirtySplit` already changed actual
  PatHouse frame time from 27.2807 ms to 27.7372 ms (**1.6734% worse**) and was
  removed. A persistent incremental packer is not allowed to relabel or repeat
  that block-only split.
- **PRODUCTION/REMOTE UNCHANGED:** no runtime, page, cache, production asset,
  service, or deployment route was changed. Only read-only analysis, tests,
  derived artifacts, and this document were added.
- **VERIFIED completion verifier repair:** the historical r9 verifier no longer
  requires its intentionally superseded Make target; it pins the preserved r9
  artifacts while validating current source wiring through the active r10
  superset target. A dedicated r10 verifier now pins clean-build/published
  JS/Wasm, cache/manifest/base/ABI, reverse-normalized groups, safe-republish
  source/Make/page contracts, and production-default exclusion. Both pass.

## Actual r10 surface table

| Surface | Leaf time | Marker wall | Standalone-10 decision |
|---|---:|---:|---|
| FFP base pack union | 4,854,630 us | 13.858198% | 3.45x saves 9.841329%; reject |
| generous command-marshalling envelope | 1,098,766 us | 3.136576% | perfect removal below 10 |
| WebGL `bufferData` | 972,728 us | 2.776784% | perfect removal below 10 |
| named WebGL draw calls | 22,777 us | 0.065020% | multi-draw cannot reach 10 |
| V8 `(program)` leaf | 4,514,985 us | 12.888635% | non-actionable heterogeneous container |

The `(program)` row is shown so a large unattributed bucket is not hidden. V8
does not separate browser native code, graphics driver time, scheduler work,
or sampling gaps inside that label. It is a search surface with causal lower
zero, not an implementation candidate.

## Source audit

### Command transport

The guest already seals each Present frame into a three-slot shared async ring.
The worker copies the bounded batch into a slot, publishes it with release
ordering, and schedules a main-thread callback. The callback passes a shared
`HEAPU8.subarray` directly to `dispatchBatch`; it does not structured-clone the
command payload. Non-Present synchronous tails drain prior slots in FIFO order.

Consequently, another message format or additional renderer worker has no
measured 10% serialization surface. A render worker could change scheduling,
but cannot remove the 28.1973% inclusive WebGL dispatch work and must not be
credited with that entire concurrent container.

### State packing

`pack-ffp.js` preserves one `WeakMap` of driver-reflected layouts per linked
program, but every pack call creates a new `ArrayBuffer`. `uploadState()` fully
packs `FFVertexData`, `FFPixelState`, and `FFPixelStages`, then calls
`gl.bufferData` for each. The shared `ffpStateDirty` bit is raised by transform,
material, light, render-state, and texture-stage changes.

This explains the measured coherent leaf family. It does not prove it lies on
the frame critical path. The earlier base-block dirty split removed some
unnecessary packs but made end-to-end frame time worse, so a new candidate must
change the actual packing algorithm, not only dirty-bit classification.

### Shader/material cache and draw batching

The steady draw path uses one linked fixed-function uber-program. There is no
per-material shader generation/compile family in the accepted window. The
actual room's historical 170 draws/Present and 44.7059% theoretical call-count
reduction do not change the current named GL draw leaf of 0.065020% wall.
Non-adjacent reordering also remains semantically unproved. Both axes are
rejected before implementation.

## Correctness contract for any future incremental packer

A new packer may be admitted only if it preserves all of the following:

1. Driver reflection remains authoritative for block size, offset, matrix
   stride, and array stride; no browser-specific std140 constants silently
   replace the existing query contract.
2. One persistent byte shadow is scoped to the exact linked program and WebGL
   context generation. Reset, relink, context loss/restore, and first draw
   invalidate and fully initialize it.
3. Every state mutation maps to all affected blocks and byte ranges. Shared
   alpha/fog/projection/sampler fields that occur in both vertex and fragment
   blocks are invalidated together.
4. IEEE-754 bit behavior, including signed zero and NaN payload behavior
   observable through the current DataView writes, remains differential-equal.
5. Dirty-range coalescing never crosses a block or publishes bytes from a later
   command. Batch ordering, resource lifetimes, draw order, and Present
   boundaries remain unchanged.
6. The first upload after invalidation is complete; partial `bufferSubData`
   updates may follow only after the full shadow and GPU buffer agree.
7. Random command-sequence differential tests compare every produced byte with
   the current packers, including transform/light/material/alpha off-on,
   texture stages, clip planes, blend matrices, reset, and context restoration.
8. Existing shader compile/link, round-trip, page contract, and actual visual
   PatHouse gates all pass before performance measurement.

## Reopen and experiment gate

The current 3.45x design assumption is rejected. A materially different packer
may reopen this track only in this order:

1. A captured-state differential replay must show **at least 3.591884x** for
   the complete measured pack family, not one sub-packer, while producing exact
   bytes under the correctness contract.
2. A fresh r10 actual-PatHouse diagnostic must join async slot sequence to
   producer ring-full wait microseconds, synchronous-drain wait microseconds by
   reason, renderer `dispatchBatch` begin/end, and pack intervals.
3. Renderer-caused backpressure must have a **>=10% full-wall removable lower
   bound** in that same window. Counts alone are insufficient when nonzero;
   missing counters are not treated as zero.
4. Only then may an opt-in candidate enter fresh-process equal-phase r10 A/B.
   Actual frame time must improve by at least 10% under the project admission
   rule; renderer-local speedup is not the decision metric.

## Evidence

- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.verified.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.runtime_wait_shift.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.host_renderer_profiles.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.renderer_next10_gate.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.renderer_next10_gate.json`
- `artifacts/performance/ubo_dirty_split_ab_20260831.csv`
- `tools/browser_diagnostics/analyze_renderer_next10_gate.py`
- `tools/test_renderer_next10_gate.py` — 6/6 PASS
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-face-r9-cwd-writer-runtime-cache.mjs` — PASS in historical-artifact/current-superset scope
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-face-r10-cwd-safe-runtime-cache.mjs` — PASS
- `artifacts/performance/face_r9_verifier_current_scope_20260901.json`
- `artifacts/performance/face_r10_cwd_safe_runtime_cache_verification_20260901.json`
- `tools/boxedwine_local/web_backend/host/d3d9web-runtime.js`
- `tools/boxedwine_local/web_backend/host/pack-ffp.js`
- `tools/boxedwine_local/bwujit_threaded_abi/source/opengl/d3d9web.cpp`
