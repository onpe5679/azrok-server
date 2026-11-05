# 166 D3D9Web Phase 9 — pre-PatHouse upload, lifecycle, light, and query surface

Date: 2026-07-19

## Result

**VERIFIED in the local browser:** the remaining Gate 1 device calls required
before a bounded PatHouse launch now have concrete x86 COM implementations, and
the real Acknex texture upload shape now crosses the complete guest COM →
`INT 0x9A` → JavaScript → WebGL2 path.

```text
D3D9WEB_PHASE9_LIFECYCLE ... mode=800x600 cursor=0/1 backbuffer=800x600 reset=640x480 passes=1 palette=0x00000000 result=PASS
D3D9WEB_PHASE9_SURFACE level=2 size=2x2 pitch=4 value=0x1234 result=PASS
D3D9WEB_PHASE9_STATE material=1 light=1 enable=1 active=1
D3D9WEB_PHASE9_LIGHT ... result=PASS
D3D9WEB_PHASE9_QUERY type=4 size=16 issue=0x00000000 data=0x00000000 pattern=0x48434143 result=PASS
D3D9WEB_PHASE7_PIXELS red=255,0,0,255 green=0,255,0,255 blue=0,0,255,255 white=255,255,255,255 result=PASS
D3D9WEB_PHASE9_RESULT=PASS
D3D9WEB_PHASE6_EXITCODE=0
```

No Azrok content was launched.

## Static correction: LockRect zero counts were not absence proof

**VERIFIED static with Ghidra MCP:** `acknex.dll` function `FUN_1002CD50`
creates the BMAP texture, calls texture slot 18 `GetSurfaceLevel` for each mip,
passes the returned surface into its embedded image decoder, and releases it.
`FUN_1009F3ED` calls surface slot 12 `GetDesc`, slot 13 `LockRect`, writes the
decoded WIS pixels, and later unlocks. The public BMAP lock/unlock path also
directly calls texture slots 19/20.

Therefore the probe report saying Texture/Surface LockRect was called zero
times cannot be used as an API-absence proof. Its per-interface first-vtable
hook guard can miss a different surface implementation/vtable used inside the
embedded D3DX path. `UpdateTexture=0` remains valid, but pixel upload is via
`GetSurfaceLevel → Surface::LockRect/UnlockRect`.

Phase 9 directly exercises that exact COM shape on mip 2, writes sentinel
`0x1234`, unlocks through the Surface, then reads the same CPU backing through
Texture LockRect. The upload command reaches WebGL2 successfully.

## Lifecycle and query surface

The following directly called Gate 1 device slots are now filled and exercised:

- TestCooperativeLevel, GetAvailableTextureMem, GetDirect3D, GetDeviceCaps,
  GetDisplayMode, ShowCursor.
- Reset and implicit mono GetBackBuffer with a stable Surface COM object and
  dimensions/format following the presentation parameters.
- SetMaterial, SetLight, LightEnable, BeginStateBlock, ValidateDevice,
  SetPaletteEntries, and CreateQuery.

**VERIFIED static with Ghidra MCP:** `FUN_1008E0E1`/`FUN_1008EDD7` use query
type 4 (`D3DQUERYTYPE_VCACHE`), including a null-output capability probe,
object creation, `Issue(D3DISSUE_END)`, and 16-byte `GetData` with FLUSH. The
implementation now returns the correct 16-byte `D3DDEVINFO_VCACHE` shape with
`Pattern='CACH'`; the original four-byte placeholder was rejected by this gate.

## Transform and state transport

- World/View/Projection and texture transforms remain in D3D row-vector
  convention and are converted to GLSL storage only at the shader boundary.
- SetTransform marks narrow dirty categories. Matrix composition is deferred
  until a draw instead of doing work for every setter.
- View changes rebuild only the existing blend matrices and camera-space light
  values. Individual world-palette or texture-stage changes update only their
  affected entries.
- The 16 KiB 256-matrix blend UBO and clip-plane UBO are no longer rebuilt and
  uploaded on every unchanged draw. Other FFP blocks remain conservatively
  uploaded per draw pending profiling.
- Material/light packets are ABI-checked by their exact 72/112/16-byte host
  parsers; invalid light index 8 returns `D3DERR_INVALIDCALL` in the guest.

## Direct failure retained

The first Phase 9 run loaded the Phase 8 copy of `d3d9web-runtime.js` from the
local harness staging tree and rejected commands 22–24 as unknown. This was a
harness publication error, not a guest ABI failure. The served host runtime was
replaced with the current source, its SHA matched, and a versioned module URL
forced a fresh browser load. The immediate rerun produced the PASS evidence
above. The failed run is not used as success evidence.

## Artifacts

- `tools/boxedwine_local/apps/D3D9Web_phase9.zip` — 77,980 bytes — SHA-256
  `DFBD4446D191117CF4C419B55940FA3320DEE51103C09F6B917F6A2214711F1B`
- `tools/d3d9_web_backend/d3d9_web.dll` — 14,848 bytes — SHA-256
  `E3BBE35AF4DBE396CB86C7860541E33BA8AEA1FBA00C60ED23FE3682718B1141`
- `tools/d3d9_web_backend/bootstrap_client.exe` — 126,464 bytes — SHA-256
  `3D34015507D9F425B52B9054A25217876AE2725AA2EA7A8DB1C1DD79661352E0`
- `artifacts/web_backend/20260719_d3d9_pre_pathouse_phase9/browser_evidence.txt` —
  6,158 bytes — SHA-256
  `9DB87666A40660FB49D5A4BEE81249B4F350A2D27BF22F523CE215E5AC972B2D`
- `artifacts/web_backend/20260719_d3d9_pre_pathouse_phase9/webgl2_phase9_triangle.png` —
  33,955 bytes — SHA-256
  `E553B8AC4BEE24E025490CFF0B1F3EDFD883E16C9FD6B84B74FC2F5DB0874861`

## Next gate

The next launch is the first real-client proof and is capped at PatHouse. Its
only purpose is to determine whether the original binary reaches and renders
one 3D room through the new backend. Plaza is optional only if PatHouse passes
without a new API/format gap; broad content QA remains out of scope.
