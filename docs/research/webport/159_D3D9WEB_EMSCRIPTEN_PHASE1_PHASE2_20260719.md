# 159 D3D9Web Emscripten Phase 1/2 — browser round trip

Date: 2026-07-19

> **WebGL2 follow-up completed by 160.** This document remains authoritative
> for the Phase 1/2 scalar round trip.

## Phase 1: host C++ -> JavaScript

**VERIFIED:** local Emscripten SDK 6.0.3 compiled a standalone `EM_JS`
control. C++ sent opcode 7 and `0x89ABCDEF`; JavaScript printed the exact
unsigned value and returned `0x5678` to C++. The process exited 0.

```text
D3D9WEB_PHASE1_JS opcode=7 value=0x89ABCDEF
D3D9WEB_PHASE1_CPP eax=0x00005678
```

## Phase 2: x86 PE -> BoxedWine -> JS -> x86 PE

**VERIFIED in the local browser:** the BoxedWine Emscripten release was rebuilt
with `BOXEDWINE_D3D9WEB`. The existing `INT 0x9A` decoder slot invokes
`callD3D9Web`; its Emscripten branch forwards the two copied 32-bit values to
JavaScript and returns the JS result in guest EAX.

The 32-bit PE guest and Wine were not mocked. Four seconds after launch, the
same browser console contained:

```text
D3D9WEB_PHASE2_JS index=0 arg1=0xA1B2C3D4 arg2=0x11223344
D3D9WEB_GUEST index=0 arg1=0xA1B2C3D4 arg2=0x11223344 eax=0x00001234
D3D9WEB_PHASE2_EXITCODE=0
```

This closes both transport questions from 147/150/153:

1. guest x86 PE can reach the host callback through `CD 9A`;
2. that callback can synchronously execute JavaScript and return a value to
   the guest.

The bridge does not require OpenGL, Vulkan, a new decoder enum, a guest Linux
module, a DeviceIoControl driver, or per-frame serialization.

## Build observations

- Official `emsdk latest` resolved to 6.0.3 on this date.
- The upstream Makefile needed a Windows-safe relative source/object mapping;
  no emulator semantics changed for that fix.
- First parallel compile raced while populating Emscripten SDL2/zlib ports.
  A one-time `-j1` build completed; subsequent incremental rebuild took about
  six seconds.
- A control smoke on the same custom WASM ran at 128–160 MIPS, separating the
  bridge from Wine background diagnostic noise.

## Artifacts

- `artifacts/web_backend/20260719_int9a_phase2/browser_evidence.txt`
- `tools/boxedwine_local/index_d3d9web_phase2.html`
- `tools/boxedwine_local/apps/D3D9Web_phase2.zip`
  - 65,656 bytes
  - SHA-256 `9D4125806B9482DB671391853E855AF627BF03DC58524617C1170CCF751AF63D`
- `tools/boxedwine_local/assets_d3d9web/boxedwine.js`
  - SHA-256 `3AE8ADFA813D9B759E5FB803DCC9B6F28CC281943C61F32E63B076C32E949375`
- `tools/boxedwine_local/assets_d3d9web/boxedwine.wasm`
  - SHA-256 `A97FCE184FDE2B5C48D261566C9F97B18299CA032C4A554C3713E9EA79865968`

## Next gate

Transport feasibility is complete. Document 160 completed index 1: JavaScript
obtained WebGL2 on the existing shared canvas, cleared it, drew one triangle,
returned `0x3001` to the guest, and exited 0. The next gate is a separate
minimal D3D9 COM object/vtable subset.
