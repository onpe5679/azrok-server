# 496 Gate 6 in-app sustained performance boundary (2026-07-28)

## VERIFIED

- The current retained in-app PatHouse run decayed from a fresh
  `121.6235 FPS` direct-Present 29.600 s window to a later visible
  `38.3610 FPS` direct-Present 28.154 s window.
- The decline reproduced after the normal `lean=1` route stopped retaining
  native trace text: the hidden output textarea remained exactly zero bytes.
  The text-output path was therefore not the sufficient cause of the sustained
  in-app slowdown.
- The lean shell now sends native `D3D9WEB_FPS_SAMPLE` records directly to the
  page's existing counter and retains full native console/textarea output only
  with explicit `?debugConsole=1`.  This removes avoidable host logging work
  while preserving direct-Present evidence in playable sessions.
- `node --check` passes for the modified shell and the launcher contract tests
  pass (four tests).

## NOT VERIFIED

- A continuous three-window in-app 50 FPS acceptance run has not completed.
  The remaining decay must be profiled with a renderer/host timing source that
  does not reintroduce per-frame output overhead.
