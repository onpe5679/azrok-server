# Gate 2C: browser pointer-lock relative input

Date: 2026-07-22

## Result

- **VERIFIED (static):** Emscripten SDL already converts DOM `movementX/movementY` into SDL `xrel/yrel` while pointer lock is active. The old BoxedWine SDL input adapter discarded those relative fields and always forwarded absolute `x/y` with `relative=false`.
- **VERIFIED (implementation/build):** the BoxedWine SDL adapter now registers an asynchronous pointer-lock change callback and forwards scaled `xrel/yrel` as relative motion. `XServer::mouseMove()` accepts the relative flag in its raw-motion path and falls back to SDL's virtual absolute position when XI RawMotion is unavailable. No synchronous main-thread DOM query was introduced.
- **VERIFIED (browser visual):** the `boxedwine.pointer1` 1 GiB pthread build reaches the accepted PatHouse scene without carpet, wall, furniture, character, Korean-text, fatal, or OOM regression.
- **VERIFIED (test-surface limitation):** the Codex in-app browser accepted the fullscreen request but rejected both direct and post-fullscreen `canvas.requestPointerLock()` calls with `WrongDocumentError: The root document of this element is not valid for pointer lock.` The rejection happens before the BoxedWine pointer-lock callback can report an active lock.
- **NOT VERIFIED:** actual attach, sustained relative camera rotation beyond screen bounds, proportional deltas, reverse direction, Escape detach, and absolute-coordinate recovery require a standard browser surface whose root document permits Pointer Lock.

## Static path

1. `lib/sdl2/src/video/emscripten/SDL_emscriptenevents.c` receives DOM mouse events. Under pointer lock it scales `movementX/movementY` and sends SDL relative motion.
2. `platform/sdl/knativeinputSDL.cpp` now observes Emscripten pointer-lock state asynchronously, selects `e.motion.xrel/yrel`, and scales deltas without absolute-position offsets.
3. `source/x11/xserver.cpp` treats either `forceRelativeMouse` or the explicit relative flag as raw motion. Its non-XI fallback recovers SDL's maintained virtual absolute cursor before emitting ordinary grabbed motion.
4. `assets_d3d9web/boxedwine-shell.js` uses standard DOM Fullscreen and then requests pointer lock; the page no longer calls the non-exported `Module.requestFullScreen` runtime method.

## Build identity

- HTML SHA-256: `EEB2EB1BD84E7D275B78E1962B1DC1C303EBC3862F5B1A5CE7C2E1763F1F98EC`
- JS SHA-256: `CAA35FA4079A78BB49CF4E2EE58556E8577E8F28DC3CAF90C856CC4692DA066C`
- WASM SHA-256: `38A498BF9671707923DE3AA3E52AE386C5DA123C325278727D83BACEF616E64C`
- The WASM contains `D3D9WEB_POINTER_CALLBACK`, `D3D9WEB_POINTER_LOCK`, and `D3D9WEB_POINTER_MOTION` trace strings.

## Dynamic acceptance criteria

Do not accept camera motion alone as proof because Acknex anchors the cursor with `GetCursorPos/ScreenToClient` on left-button down.

1. Attach requires `document.pointerLockElement === canvas` and a BoxedWine `D3D9WEB_POINTER_LOCK active=1` callback.
2. While holding left mouse, send eight same-direction horizontal pulses totalling at least 1,600 CSS pixels. The last three pulses must still rotate at least 80% as much as the first three; none may become zero at a screen edge.
3. A 120-pixel pulse must rotate 1.6-2.4 times a 60-pixel pulse; reverse direction must reverse yaw.
4. Release the left button before Escape. Detach requires `pointerLockElement === null` and `D3D9WEB_POINTER_LOCK active=0`.
5. After detach, clicks at 10%, 50%, and 90% canvas coordinates must land within about 1% with no camera jump.

## Current blocker

Chrome-backed browser control was unavailable in this session, and browser-control policy forbids launching or repairing it without the user's permission. The in-app game session was closed before attempting the alternate surface, so no duplicate game instance was left running.
