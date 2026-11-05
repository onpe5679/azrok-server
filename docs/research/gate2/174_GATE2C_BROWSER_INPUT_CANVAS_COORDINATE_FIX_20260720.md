# 174 — Gate 2c browser input canvas coordinate fix (2026-07-20)

## Scope

This is a bounded input-path repair for the browser D3D9Web run. It does not
claim character creation or PatHouse entry success.

## VERIFIED observations

1. The browser game reached character selection with Wine's virtual desktop at
   `1024x768`, while the SDL/BoxedWine presentation canvas was `640x480` and
   the D3D9Web output canvas (`#d3d9web-canvas`) was `1024x768`, both drawn in
   the same CSS rectangle.
2. The previous browser input adapter read `Module.canvas` (`640x480`) and
   scaled pointer coordinates a second time into the `1024x768` guest
   desktop. A direct probe recorded this mismatch before the repair.
3. The adapter now selects `#d3d9web-canvas` when present and only falls back
   to `Module.canvas`. Direct browser input then recorded identical guest and
   D3D9 output coordinates: `raw=412,545`, `guest=412,545`,
   `logical=1024x768`, `canvas=1024x768`. The rendered in-game key cursor
   visibly moved to the same point.
4. Adding browser-only fields to `KNativeInputSDL` requires a clean
   Emscripten rebuild: the make dependency graph did not rebuild every TU that
   includes the class header on an incremental build. A clean MultiThreaded
   rebuild was performed before the final production build.
5. The final clean production `boxedwine.wsmulti.wasm` SHA-256 is
   `A5F034151BCE128993E27EAA3E171BF43ED6AA9DEF4FF9940D18D917C5510B3F`.

## NOT VERIFIED

- The browser-control automation's `click` operation produced movement but no
  `SDL_MOUSEBUTTONDOWN/UP` in the diagnostic build. This is a limitation of
  that automation route, not evidence about a physical user click. It must not
  be used to declare character creation failed.
- Character creation and PatHouse 3D rendering remain the next bounded user
  input/render gate.

## Changed implementation

- `platform/sdl/knativeinputSDL.cpp`: browser pointer conversion now uses the
  D3D9Web render canvas dimensions rather than the legacy SDL presentation
  canvas dimensions.
- `platform/sdl/knativeinputSDL.h`: stores the browser render-canvas
  dimensions used by that conversion.
- `tools/boxedwine_local/assets_d3d9web/boxedwine.wsmulti.{js,wasm}`: rebuilt
  clean production host assets.
- `tools/boxedwine_local/index_d3d9web_pathouse.html`: the `build` query value
  is now appended to the host-JS URL as well as the WASM URL, preventing a
  stale JavaScript loader from pairing with a newly rebuilt WASM module.
