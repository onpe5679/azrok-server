# 187 — Gate 2c browser input source-coordinate repair

Date: 2026-07-20

> **SUPERSEDED by 188.** The claimed clean browser build later reproduced a
> Wasm `operation does not support unaligned accesses` exception before a
> usable game frame, so its runtime-success conclusion is withdrawn.

## Finding — VERIFIED

The browser DOM input source is `Module.canvas`, not the D3D9Web output
overlay:

1. `Browser.getCanvas()` and the Emscripten mouse-event conversion use
   `Module.canvas`. The live selection page measured that source at 640x480.
2. The D3D9 overlay has `pointerEvents = 'none'`; it cannot receive DOM mouse
   events.
3. The stale `boxedwine.wsmulti` and `boxedwine.inputtrace` Wasm builds
   embedded `d3d9web-canvas || Module.canvas` as the denominator used by
   `KNativeInputSDL::xFromScreen/yFromScreen`.
4. The guest desktop is 1024x768. Treating a raw 640x480 SDL coordinate as
   one already in the 1024x768 output space leaves it only 62.5% of the way
   across/down the desktop. This matches the reported game cursor lying above
   and left of the physical pointer.

The corrected input source policy is therefore:

```text
DOM event -> Module.canvas raw (640x480) -> guest desktop (1024x768)
```

The D3D output canvas is a renderer target only; it is not an input-coordinate
reference.

## Implementation — VERIFIED build contents

`platform/sdl/knativeinputSDL.cpp` already contains the corrected
`Module.canvas`-only `MAIN_THREAD_EM_ASM_INT` queries. The issue was that the
browser-selected `wsmulti/inputtrace` assets predated that source correction.

A clean `Build/InputFix` Emscripten build was made with the existing browser
configuration:

- `-DBOXEDWINE_MULTI_THREADED -pthread`
- `-DBOXEDWINE_D3D9WEB_PROFILE`
- `-sPTHREAD_POOL_SIZE=32 -sPROXY_TO_PTHREAD=1`
- `-sOFFSCREENCANVAS_SUPPORT=0`
- 1 GiB initial memory.

Its generated JS embeds only:

```js
const canvas = (typeof Module !== 'undefined') ? Module.canvas : null;
return canvas ? canvas.width : 0;
```

The generated `boxedwine.js/.wasm` pair was copied byte-for-byte into both
browser-selected asset pairs:

```text
assets_d3d9web/boxedwine.wsmulti.{js,wasm}
assets_d3d9web/boxedwine.inputtrace.{js,wasm}
```

The page cache token is now `inputfix1` for both JS and Wasm loads, so an old
`batch1` browser cache cannot silently retain the bad coordinate policy.

## Dynamic boundary check — VERIFIED, limited

A fresh `inputtrace=1` browser run loaded the new one-GiB asset and reached
the original selection UI. A mouse move/click sequence reached the game's
delete-confirmation modal; Escape dismissed it, so no character data changed.
This proves the browser-to-guest click transport is live after the rebuild.

The Codex CUA coordinate system is not a substitute for the user's physical
pointer calibration. The remaining live check is one ordinary user mouse
hover/click in the same session, then a PatHouse screenshot. No additional
content QA is required.
