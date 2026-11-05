# 184 Gate 2c PatHouse GPU/CPU split (2026-07-20)

> **AMENDED by 192.** The GPU-time result remains valid, but
> `D3D9WEB_CPU_PROFILE` sample counts cannot be converted to per-module CPU
> percentages, and `proxy_us` excludes guest packet construction plus two
> command-copy stages. See 192 for the corrected measurement boundary.

## Scope

Fresh 1 GiB direct-dispatch browser sessions, 1024x768, normal automatic
PatHouse bootstrap, single scene only. One run enables WebGL elapsed-time
queries (`?gpuprobe`); the control run uses identical code without that flag.

## VERIFIED

1. Both runs rendered the original PatHouse room (floor, furniture, character
   and HUD) and had no browser warning/error entries.
2. The timer extension was available. In the stable PatHouse window it reported
   1,672--2,397 microseconds of GPU time per batched frame, centered near
   2.0 ms.
3. The identical-code control run measured fourteen 120-Present samples from
   31.39 to 39.40 FPS, mean **34.96 FPS**. This replaces the older 23-FPS
   baseline as the current same-machine steady-state reference; the earlier
   lower result is retained as a historical measurement, not used for a delta.
4. The GPU-timed run was in the same 29--37 FPS range, so the elapsed-time
   query did not create the control result. Its measured GPU time is only about
   7% of the 28.6-ms mean control frame budget.
5. The worker-to-main bridge proxy remains 4.0--4.8 ms per frame (about
   14--17% of wall time). The remaining majority is CPU-side guest execution
   plus host command processing, not GPU rasterization.

## Consequence

GPU shader or texture optimization cannot by itself reach 50 FPS. The next
low-risk A/B is moving WebGL ownership from the main-thread proxy to the
Emscripten worker through an OffscreenCanvas-capable profile, if the current
BoxedWine/SDL bridge can support it. A CPU-engine replacement remains a later
gate, not a conclusion drawn from indirect evidence.
