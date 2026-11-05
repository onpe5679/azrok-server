# 190 — Gate 2c PatHouse scene-state and static-cache regression

## Scope

Browser D3D9Web PatHouse visual QA after the user reported a repeated carpet,
the persistent `캐릭터를 생성해주세요` text, low frame rate, and then a
wall/furniture regression during the first cache experiment.

## VERIFIED — selection text is not a PatHouse HUD element

`docs/research/_salvage/symbols/plaza_dump.txt`,
`thunk_FUN_005ebbd0` (`004dc3ed`), iterates four lobby slots.  For a slot
whose `char_table[2 + slot] == -1`, it draws `DAT_006ad5f0` at screen Y
`0x24e`; these are exactly the three lower-screen empty-slot labels seen in
the browser capture.

The active browser session's packet log also directly shows the opt-in server
route sending S2C `0x0003(Data\\Space\\PatHouse)`, `0x0007`, `0x0005`,
`0x000A`, and `0x000B` after heartbeat 9, while no C2S `0x0005` selection
packet appears in that capture.  Therefore the current automatic server
continuation can put the client in the room without the client's local lobby
selection layer having retired.  Hiding the text in the renderer would be an
incorrect workaround.

**Status:** VERIFIED source and wire behavior; NOT VERIFIED that one physical
pointer selection clears the layer in the current browser input package.

After this finding, the local preservation server was restarted without
`--auto-select-existing`.  A fresh browser session now reaches lobby heartbeat
9 with only the normal S2C heartbeat replies; the prior unsolicited PatHouse
bundle is absent.  This is the clean baseline for the next one-click physical
selection check.

## VERIFIED — cache experiment regression and rollback

The first static indexed-geometry cache (`staticcache1`) changed indexed draws
from one scratch WebGL buffer to multiple cached `WebGLBuffer` objects but
left `configureVertexInput`'s signature constant as `indexed`.  A WebGL VAO
retains the `ARRAY_BUFFER` selected by `vertexAttribPointer`, so a later draw
could use a new index buffer with attributes still pointing to an old vertex
buffer.  The resulting browser image had missing walls and furniture rendered
as character-like fragments.

The attribute-signature omission was corrected, then the entire static-cache
path was disabled in the live runtime (`staticcache3rollback`) pending an
isolated full-scene test.  The rollback build passes `node --check`, starts
the original client, reaches the normal character-selection renderer, and has
no `D3D9WEB_PHASE6_ERROR` at startup.  No performance result is retained from
the rejected cache path.

## VERIFIED — current measured performance boundary

In the visible PatHouse transition, a 120-Present sample reported
`fps_x100=974` (9.74 FPS), 362 batches, 53.2 MB uploads, and 27.7% bridge
time.  The immediately preceding initial-selection samples were 30--40 FPS
and are not a PatHouse measurement.  The 50-FPS target remains **NOT
VERIFIED**; performance work is paused until the content-correct PatHouse
route is restored.

## Next direct checks

1. Launch a fresh no-auto-select server session and use only the natural C2S
   `0x0005` path; verify that the three lobby labels disappear before judging
   render defects.
2. On that content-correct scene, trace indexed draw tuple/vertex data for
   the carpet and furniture rather than changing sampler or cache behavior by
   inference.
3. Only after pixel comparison against
   `artifacts/dynamic-analysis/COOKING_QA_RESTART_PATHOUSE_STABLE.png`, take
   a fresh 120-Present performance baseline.
