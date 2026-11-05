# 493 Gate 6 Chrome mobile viewport 50 FPS proof (2026-07-28)

## Scope

This is an emulated narrow-browser test, not a claim about a particular phone
GPU, thermal state, or mobile OS audio route.  It replaces the rejected
in-app-browser viewport attempt in #492 with a browser surface that actually
applied the requested viewport.

## VERIFIED

- A fresh private HTTPS run used a Chrome viewport of `390x844` CSS pixels.
  The page reported `window.innerWidth=390` and `window.innerHeight=844`.
- The real `run_azrok_seh.bat` D3D9Web path reached FFP initialization and
  emitted direct `D3D9WEB_FPS_SAMPLE` counters.
- Before the layout repair, BoxedWine overwrote both canvas inline styles to
  `1024px x 768px` after the guest window opened.  The browser viewport
  remained `390x844`, but both displayed canvas rectangles became `1024x768`.
  The resulting 30-second direct-Present rate was `118.2469 FPS`, but that
  geometry was not acceptable as mobile presentation proof.
- The launcher now marks only `?mobileCapture=1` runs with
  `body.d3d9web-mobile`.  Its `#dropzone > canvas` rule uses important
  width/height declarations so Wine's fixed inline dimensions cannot expand
  either the source or WebGL overlay beyond the narrow container.
- After a fresh reload and real launch, both `#canvas` and
  `#d3d9web-canvas` displayed `347x260.25` CSS pixels (exact 4:3) in the
  `390x844` viewport, despite their inline styles returning to `1024x768`.
- The final visible direct-Present window measured `3600` Presents over
  `29927.385 ms`: **120.2912 FPS**.  It is above the 50 FPS Gate 6 floor and
  its HUD state was `fast`.
- `tools/test_d3d9web_page_contract.py` passes with the new mobile layout
  assertions; `node --check tools/boxedwine_local/web_backend/host/d3d9web-runtime.js`
  also passes.

## INFERRED

- The same CSS containment should apply to normal narrow Chromium-family
  browser sessions because it keys only off an explicit URL option and
  standard CSS sizing.  This does not establish physical-device performance.

## NOT VERIFIED

- A real Android/iOS device, sustained thermal run, touch gameplay, speaker
  audibility, and a physical-device 50 FPS sample remain required for a full
  smartphone acceptance claim.
