# 212 Gate 2c x87 trace browser entry and release A/B

Date: 2026-07-21

## Scope

This is the browser gate for document 210's exact C++ trace helper. It uses
one tab at a time, closes each tab between builds, and compares two otherwise
identical counter-free 1 GiB release artifacts. The only dispatch difference
is `BOXEDWINE_D3D9WEB_X87_AOT`.

## VERIFIED -- rendering remains intact

Both release artifacts reached 1024x768 PatHouse through the existing
automatic entry path. Walls, doorway, carpet, table, stool, character face and
shadow, HUD, Korean text, alpha, and culling match the accepted reference.
There was no OOM, visible corruption, or browser exception.

## VERIFIED -- current PatHouse does not enter AA80

The helper emits one bounded first-entry marker named
`D3D9WEB_HOT_AOT enabled=FUN_1004a6d0_x87`. The page scans only newly appended
output and publishes `data-x87-aot-seen`. It remained `0` on character select
and after PatHouse was fully rendered with thousands of Presents. Therefore
the exact original `0x1004AA80` entry is not executed in this fixed scene.
Document 201's 16-byte bucket was valid hot-region evidence but did not prove
this exact entry.

## VERIFIED -- release numbers are noise, not x87 gain

Without x87 dispatch, five 5-second windows were 34.627, 33.240, 33.685,
34.654, and 33.002 FPS (mean 33.842). With optional x87 dispatch, five windows
were 33.433, 32.849, 34.242, 33.605, and 32.168 FPS (mean 33.260). Three later
10-second windows were 34.620, 34.194, and 33.629 FPS (mean 34.148).

Because the entry marker stayed zero, none of these differences can be
attributed to the helper. The current counter-free release band is roughly
33--34 FPS on this run, still far below 65 FPS.

## Decision

- Keep `hotAotX87Trace` and its exact differential oracle as reusable code.
- Keep dispatch behind `BOXEDWINE_D3D9WEB_X87_AOT`; do not enable it by
  default.
- Do not spend another browser session optimizing AA80 for this scene.
- Select the next candidate only from an exact entry observed in current
  PatHouse.

## Artifacts

- Baseline WASM SHA-256:
  `B697B4EFA9EB9A24DEBBE7D2DEF43C0D6CFF5704B4CA0D7FFB23C8851A6C71A3`
- Optional x87 WASM SHA-256:
  `DCB7C905C25B924DCB67D891F195F14B66FBA4F79DB81F4470EFFDAC14DF7D1D`
- Both browser sessions were closed; no game tab was left running.
