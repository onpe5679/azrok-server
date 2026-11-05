# 186 — Gate 2c UI alpha, cull mapping, and Korean font root

Date: 2026-07-20

## Scope

This is a bounded browser-render correction. It does not expand content QA:
the visible character-selection screen is used only as a quick UI/renderer
probe before the existing PatHouse gate.

## Korean dynamic text — VERIFIED

- The isolated browser filesystem root
  `TinyCore15Wine11.0-wsaeventfix5-korean3.zip` contains the physical
  `C:\\windows\\Fonts\\gulim.ttc` file (13,533,424 bytes). The original root
  is unchanged.
- The root already selects the CP949-compatible Gulim/Batang FontLink path,
  and `run_azrok_seh.bat` sets `LANG`/`LC_ALL` to `ko_KR.EUC-KR`.
- A live browser run from that isolated root visibly rendered dynamic UI text
  such as `캐릭터 선택` and `캐릭터를 생성해주세요` as Korean glyphs instead of
  mojibake.

This proves the missing guest font was one required cause of the dynamic-text
failure. It does not yet prove every CP949 text path in every room.

## UI alpha — VERIFIED cause and implementation

### Cause

`Mouse*.tga` has real alpha (including 5,613 zero-alpha pixels), and the D3D9
bridge preserves alpha for the observed A8R8G8B8/A4R4G4B4 uploads. The host,
however, previously toggled only `D3DRS_ALPHABLENDENABLE` (27). It ignored
`D3DRS_SRCBLEND` (19) and `D3DRS_DESTBLEND` (20), leaving WebGL's default
ONE/ZERO blend factors. A transparent source pixel therefore wrote opaque
black instead of leaving the destination unchanged.

Gate-1 observations include the expected UI factors `SRCALPHA` (5) and
`INVSRCALPHA` (6).

### Change

`tools/boxedwine_local/web_backend/host/d3d9web-runtime.js` now maps D3D9
blend factors 1..11 to their WebGL2 equivalents and applies the current
source/destination pair whenever state 19, 20, or enabled state 27 changes.

### Dynamic result

In a fresh browser session, the selection screen no longer had the formerly
opaque black portrait rectangles. The expected character art and transparent
UI layers were visible. This is direct visual confirmation of the blend-path
fix, not a synthetic shader-only result.

## 3D face orientation — VERIFIED code correction; PatHouse visual confirmation pending

The existing `D3DRS_CULLMODE` (22) conversion reversed D3D's meaning:

| D3D cull mode | Meaning | Correct WebGL face to cull |
|---|---|---|
| `D3DCULL_CW` (2) | discard clockwise triangles | `BACK` |
| `D3DCULL_CCW` (3) | discard counter-clockwise triangles | `FRONT` |

The bridge previously selected `FRONT` for mode 2 and `BACK` for mode 3. It
now uses the table above under its CCW-front convention. This precisely
matches the user-reported front/back inversion. The selection scene is a
2D/limited-model probe, so a fresh PatHouse 3D screenshot is still required
before promoting face-orientation repair to a visual VERIFIED result.

## Input observation — NOT VERIFIED cause, direct measurement

> **SUPERSEDED by 187 for the browser-input diagnosis and rebuilt asset result.**

The current page was launched with `resolution=1024x768`, but the live DOM
canvas measured 640x480 at CSS rectangle `(312.5, 159, 640, 480)`. A test
click at y=655 was outside that canvas. The Emscripten-generated event path
normally rescales through `canvas.width / rect.width`, which is 1 in this
session; the remaining guest-side mapping needs tracing before changing it.
This is tracked separately from the alpha/cull renderer fixes.

## Validation

- `node --check tools/boxedwine_local/web_backend/host/d3d9web-runtime.js` — pass.
- `node tools/web_backend/harness/run-headless.js` — shader compile/link and
  no-GL-error draw pass.
- Fresh local browser run with `build=9` and Korean root — live dynamic Korean
  text and alpha UI visual check passed.
