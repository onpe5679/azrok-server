# 180 Gate 2c PatHouse indexed-cache measurement (2026-07-20)

## Scope

One browser session, existing slot-zero character, automatic normal PatHouse
bootstrap, 1024x768. This is a renderer performance measurement only; no
content QA was performed.

## VERIFIED

1. The fresh 1 GiB profile reached the original PatHouse 3D room and remained
   live long enough to display the floor, rugs, furniture, character, and HUD.
   This is direct browser-frame observation after the normal `0x0005` server
   selection route.
2. Eight stable 120-Present samples measured `fps_x100` of 2359, 2463, 2344,
   2412, 2226, 2215, 2255, and 2205: arithmetic mean **23.10 FPS**. The
   50-FPS target is therefore not met.
3. Every stable sample reported `upload_calls=120`,
   `upload_bytes=13072800`, and `upload_largest=10:2:108940`. The guest locks
   and uploads the same 108,940-byte kind-2 vertex buffer once per Present;
   the partial-upload ABI did not reduce this source range in this scene.
4. The experimental indexed cache reported `ib_hit=120, ib_miss=0`, but
   `vb_hit=0, vb_miss=120` on each stable 120-Present sample. It correctly
   reuses the index data, but cannot reuse a vertex buffer whose content
   version changes every frame. No FPS improvement is attributed to it.
5. Bridge proxy time was 0.719--0.794 seconds per 120 Presents (about
   14--16% of wall time). It is measurable but not the dominant limiter;
   optimizing only the worker-to-main proxy cannot plausibly turn 23 FPS into
   50 FPS.

## Next measured question

Determine why `handle=10` receives a full vertex-buffer lock each frame and
whether the cost lies in the guest's software x86 execution, the buffer copy,
or the application's genuine dynamic geometry. Do not add more renderer
caches until that direct lock/flag evidence is collected.
