# 139 Gate 2b: PatHouse loads and issues indexed 3D draws; room pixels still absent

Date: 2026-07-19

Status: **VERIFIED** for the observations below. The renderer-cause conclusion is
explicitly limited to the measured alternatives.

## Exact measured route

An isolated native BoxedWine / Wine 11 client used the already verified named
startup contract and Korean code page environment:

```text
Azrok.exe -NX 200 -NWND -PL d3d_scene -DIR localauth -IP 127.0.0.1:9200
LANG=ko_KR.EUC-KR
LC_ALL=ko_KR.EUC-KR
WINEDEBUG=+d3d9,+d3d
```

The normal client UI created a character. The preservation server then received
C2S `0x0004` and sent S2C `0x0003` containing `Data\\Space\\PatHouse`.
After the loading/tutorial panel, the client entered the PatHouse outer UI.
The captured result still has the purple fallback/UI canvas where the room is
expected, matching the reported symptom.

> **Route-equivalence caveat:** the exact required UI order (select one of the
> four Azrok characters, then create, name, and confirm) was clarified after
> this Wine 11 run. This run proves the scene response and draw behavior after
> creation, but is **NOT VERIFIED** as a strict version-comparison counterpart
> until Wine 11 is repeated with that exact UI order.

## Native-proxy limitation (VERIFIED)

The latest 128,512-byte `tools/d3d9_probe/d3d9.dll` was copied unchanged to the
guest mount. With `WINEDLLOVERRIDES=d3d9=n`, Wine logged `D:\\d3d9.dll` as a
native module, but no `d3d9_probe.log`, D3D device trace, or server connection
followed. Thus the existing Windows drop-in proxy cannot measure Wine with that
override: its intended system-D3D9 forwarding path is unavailable when Wine's
builtin D3D9 implementation is forbidden. No game binary was patched.

This is a limitation of this probe arrangement, not evidence that D3D calls are
absent. The Wine builtin trace below is the non-invasive fallback measurement.

## Builtin Wine D3D9 measurement (VERIFIED)

Counts below are for the short character-create-to-PatHouse sample (347
Presents), not the Gate 1 full-session baseline and therefore must not be used
as a duration-normalized performance comparison.

| Method | Gate 2b measured calls |
|---|---:|
| `CreateTexture` | 450 |
| `SetTexture` | 11,359 |
| `SetTextureStageState` | 51,187 |
| `SetRenderState` | 58,720 |
| `DrawIndexedPrimitive` | 573 |
| `DrawPrimitiveUP` | 10,294 |
| `SetFVF` | 12,006 |
| `SetVertexDeclaration` | 627 |
| `BeginScene` / `EndScene` | 346 / 345 |
| `Present` | 347 |

The final PatHouse frames repeatedly submit triangle-list indexed draws,
including `vertex_count=1087, primitive_count=2068`, plus several other
indexed meshes. No `CreateTexture` failure or `D3DERR_*` texture/device failure
was found in this trace.

The sampled 2,068-triangle draw has a non-null stage-0 texture and a vertex
declaration, and is issued with `D3DRS_ZENABLE` (`state 0x7`) set to `1`.
It precedes the subsequent UI `DrawPrimitiveUP` calls. This excludes the simpler
“no mesh draw”, “no bound texture object”, and “depth was globally disabled”
explanations, while still leaving texture alpha/colour-key, depth semantics,
and other WineD3D fixed-function translation details open. Gate 1 later
measured zero render-target/surface-switch calls for the complete route, so
the render-target/viewport branch is excluded (143).

The trace is 168,011,312 bytes, or about 484,182 bytes per `Present`. Therefore
the very low frame rate observed during this particular run is contaminated by
the deliberately exhaustive `+d3d9,+d3d` logging. It is valid for call-surface
classification, but not a native BoxedWine performance benchmark.

WineD3D selected the host `NVIDIA GeForce RTX 5090/PCIe/SSE2` OpenGL renderer
(`GL_VERSION 4.4.0 NVIDIA 610.62`) through GLX after its EGL attempt could not
load `libEGL.so.1`; this run is not using a software GPU renderer. The trace
also contains 816 repeated WineD3D invalid zero-width map warnings. Their
causal connection to the missing room is **NOT VERIFIED**, but they are a
specific compatibility signal to retain for the next renderer comparison.

## Decision from the Gate 1 differential

The first proposed branch, “no `DrawIndexedPrimitive` means `.wmb`/path load
failure,” is **excluded** for this route. The asset directory and server scene
response are present, and indexed geometry is submitted after entering the
scene.

It is **not yet proven** whether the missing room pixels are a transparent or
black texture, a depth/stencil/alpha-test issue, or another WineD3D
fixed-function state difference. The observed combination is therefore: scene
load and geometry submission pass; final room composition fails. The native
route's 70,045 `SetMaterial`, 6,415 `SetLight`, and 4,072 `LightEnable` calls
keep fixed-function lighting in the WineD3D hypothesis set; `SetGammaRamp` was
never called, so gamma is excluded. This does not compare the scene brightness:
WineD3D has no room image to compare, while Vulkan darkness is a separate
native-baseline fidelity question (143).

## Separate non-render findings

- The Korean environment changes Wine's active code page to 949. Some dynamic
  Korean text remains garbled and needs byte-level server/UI tracing; this is
  not a D3D conclusion.
- DirectSound effects are audible. Background music remains blocked by the
  guest Quartz/GStreamer dependency failure (`libpcre2-8.so.0`); this is
  independent of the PatHouse draw result.

## Evidence

- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_d3d_scene_0431_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_probe_force_native_0420_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/server_9200_hoststack_full_stdout.log`
