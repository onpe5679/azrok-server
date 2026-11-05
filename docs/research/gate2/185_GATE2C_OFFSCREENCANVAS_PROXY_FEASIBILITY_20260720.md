# 185 Gate 2c OffscreenCanvas proxy feasibility (2026-07-20)

## VERIFIED

1. The current profile explicitly builds
   `-sPROXY_TO_PTHREAD=1 -sOFFSCREENCANVAS_SUPPORT=0`. It does not transfer
   the canvas to the worker.
2. Emscripten's `OFFSCREENCANVAS_SUPPORT=1` supports transfer of `Module.canvas`
   to the proxied pthread, and a dry-run make command produces the expected
   one-GiB `Build/OffscreenAB` link line with that flag enabled.
3. This is not a flag-only PatHouse optimization in the current design:
   the main DOM thread creates the D3D9Web WebGL2 runtime first, while the
   guest D3D batch dispatcher synchronously calls it with
   `MAIN_THREAD_EM_ASM_INT`. After transfer, main-thread canvas/context access
   is invalid and the worker has no D3D9Web runtime.
4. The Emscripten SDL path also forces a software renderer on the same canvas,
   so WebGL ownership must be separated or coordinated before a worker-local
   renderer can be correct.

## Consequence

The isolated transfer build is useful only as a boot/ownership smoke test. It
cannot prove a PatHouse performance improvement until three implementation
items exist: worker-side runtime/shader initialization, replacement of the
main-thread batch bridge with worker-local dispatch, and SDL canvas ownership
resolution. Do not claim the current 4--5ms proxy cost is removable by one
compiler flag.
