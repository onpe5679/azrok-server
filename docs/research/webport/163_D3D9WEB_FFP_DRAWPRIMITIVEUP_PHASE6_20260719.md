# 163 D3D9Web Phase 6 — measured-FVF DrawPrimitiveUP through the real FFP backend

Date: 2026-07-19

## Result

**VERIFIED in the local browser:** the real x86 drop-in `d3d9.dll` now implements
the first measured `IDirect3DDevice9` state/draw subset. A synthetic PE submitted
the game-observed `FVF 0x000002C4` (`XYZRHW | DIFFUSE | SPECULAR | TEX2`) with a
40-byte stride and three vertices through `DrawPrimitiveUP`.

The call crossed this complete path synchronously:

```text
x86 client -> d3d9.dll COM vtable -> INT 0x9A command packet
-> BoxedWine guest-memory copy -> JavaScript command/state runtime
-> existing driver-tested std140 packer + D3D9 FFP uber shaders
-> WebGL2 drawArrays(TRIANGLES)
```

The browser visibly rendered a large interpolated triangle on the shared 800x600
canvas. Its red, green, and blue vertices match the three guest D3DCOLOR values,
which directly validates the required little-endian BGRA-byte to WebGL RGBA
attribute swizzle rather than merely proving that a draw call returned success.

```text
D3D9WEB_PHASE6_FFP_INIT webgl2=1 shader=driver-linked blocks=5
D3D9WEB_PHASE6_DRAW up=1 fvf=0x2C4 primitive=4 vertices=3 stride=40 bgraSwizzle=1
D3D9WEB_PHASE6_PRESENT draws=1 fvf=0x2C4
D3D9WEB_PHASE6_STATE fvf=0x000002C4 stride=40 viewport=800x600 scissor=800x600 setters=20 result=PASS
D3D9WEB_PHASE6_COM create9=1 createDevice=0x00000000 clear=0x00000000 begin=0x00000000 drawUP=0x00000000 end=0x00000000 present=0x00000000
D3D9WEB_PHASE6_RESULT=PASS
D3D9WEB_PHASE6_EXITCODE=0
```

No Azrok content was launched for this gate.

## Implemented device subset

The synthetic device vtable now binds exact x86 WINAPI signatures for:

- slot 44 `SetTransform`;
- slots 47/48 `SetViewport` / `GetViewport`;
- slot 57 `SetRenderState`;
- slot 67 `SetTextureStageState`;
- slot 69 `SetSamplerState`;
- slots 75/76 `SetScissorRect` / `GetScissorRect`;
- slot 83 `DrawPrimitiveUP`;
- slot 89 `SetFVF`.

Viewport and scissor getters are guest-local echoes and therefore perform no
JavaScript round trip. The smoke submitted twenty setters and asserted exact
800x600 viewport/scissor round trips before drawing.

## Host/backend integration

`tools/web_backend/host/d3d9web-runtime.js` is the new narrow owner of command
decoding and WebGL objects. It reuses without duplicating:

- `createDefaultState()` from `ffp-state.js`;
- `packAll()` and runtime driver offset queries from `pack-ffp.js`/`std140.js`;
- the existing `d3d9_ffp.vert` / `d3d9_ffp.frag` shaders.

The runtime links those shaders on the actual browser driver, binds all five
uniform blocks and sixteen dummy sampler targets, maps the measured FVF to the
fixed 16-attribute shader contract, uses buffer orphaning for every UP draw,
and handles D3D top-left `XYZRHW` viewport conversion.

The BoxedWine handler copies packet bytes from the guest virtual address into a
temporary WASM-native buffer before invoking JavaScript. JavaScript copies the
packet once more before the native buffer is released, so no guest or temporary
pointer escapes the synchronous call.

## Boundaries

- This proves the state/FVF/UP-byte/FFP-shader path, not the resource path.
- `CreateTexture`, texture Lock/Unlock/SetTexture, VB/IB objects, and indexed
  drawing are still absent.
- Phase 6 uses dummy white textures; sampler values are guest-shadowed but not
  yet applied to real texture objects.
- Only the measured `XYZ` and `XYZRHW` base layouts plus diffuse/specular and
  ordinary texture-coordinate counts are decoded. Additional FVF forms remain
  demand-driven.
- Render-state coverage is deliberately the smoke subset; full Gate 1 state
  semantics remain incremental.

## Artifacts

- `tools/d3d9_web_backend/d3d9_web.cpp`
- `tools/d3d9_web_backend/bootstrap_client.cpp`
- `tools/web_backend/host/d3d9web-runtime.js`
- `tools/boxedwine_local/index_d3d9web_phase6.html`
- `tools/boxedwine_local/apps/D3D9Web_phase6.zip`
  - 70,426 bytes
  - SHA-256 `3636AFD1761A6AC1882D12C137A66FB6A865959D587233F8C86E72A0286C7605`
- `tools/d3d9_web_backend/d3d9_web.dll`
  - 7,168 bytes
  - SHA-256 `08A084391299D347743EEB426B20625522B1C0B3FDC1019BA9F9075F7B773903`
- `tools/d3d9_web_backend/bootstrap_client.exe`
  - 120,320 bytes
  - SHA-256 `33656C907B0F69CB7B97A9F035C334359EDCFD6A538D156A2D5FD5F37C7EE363`
- `artifacts/web_backend/20260719_d3d9_drawup_phase6/browser_evidence.txt`
- `artifacts/web_backend/20260719_d3d9_drawup_phase6/webgl2_drawup_triangle.png`
  - 32,873 bytes
  - SHA-256 `11ED3D8EFB20A8965EC4AC757AE273A3C484B5F770B89C611DBAF76017F382CA`

## Next gate

Implement CPU-backed texture/VB/IB COM objects and their Lock/Unlock paths,
then connect `SetTexture`, stream/index binding, `DrawPrimitive`, and
`DrawIndexedPrimitive`. Only after that synthetic resource gate passes should
Azrok be launched for one bounded PatHouse rendering proof. Do not resume broad
content QA.

