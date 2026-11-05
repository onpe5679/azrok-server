# 164 D3D9Web Phase 7 — texture, VB/IB, and DrawIndexedPrimitive

Date: 2026-07-19

## Result

**VERIFIED in the local browser:** the x86 drop-in now creates CPU-backed
`IDirect3DTexture9`, `IDirect3DVertexBuffer9`, and `IDirect3DIndexBuffer9`
objects, transports their bytes through the existing `INT 0x9A` bridge, binds
them in the WebGL2 runtime, and executes `DrawIndexedPrimitive`.

The bounded synthetic gate used a directly observed Gate 1 texture tuple:

```text
CreateTexture(8, 8, 1, usage=0, format=23/R5G6B5, pool=1/MANAGED)
```

VB/IB creation arguments remain synthetic design choices because the current
argument probe did not histogram those creation/Lock arguments. The draw used
the measured `FVF 0x2C4`, 40-byte stride, `D3DPT_TRIANGLELIST`, three vertices,
and a 16-bit `[0,1,2]` index buffer.

The browser output was not accepted on HRESULT/log evidence alone. The runtime
read four pixels back from the rendered checker-textured triangle:

```text
D3D9WEB_PHASE7_PIXELS red=255,0,0,255 green=0,255,0,255
  blue=0,0,255,255 white=255,255,255,255 result=PASS
D3D9WEB_PHASE7_RESOURCE tex=23/8x8/128 pitch=16 lock=PASS
  vb=120/40 lock=PASS ib=6/index16 lock=PASS
  source=texture-observed,vb-ib-synthetic
D3D9WEB_PHASE7_COM createTex=0x00000000 createVB=0x00000000
  createIB=0x00000000 bindTex=0x00000000 bindStream=0x00000000
  bindIndices=0x00000000 dip=0x00000000 present=0x00000000
D3D9WEB_PHASE7_RESULT=PASS
D3D9WEB_PHASE7_EXITCODE=0
```

No Azrok content was launched.

## Guest COM and transport

The following measured device slots are now bound with exact x86 WINAPI
signatures: 23 `CreateTexture`, 26 `CreateVertexBuffer`, 27 `CreateIndexBuffer`,
65 `SetTexture`, 82 `DrawIndexedPrimitive`, 100 `SetStreamSource`, and 104
`SetIndices`.

Texture, VB, IB, and surface vtables are populated through their complete
resource subsets. The synthetic gate directly exercised Texture `LockRect` /
`UnlockRect`, VB/IB `Lock` / `Unlock`, resource `Release`, binding, and indexed
draw. `GetLevelDesc`, `GetSurfaceLevel`, and the embedded surface vtable are
implemented because Gate 1 measured those calls even though this smoke did not
need them.

Commands 12–19 extend the bridge ABI with resource create, chunked upload,
destroy, texture/stream/index binding, and indexed draw. Upload chunks are
validated for exact handle/kind/total/offset continuity before acceptance.

## Host/WebGL2 mapping

The host keeps handle-keyed raw resource shadows and stage-specific WebGL
sampler objects. Texture upload supports all four uncompressed formats seen in
the minimal Gate 1 argument probe:

- 21 `A8R8G8B8`: BGRA bytes to RGBA8;
- 22 `X8R8G8B8`: BGRX bytes to RGBA8 with alpha forced to 255;
- 23 `R5G6B5`: little-endian words to RGB565;
- 26 `A4R4G4B4`: ARGB nibbles rotated to WebGL RGBA4.

The verified smoke used format 23. Formats 21/22/26 are implemented from the
verified SDK layout but still need their own pixel fixtures if they become a
failure site.

Indexed drawing validates vertex/index ranges, honors stream offset/stride,
rebases signed `BaseVertexIndex` on the CPU, applies the same D3DCOLOR swizzle
verified in Phase 6, and calls `drawElements` with the mapped index type.

## Boundaries found by parallel static/dynamic review

- **VERIFIED:** the Gate 1 character-select log contains `levels=4` texture
  creation tuples. The current guest object accepts only level 0/1 and therefore
  cannot yet run that real scene.
- **VERIFIED:** real indexed 3D calls pair with `SetVertexDeclaration`; the
  current host indexed path accepts FVF only.
- Device/resource cleanup across device recreation, strict IID filtering, and
  transport-failure rollback remain hardening tasks.
- Partial Locks currently upload the full CPU shadow. This is correct but not
  performance-final.
- The BoxedWine build still contains an earlier OX unmap trace; its unrelated
  startup messages are not evidence for this gate.

## Artifacts

- `tools/d3d9_web_backend/d3d9_web.cpp`
- `tools/d3d9_web_backend/bootstrap_client.cpp`
- `tools/web_backend/host/d3d9web-runtime.js`
- `tools/boxedwine_local/index_d3d9web_phase7.html`
- `tools/boxedwine_local/apps/D3D9Web_phase7.zip`
  - 74,173 bytes
  - SHA-256 `FFEF668D82FA501E91E6CE5843ADFF3C0D0533949923DB69BA13C899F53DF0EB`
- `tools/d3d9_web_backend/phase7_package/d3d9.dll`
  - 11,776 bytes
  - SHA-256 `B2F9563982BA442A3921EE4425F534C6C2F1CFF64BD9F0199C36F61A19AED2A3`
- `tools/d3d9_web_backend/phase7_package/bootstrap_client.exe`
  - 122,880 bytes
  - SHA-256 `D54F8A17150B1E17DF4527B9252A51ACE5E2FC735C813CEDF0479E4FC816F870`
- `artifacts/web_backend/20260719_d3d9_resources_phase7/browser_evidence.txt`
  - SHA-256 `7501B49F1B43F157E0AACB4519D500AABC0EDACA72CD7FA07D7AA9937EC2CD46`
- `artifacts/web_backend/20260719_d3d9_resources_phase7/webgl2_texture_vbib_indexed.png`
  - 33,631 bytes
  - SHA-256 `3F835B913B81FD511BB1FAA8EB564ED62648089F5E5A3556F739E727E774FE57`

## Next gate

Implement level-specific mip layout/Lock/desc/surface upload and the measured
vertex-declaration path. Then launch only the minimum real client scene needed
to prove rendering, with PatHouse as the first and normally final content gate.
