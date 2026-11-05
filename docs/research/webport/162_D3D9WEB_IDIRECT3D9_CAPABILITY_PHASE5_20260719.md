# 162 D3D9Web Phase 5 — IDirect3D9 capability bootstrap

Date: 2026-07-19

> **Device state/DrawPrimitiveUP follow-up completed by 163.** This document
> remains authoritative for the IDirect3D9 capability profile.

## Result

**VERIFIED in the local browser:** the real implementation lane under
`tools/d3d9_web_backend` now fills all 17 `IDirect3D9` vtable slots with exact
32-bit WINAPI signatures. A synthetic client exercised the twelve
adapter/capability methods, then `CreateDevice`, the Phase 4 device scene
methods, and WebGL2 Present in one clean run.

All exercised capability HRESULTs were `S_OK`; adapter/mode counts were one;
the profile reported 800x600, eight simultaneous textures, and a non-null
monitor identity. The result, WebGL output, and process exit all passed:

```text
D3D9WEB_PHASE5_CAPS adapters=1 modes=1 id=0x00000000 enum=0x00000000 display=0x00000000 type=0x00000000 format=0x00000000 ms=0x00000000 depth=0x00000000 conversion=0x00000000 caps=0x00000000 size=800x600 textures=8 monitor=00000001 result=PASS
D3D9WEB_PHASE3_GL webgl2=1 triangle=1 canvas=shared size=800x600
D3D9WEB_PHASE5_COM create9=1 createDevice=0x00000000 clear=0x00000000 begin=0x00000000 end=0x00000000 present=0x00000000
D3D9WEB_PHASE5_RESULT=PASS
D3D9WEB_PHASE5_EXITCODE=0
```

## Failure differential

**VERIFIED:** the first run passed every capability method through
`GetDeviceCaps`, then exited `0xC0000096` before the `GetAdapterMonitor` return.
That implementation called `GetDesktopWindow` and `MonitorFromWindow`, which
enters Wine's unavailable X11/window-monitor path in this browser root.

D3D9 exposes `HMONITOR` as an opaque identity to the caller. Returning a stable
non-null virtual monitor handle removed that host-window dependency; the next
run passed the entire chain. This is a browser adapter boundary, not a COM ABI
or renderer failure.

## Implemented IDirect3D9 surface

- `QueryInterface`, `AddRef`, `Release`;
- `RegisterSoftwareDevice`;
- `GetAdapterCount`, `GetAdapterIdentifier`, `GetAdapterModeCount`,
  `EnumAdapterModes`, `GetAdapterDisplayMode`;
- `CheckDeviceType`, `CheckDeviceFormat`, `CheckDeviceMultiSampleType`,
  `CheckDepthStencilMatch`, `CheckDeviceFormatConversion`;
- `GetDeviceCaps`, `GetAdapterMonitor`, `CreateDevice`.

The capability profile is intentionally conservative and computed entirely in
the guest DLL. Repeated `CheckDeviceFormat` calls do not cross into JavaScript,
which satisfies the Gate 1 requirement that its 367,297 calls not become host
round trips.

## Boundaries

- The browser run proves signatures, vtable order, return transport, and the
  synthetic profile used by the test.
- It does **not** prove that every advertised capability value is sufficient
  for Azrok's device-selection branches.
- The device object still implements only the seven Phase 4 slots. Textures,
  buffers, state shadowing, and real draw commands are not connected.
- No Azrok content was launched for this phase.

## Artifacts

- `tools/d3d9_web_backend/d3d9_web.cpp`
- `tools/d3d9_web_backend/bootstrap_client.cpp`
- `tools/d3d9_web_backend/build.bat`
- `tools/d3d9_web_backend/run_browser.bat`
- `tools/boxedwine_local/index_d3d9web_phase5.html`
- `tools/boxedwine_local/apps/D3D9Web_phase5.zip`
  - 68,646 bytes
  - SHA-256 `32022FE4EA9CC3ECB2BA3CA3918137DEDB15EFE44027AA2988867FF1EBBCEE28`
- `artifacts/web_backend/20260719_d3d9_capability_phase5/browser_evidence.txt`
- `artifacts/web_backend/20260719_d3d9_capability_phase5/webgl2_triangle.png`
  - 31,466 bytes
  - SHA-256 `5BF918C12A88E6B36C2685613460FAEBCFD059B8BCF276B562C3FE8714387FAB`

## Next gate

Implement the measured device bootstrap/state path with exact signatures and
guest-side shadow state, then add CPU-backed texture/VB/IB objects and
`DrawPrimitiveUP`. Only after those synthetic contracts pass should the DLL be
placed beside Azrok for one bounded browser rendering scene.
