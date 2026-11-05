# 143 Gate 2b: fixed-function and OX hypotheses narrowed

Date: 2026-07-19

Status: **VERIFIED** Gate 1 call evidence and native OX baseline; Wine 11
Vulkan OX-exit cause remains **NOT VERIFIED**.

## Direct Gate 1 evidence

The completed native route (login, PatHouse, Plaza, natural OX round, cooking)
used the following D3D9 device methods:

| Method | Calls | Consequence |
|---|---:|---|
| `SetGammaRamp` | 0 | The WineD3D dark PatHouse image is not caused by a game gamma ramp. |
| `SetMaterial` | 70,045 | Fixed-function material semantics are active. |
| `SetLight` | 6,415 | Fixed-function light parameters are active. |
| `LightEnable` | 4,072 | Fixed-function light enable state is active. |
| `SetPaletteEntries` | 6 | Paletted texture / colour-key handling remains a renderer risk. |
| `Reset` | 2 | The complete native route uses Reset, but that alone does not attribute it to a room transition. |
| `TestCooperativeLevel` | 2 | The complete native route checks cooperative state. |

`SetRenderTarget`, `CreateRenderTarget`, `CreateDepthStencilSurface`,
`CreateAdditionalSwapChain`, and `StretchRect` were all uncalled. The game
therefore renders only to its implicit back buffer in this route; the former
render-target/viewport branch is excluded.

`SetVertexShader` and `SetPixelShader` were uncalled. This is a
fixed-function rendering path, not a custom-shader compatibility issue.

## Two renderer symptoms, kept separate

WineD3D/OpenGL (139) submits the room geometry but produces no room pixels.
Wine 11 Vulkan (141) produces the floor, rug, furniture, and character, but
the resulting scene is visually dark. These are separate observations:

- The WineD3D missing-room investigation determines whether the GL failure is
  a repairable WineD3D bug or a limitation relevant to a WebGL backend.
- The Vulkan darkness must be compared with the native Windows scene, not with
  WineD3D's absent room. The fixed-function material/light counts make DXVK
  ambient, diffuse, specular, and attenuation semantics candidates, but this
  is a visual-fidelity issue rather than the current browser-backend blocker.

Evidence: `artifacts/d3d9_probe/20260719_gate1/d3d9_probe_full_session.log`.

## OX server-contract exclusion

The Gate 2b Vulkan process disconnected immediately after the server's 14-byte
S2C `0x00C8` (142). That does **not** establish an incomplete OX server
contract: the same preservation server completed the native client sequence
`006B -> 006E -> C8 -> CC -> CE -> CA -> CB -> C9 -> 000D`, then returned to a
healthy Plaza in 122. Gate 1 also included a natural complete OX round.

Thus "incomplete post-C8 OX contract" is **excluded for this comparison**.
The remaining first-class causes are a guest-client exit or a
BoxedWine/Wine-Vulkan compatibility failure outside the server contract.

## Next direct measurement

The OX Reset measurement is now completed by 144: the successful second OX
entry has no D3D9 Reset or cooperative-level record, so Reset/device-loss is
excluded for that event. Determine whether the WineD3D missing-room result is
a repairable WineD3D bug or a GL-path limitation before selecting WebGL versus
WebGPU. Compare Vulkan darkness independently against the native Windows
scene.
