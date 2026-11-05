# 177 Gate 2c D3D9Web worker profile and upload boundary (2026-07-20)

## Scope

One browser client only. This is renderer transport measurement, not content
QA. Screenshots were checked before assigning any room-specific conclusion.

## VERIFIED

- The multithreaded Emscripten target does not execute guest CPU work through
  `kscheduler.cpp::runSlice`. Each guest worker is the unbounded
  `NormalCPU::run()` path in `normalPlatformMultiThreaded.cpp`.
- A diagnostic-only build samples one in 4096 normal opcodes per worker and
  emits 120-Present bridge windows. The Azrok render worker measured FPU at
  about 2.0--2.7% and SSE at about 7--8%. x87 is not the measured bottleneck;
  JIT/AOT work is not justified by this evidence.
- Character-selection windows reached 51.5--60.2 FPS with zero steady-state
  resource uploads and 5--7% worker-to-main proxy time. Screenshots confirm
  this was the selection UI, not PatHouse.
- A later transition/selection window repeatedly issued
  `COMMAND_UPLOAD_RESOURCE` (opcode 14): about 14.2 MB per 120 Presents,
  23.2--24.8 FPS, and 14.5--16.1% worker-to-main proxy time. Individual WebGL
  dispatch time and x87 cannot explain the remaining cost.
- Opcode 14 is now batched with ordered commands. `dispatchBatch` processes an
  earlier draw before the upload and later draws after the upload. The first
  post-change startup window had no per-frame direct proxy transfer.

## NOT VERIFIED

- PatHouse 50 FPS. The only 50+ FPS samples in this document are character
  selection and must not be presented as PatHouse evidence.
- The exact resource type/handle responsible for the 14 MB frame upload and
  whether partial dirty-range upload eliminates it.

## Next direct measurement

Collect a screenshot-confirmed PatHouse frame together with the bridge profile.
If opcode 14 persists, identify its resource kind/handle and change the guest
lock/unlock path to submit only its dirty range before considering CPU JIT.
