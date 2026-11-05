# 193 Gate 2c PatHouse steady profile and carpet draw isolation

## Scope

Natural character selection (`C2S 0x0005`) into the browser D3D9Web
PatHouse scene, followed by eight consecutive steady 120-Present windows and
a one-frame pixel-change trace against the known-good Windows capture
`artifacts/dynamic-analysis/COOKING_QA_RESTART_PATHOUSE_STABLE.png`.

## VERIFIED — natural room entry and visual baseline

- The preservation server was run without automatic selection.
- The browser emitted natural `C2S #18 opcode=0x0005`; the server then sent
  `Data\\Space\\PatHouse`, `0x0007`, `0x0005`, `0x000A`, and `0x000B`.
- The browser visibly rendered the 1024x768 PatHouse floor, walls, furniture,
  character, and HUD. The former lobby selection text was absent.
- Walls, table, chairs, and character geometry were intact with the indexed
  static cache disabled.
- The rug differed from the known-good Windows capture: the native capture
  contains one large left rug, while the browser showed smaller repeated rug
  sections toward the lower/right part of that surface.

## VERIFIED — eight steady performance windows

The first transition window (`1327` packet copies, `84.3 MB`) was rejected.
The next eight windows had the same draw/resource structure: `1441` or `1442`
profiled guest copies, about `52.874 MB` guest packet bytes, `1921` or `1922`
host uploads, and about `53.190 MB` host upload bytes per 120 Presents.

Eight-window averages:

| Metric | Average per 120 Presents |
|---|---:|
| frame rate | 7.47 FPS |
| guest packet-copy timer | 1,280.6 ms |
| guest Present INT timer | 407.9 ms |
| bridge wall time | 16,107.6 ms |
| runtime-thread proxy time | 4,720.6 ms (29.31% of bridge wall) |

The host JS batch timer varied independently and is not substituted for guest
packet construction or the two guest/host copy boundaries.

## VERIFIED — unconditional static caching is invalid

The stable windows upload dynamic `VB 109` (`108,940` bytes) once per frame;
its upload version increases every frame. Other scene buffers also increase
versions every frame. This directly rejects the previous unconditional
"visually static scene" cache premise. Any future suppression needs exact
content equality and successful-upload lifetime evidence; a screenshot or
resource handle alone is insufficient.

## VERIFIED — the repeated rug is an actual FFP draw result

A bounded one-frame probe sampled cleared backbuffer pixels after each draw.
The clear baseline at all targets was `0,0,128,0`, so the repeated rug is not
a stale color/depth remnant.

The normal and repeated regions are produced by separate original
`DrawPrimitiveUP` calls, all with FVF `0x100312`, stride 52,
`D3DPT_TRIANGLEFAN`, stage 0 texture 48, stage 1 texture 55, WRAP/WRAP,
TEXCOORDINDEX `0` and `1`, and TTFF disabled:

- expected rug pixel: triangle fan primitive count 2;
- repeated edge pixel: triangle fan primitive count 5;
- repeated lower pixel: triangle fan primitive count 3.

The native Wine/D3D trace contains the same triangle-fan counts and stride 52,
so deleting the later fans would incorrectly remove original geometry. The
difference is in how the multiple UV-atlas regions are sampled/composed.

## VERIFIED — global 3D V flip is rejected

An isolated A/B flipped passthrough V only for non-POSITIONT vertices. It
reduced the rug repetition but visibly inverted the character face and broke
floor/furniture lighting and colors. The experiment was rejected; a global
3D V conversion is not content-correct.

## NOT VERIFIED — stage-specific V convention A/B rolled back

The rug trace distinguishes stage 0 dynamic-atlas coordinates from stage 1
repeating-material coordinates. A stage-1-only V A/B was prepared after
restoring stage 0, but its cold browser session did not complete the local
loading screen in the bounded run. With no visible PatHouse proof, the shader
change was rolled back rather than retained.
