# 492 Gate 6 current in-app-browser mobile viewport rejection (2026-07-28)

## Direct result

- **VERIFIED:** the Browser viewport capability was explicitly set to
  `390x844` before opening a fresh `mobileCapture=1` game session.
- **VERIFIED:** the page nevertheless reported `window.innerWidth=1280`,
  `window.innerHeight=720`, DPR 1, body width 1265, and a displayed
  `1024x768` canvas.  The captured visible page likewise remained desktop
  geometry.
- **VERIFIED:** this fresh session did render and its BGM containment route
  was `playing` through `media-element`, but its `FPS 191.0` is desktop data.

## Boundary

This in-app browser surface currently ignores the requested mobile viewport,
so it cannot provide the requested smartphone 50-FPS proof.  Do not reuse
this sample as mobile evidence.  The existing mobile canvas/touch route in
485 remains static/contract-tested; a browser that actually applies a 390x844
device viewport (or a real phone) is required for dynamic mobile acceptance.
