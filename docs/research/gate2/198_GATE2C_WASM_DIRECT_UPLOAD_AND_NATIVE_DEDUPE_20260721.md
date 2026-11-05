# 198 Gate 2c WASM direct upload transport and native dedupe result

## Scope

All dynamic measurements used one browser tab, the saved-character automatic
PatHouse entry, and no gameplay input. No native game process was launched.
The corrected `UpdateSurface` scene from documents 196--197 remains the visual
reference.

## VERIFIED -- direct guest-memory upload transport

The proxy now sends a fixed 40-byte descriptor for resource uploads through
INT `0x9A` index `base+3`. BoxedWine validates the descriptor and copies the
payload from guest memory with compiled WASM code into the existing ordered
command batch. Draw/upload order and the Present flush boundary are unchanged.

The browser loaded `boxedwine.directupload1.{js,wasm}` and the paired
`Azrok_D3D9Web_pathouse_directupload1.zip`. PatHouse rendered intact walls,
carpet, furniture, character, and HUD. There was no direct-upload rejection,
bad resource upload, phase-6 error, or mapped exception.

Three PatHouse 120-Present windows measured 16.28, 18.12, and 20.42 FPS. Their
aggregate is 18.12 FPS, versus the clean corrected baseline of 13.01 FPS:

- FPS: +39.3% aggregate.
- frame time: 76.88 ms -> 55.18 ms.
- interpreted guest packet-copy: 2.191 s/120 frames -> 0.
- upload-call count and bytes remain about 2160 and 60.44 MB/120 frames; this
  change removes the guest construction loop, not the uploads themselves.

The three windows continued to warm up, so 18.12 FPS is the current aggregate,
not a claimed stable upper bound. It is still far below the 50 FPS gate.

## VERIFIED -- native exact dedupe rejected

A follow-up WASM prototype compared full VB/IB uploads with native
`KMemory::memcmp`, excluding `DISCARD` and `NOOVERWRITE`, and invalidating on
INIT/create/destroy. It suppressed 1801 uploads and 25.75 MB per 120 frames;
the host upload top then contained only changing VB 121 and VB 79 plus transient
textures. The scene remained visually intact.

Despite the real byte reduction, two PatHouse windows measured only 16.22 and
15.36 FPS. Full native comparisons plus shadow copies for changing buffers
cost more than the removed host work. Static review also found and corrected a
pre-append shadow update order and a missing pointer-overflow guard, but the
measured performance failure means the dedupe path is rejected regardless and
is not the active browser build.

## Active result and next measurement

The active single browser tab is returned to `directupload1`; native dedupe is
not selected. The next optimization gate must measure the remaining 55.18 ms
per-frame budget with a real time-based guest profiler. Instruction-count
samples from `normalCPU.cpp` are not time percentages. Prioritize Acknex CPU
animation/transform and interpreter opcode costs before additional WebGL state
caching, because host JS remains only about 0.32--0.39 s per 120 batches.
