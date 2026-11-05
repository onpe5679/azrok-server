# 255. Gate 6 upstream WASM JIT proxy wake and valid PatHouse

Date: 2026-07-22 KST

## Result

- **VERIFIED:** The official BoxedWine WASM JIT tree at `C:\bwujit` can run the original Azrok client through character selection into an intact 1024x768 PatHouse scene.
- **VERIFIED:** The former splash/selection stall was not absence of the Azrok SOCKFS poll implementation. `knativesocket.cpp` already contained the browser track/poll/recv path.
- **VERIFIED:** The required execution topology is `-sPROXY_TO_PTHREAD=1 -sOFFSCREENCANVAS_SUPPORT=0`. Without it, the browser build received the server zone bundle but never produced the parser-driven client replies.
- **VERIFIED:** Enabling that topology exposed two Emscripten 6 compatibility defects in `boxedwine-wasm-jit-module-broker.js`: unmaterialized worker-pool arrays during preRun, and the obsolete string worker command `callHandler`. Treating absent arrays as empty and using numeric command `9` restored startup.

## Direct network proof

The corrected `boxedwine.upstreamjit5proxy` run produced the exact natural client sequence after the server zone bundle:

```text
09:27:35.508 C2S 0016
09:27:35.515 S2C 0016
09:27:35.520 S2C 0003 len=21
09:27:35.524 S2C 0007 len=472
09:27:35.529 S2C 0005 len=6
09:27:35.534 S2C 000A len=150
09:27:35.538 S2C 000B len=62
09:27:35.572 C2S 0017 len=6
09:27:35.578 C2S 0017 len=6
09:27:35.585 C2S 0008 len=41
```

This is direct proof that the guest parser and its socket/event wake resumed. The earlier dynamic classification of a missing FD_READ/poll implementation is superseded by the source/binary audit and this A/B.

## Visual and performance proof

- **VERIFIED:** Carpet, walls, furniture, character, Korean text, and the accepted D3D9 StateBlock path rendered without the old mip/culling/resource regressions.
- **VERIFIED:** Four real-`COMMAND.PRESENT` 10-second windows were 22.366, 28.794, 29.988, and 29.882 FPS. The last two warm windows average about 29.94 FPS.
- **VERIFIED:** Compared with the corrected custom-release baseline 23.295 FPS in document 254, the steady upstream-JIT result is about +28.5%, but it still fails the 50 FPS target.
- **INVALID AS GAME FPS:** The former non-proxy splash result around 174.8 FPS never entered the game and must not be used as a performance claim.

## Artifacts

- `C:\bwujit\project\emscripten\makefile`
- `C:\bwujit\project\emscripten\boxedwine-wasm-jit-module-broker.js`
- `tools/boxedwine_local/assets_d3d9web/boxedwine.upstreamjit5proxy.js`
- `tools/boxedwine_local/assets_d3d9web/boxedwine.upstreamjit5proxy.wasm`

## Next gate

Integrate the verified 44.1 kHz/BGM-loop path and correct the upstream SDL input mapping, then compare growable, growable-resizable-buffer, and fixed-1-GiB JIT builds using real Present timestamps and linear-heap headroom.
