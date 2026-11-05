# Gate 6: current package performance recomposition

Date: 2026-07-28 KST

## VERIFIED

- The current private in-app-browser run used one visible 1024x768 CSS
  PatHouse scene, the ABI-matching replay (`94` groups, `30,550` blocks,
  `28,944` patches), and an unmuted, unpaused original `PetHouse.mp3` fallback.
- `Azrok_D3D9Web_pathouse_recompose1` with `pool`, `shaderColor`, and
  `upRing` produced **1,243 Presents / 30.001 s = 41.4319 FPS**.  Its mutually
  exclusive DrawUP batch replacement produced **1,245 / 30.0005 s = 41.4993
  FPS**.  The 0.0674-FPS difference is not a meaningful route to the 50-FPS
  gate, so DrawUP batch is not adopted.
- `Azrok_D3D9Web_pathouse_guesttexrecycle4` has a different guest `d3d9.dll`
  from `recompose1` (24,576 bytes,
  `2C5CEE49D2C06831C33581EBF16DE21B3EC1CB3F23B4BC2CEE5F42878D38E2A0`, versus
  25,600 bytes,
  `8561D893D08851BBDC8627D67F7624446E57590EB1CFE7473660EA9EFCB14F0D`).
  With the prior host companion flags it rendered the same visible PatHouse
  scene with BGM and measured **1,296 / 30.0014 s = 43.1980 FPS**.  This is
  better than the current recompose route but still below the target.
- The historical 51.2849/55.0276 records used `guesttexrecycle4`, the same
  accepted replay and a dedicated Edge instance with all three anti-throttling
  flags.  The lean-only in-app-browser repetition measured **1,258 / 30.0005
  s = 41.9326 FPS**, so the historical record is not currently reproducible in
  this browser surface and is not counted as current 50-FPS completion.

## NOT VERIFIED

- Three stable, direct-Present, BGM-enabled PatHouse windows at or above 50
  FPS.
- Whether the remaining difference is entirely the browser process launch
  contract or a guest/host code-path regression.  A new isolated desktop
  browser process could not be launched by the current execution policy; this
  is an environment boundary, not a performance conclusion.
