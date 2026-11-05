# Gate 2c D3D9Web 1024x768 presentation-size repair

Date: 2026-07-20

## Finding

**VERIFIED (live browser DOM):** The D3D9 WebGL output was already backed by
`1024x768`, but its CSS box was inherited from BoxedWine's separate SDL input
canvas and measured only `640x480`. The original source canvas also measured
`640x480`, so the visible game image was needlessly reduced to 62.5% in both
dimensions.

The target is **1024x768** (not 1024x786).

## Repair

`web_backend/host/d3d9web-runtime.js` now retains the distinct backing stores
and, after D3D `INIT`/viewport sizing, gives the SDL source canvas, D3D overlay,
and their parent the D3D output CSS dimensions. It does not change the SDL
backing store: browser pointer coordinates still first resolve to the native
`640x480` source pixels and then follow Wine's existing expansion into the
`1024x768` guest desktop.

The page imports this change with cache token `display1024_1`.

## Dynamic verification

Fresh `pathouseav=1` run, after D3D dispatch began:

| Element | Backing store | CSS rectangle |
| --- | ---: | ---: |
| `#canvas` (SDL input) | 640x480 | 1024x768 |
| `#d3d9web-canvas` (WebGL D3D output) | 1024x768 | 1024x768 |

The live dispatch counter was nonzero (`117760` commands, `1634` Presents), so
the measurement is from the active renderer rather than startup UI.

## Scope

This corrects only the visible presentation-size regression. It neither hides
the selection-layer text nor changes the renderer's performance; those require
their own natural character-selection and steady-PatHouse measurements.
