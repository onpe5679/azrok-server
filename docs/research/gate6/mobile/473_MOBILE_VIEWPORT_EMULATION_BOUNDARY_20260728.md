# Mobile viewport emulation boundary (2026-07-28)

## Probe

- **VERIFIED:** the browser viewport capability was requested at `390x844` before a fresh private browser launch. The same launch started original web fallback BGM (`paused=false`, `muted=false`) and later reached a running D3D9 Present state.
- **VERIFIED (negative result):** the page reported `innerWidth=1280`, `innerHeight=720` both before and after guest startup; the rendered canvas later occupied `1024x768` CSS pixels. The in-app browser did not apply the requested mobile dimensions.

## Boundary

- **NOT VERIFIED:** smartphone-emulated frame rate. The observed `FPS` readout was on the unchanged desktop viewport, so it cannot establish the requested mobile 50-fps experience.
- **NOT VERIFIED:** physical Android/iOS browser performance, touch input, audio route, thermal behavior, and private-Tailscale latency. These require either a browser surface that honors a device viewport/DPR or a real private-network device.
