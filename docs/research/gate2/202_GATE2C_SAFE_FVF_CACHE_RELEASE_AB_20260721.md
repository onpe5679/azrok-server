# 202 Gate 2c safe FVF cache release A/B

Date: 2026-07-21

## Scope

One browser tab was reused. Each navigation closed the prior WebSocket and
server connection before the next session; socket and heartbeat counts proved
that only one game session was active. The original client binary was not
patched. The ignored lower empty-slot text remains outside this gate.

## VERIFIED -- measurement before implementation

The compiled-WASM state profiler first measured intact 1024x768 PatHouse:

- 19,080 SetFVF calls per 120 Presents;
- 18,120 calls satisfy all safe suppression conditions;
- 240 calls are the first FVF after declaration-state invalidation;
- 720 calls change the FVF value;
- BeginStateBlock=0 and Reset=0 throughout PatHouse.

Thus 151 identical SetFVF calls per frame were removable without changing
declaration unbind, Reset, state-block recording, or command-failure behavior.
This was not inferred from generic D3D usage; it was measured in the target
scene.

## VERIFIED -- standard-preserving cache conditions

`Device_SetFVF` returns early only when:

```text
fvf_valid && old_fvf == new_fvf && declaration == NULL &&
recording_state_block == FALSE
```

- CreateDevice starts invalid through zero initialization.
- Reset invalidates the FVF shadow.
- A successful SetVertexDeclaration invalidates it, including a null bind.
- SetFVF marks it valid only after `SendCommand` succeeds.
- A bound declaration is still unbound before sending SetFVF.
- State-block recording disables suppression.

An independent static review verified these transitions. The separate proxy
standards defect remains: BeginStateBlock succeeds but EndStateBlock and
vtable slot 61 are absent. This cache does not bypass that defect; if Begin is
called, its guard disables the optimization rather than dropping recordable
state.

## VERIFIED -- instrumented A/B

With identical profiling overhead and the same PatHouse workload, host-visible
FVF packets fell from 19,080 to 960 per 120 Presents (94.97%). All 720 changed
and 240 declaration-transition packets remained. Batch size fell by about
0.2 MB per 120 frames. The intact room and Korean/UI output were unchanged.

The late steady instrumented windows reached 22.64, 22.81, and 22.73 FPS
(22.73 mean), compared with the preceding five-window 21.186-FPS measurement.
The early optimized windows were noisy, so this is supporting evidence rather
than the release performance claim.

## VERIFIED -- clean release result

All measurement-only guest counters and the sampled CPU/state profiler were
removed while retaining the safe cache. The non-profile DirectDrawUP runtime
then produced five accepted steady windows:

```text
27.30, 25.67, 27.71, 26.01, 27.21 FPS
mean=26.78, min=25.67, max=27.71
```

Each accepted window retained the normal workload
`upload_calls=2160`, `upload_bytes=60440880`, `direct_calls=240`,
`opcode12=120`. Document 200's comparable non-profile post-OOM baseline was
23.02 and 23.11 FPS (23.065 mean), so this release is +16.11% against that
baseline.

The final screenshot shows intact walls, doorway, carpet, table/stool,
character face and shadow, HUD, Korean text, alpha, and culling. Browser
warnings/errors are empty. Resource retirement continues with
`missing=0`, `bound_blocked=0`; the live count changes only when a real scene/UI
resource is added, not once per temporary texture frame.

Artifacts:

- release DLL SHA-256:
  `22FE3B1008F8CE1B32F05DE7ACDDB986E0E2A3155EC9CE1FF038F9B85027D356`
- package: `Azrok_D3D9Web_pathouse_fvfcache_release1.zip`
- package SHA-256:
  `F379997AB5B8FD5C3A9748B806766339DDA163507B30FB73CCED619CE4CDBBA1`

## Next gate

The release reaches the previously predicted no-JIT 25--30 FPS band but is
still far from 65 FPS. The next measured CPU targets are already known from
document 201, so no repeat broad profile is needed:

1. pure scalar-SSE coordinate/normal kernels at `FUN_101041d7` and
   `FUN_101042a3` (4.05% guest sampled time) for the safest first AOT/WASM-SIMD
   proof;
2. the `FUN_1004a6d0 -> FUN_10049630 -> FUN_10046760` transform chain
   (11.78%), especially the x87-heavy `0x4aa80..0x4abdd` trace;
3. if combined address-specialized traces cannot approach 65 FPS, implement a
   reusable hot-block JIT/stackifier rather than continuing one-function-only
   patches.
