# 154 — Gate 1 argument checkpoint, minimal character-select scene

Date: 2026-07-19

## Scope

This is a Windows-native measurement, not gameplay QA. It used only the
character-selection scene, which visibly contains 2D UI and a 3D character.
Attempts to add PatHouse were stopped when the optional Frida queue request
timed out; no Plaza, minigame, cooking, library, or quest traversal occurred.

## Deployment and loader proof

**VERIFIED:** `d3d9_flushprobe.dll` was temporarily deployed as the workspace
`d3d9.dll`. Toolhelp recorded both the local proxy and the chained
`C:\Windows\SysWOW64\d3d9.dll`. After capture the selected Azrok PID was closed
and dgVoodoo was restored byte-exact:

```text
B7401378B2B8E8C18C88A033E77C3EE99F4C7D2AC8CFCC949D79C1DD7FA99767
```

## Partial checkpoint result

**VERIFIED:** the final checkpoint is explicitly partial:

```text
# flush: frame=133200 status=partial(mid-session, will be overwritten by next flush)
```

It contains 2D and 3D draws and the resource-interface hooks absent from the
older Gate 1 summary. It is valid for observed argument sets, not for
full-session call-total comparison.

| Measurement | Observed set |
|---|---|
| `SetRenderState` | 50 unique `(state,value)` pairs |
| `SetTextureStageState` | 158 unique `(stage,type,value)` tuples |
| `SetSamplerState` | 270 unique `(sampler,type,value)` tuples |
| `SetFVF` | 2 values: `0x00100312`, `0x000002C4` |
| `CreateTexture` | 43 dimension/level/format/pool tuples |
| texture formats | 21, 22, 23, 26 only |
| texture usage/pool | usage 0, pool 1 only |
| `DrawPrimitiveUP` | primitive types 4, 5, 6 |
| `DrawIndexedPrimitive` | primitive type 4 only |
| `SetTransform` | 64 distinct slots, **lower bound only** |

**VERIFIED negative for this scene:** no `D3DFMT_P8` and no DXT/FOURCC compressed
texture format occurred. The four numeric formats are ordinary uncompressed
D3D9 formats (`A8R8G8B8`, `X8R8G8B8`, `R5G6B5`, `A4R4G4B4`). This removes P8
and S3TC from the minimal boot/character renderer, but does not prove later
rooms never introduce them.

Resource calls now directly observed include texture `GetSurfaceLevel`,
vertex/index buffer `Lock`/`Unlock`, surface private-data/description methods,
vertex declaration `Release`, and query `Issue`/`GetData`. The browser drop-in
surface must include these even though the original 56-method Gate 1 report
did not hook all returned resource interfaces.

## Transform measurement correction

The only full table was `SetTransform` at 64/64. The captured values include
fixed slots 2/3 and world-matrix slots `256..317`, so at least **62 consecutive
world matrices** are exercised in this scene. This is not proof of more than
64 matrices, but it leaves only two slots of margin in the current WebGL2
shader placeholder `worldViewArray[64]`.

`XF_CAP` is now 512 and the x86 flushprobe was rebuilt. `dumpbin` verifies
machine `0x14c` and the sole export `Direct3DCreate9`. No immediate content
rerun is required: the backend should not hard-code the observed 64-slot
lower bound, and the next minimal native checkpoint can collect the expanded
distribution if shader array sizing still depends on it.

## Artifacts

- `artifacts/d3d9_probe/20260719_gate1_argflush_pathouse/d3d9_argflush_character_select.log`
- `artifacts/d3d9_probe/20260719_gate1_argflush_pathouse/loader_module_snapshot.json`
- `tools/d3d9_probe/d3d9proxy.cpp`
- `tools/d3d9_probe/d3d9_flushprobe.dll`

