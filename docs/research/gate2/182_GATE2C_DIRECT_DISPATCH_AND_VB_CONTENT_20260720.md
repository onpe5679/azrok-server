# 182 Gate 2c direct dispatch and vertex-buffer content (2026-07-20)

## Scope

Separate 1 GiB Emscripten build with `BOXEDWINE_DIRECT_NORMAL_DISPATCH`,
normal automatic `Data\Space\PatHouse` server bootstrap, 1024x768, and one
bounded browser measurement. No gameplay QA.

## VERIFIED

1. The direct-dispatch build compiled into a separate `boxedwine.direct`
   profile and reached the normal PatHouse protocol bootstrap. It rendered
   in-world Azrok frames without browser console errors.
2. Ten stable 120-Present samples measured 25.60, 23.87, 25.74, 22.80, 23.64,
   23.66, 24.53, 22.67, 24.00, and 22.58 FPS: mean **23.91 FPS**.
   The prior standard profile measured 23.10 FPS under the same scene gate.
   This ~0.81 FPS / 3.5% delta is far below the 50-FPS target and is not
   promoted as a sufficient optimization.
3. The first eight handle-10 vertex-buffer locks were all
   `offset=0`, `requested=0`, `resolved=108940`, and `flags=0x800`.
   Windows SDK `d3d9types.h` defines `0x800` as `D3DLOCK_NOSYSLOCK` (not
   `DISCARD` or `NOOVERWRITE`).
4. Their 32-bit full-buffer FNV-1a hashes were `73777015` three times,
   `7a83b787` twice, then `8ba86af4`, `2b9483a9`, and `2da8e7c6`.
   Thus this buffer is not safely identical across the observed sequence;
   unconditional guest-side upload suppression would be incorrect.
5. Stable upload volume and cache behavior remain unchanged:
   13,072,800 bytes / 120 Presents, one full handle-10 VB upload per Present,
   `vb_hit=0/vb_miss=120`, and `ib_hit=120/ib_miss=0`.

## Decision

The small interpreter-dispatch change and the initial unchanged-buffer
hypothesis are both insufficient routes to 50 FPS. The next investigation must
measure a larger CPU execution change (JIT feasibility or a much cheaper guest
execution engine) before altering rendering semantics.
