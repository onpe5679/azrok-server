# 488 Gate 6 current direct-Present bridge preflight (2026-07-28)

## Direct result

- **VERIFIED (failure boundary):** the clean current `ControlA` page was
  rendering native `D3D9WEB_FPS_SAMPLE` lines in its shell output while the
  page HUD remained at zero.  A 30.005-second external window before the
  repair observed `5,520` native Presents at `183.9665 FPS`, with a visible
  `1024x768` canvas.  The renderer was active; only the worker-to-page
  counter bridge was incomplete.
- **VERIFIED (repair):** the current page now incrementally parses only newly
  appended `D3D9WEB_FPS_SAMPLE presents=<n> delta=<n> elapsed_ms=<n>` lines
  and submits their unmodified native counters to the existing monotonic HUD.
  It neither generates nor estimates frames.  Worker-message and broadcast
  bridges remain intact.
- **VERIFIED (fresh served page):** the private `<lan-ip>:8765` origin
  serves the modified file byte-identically.  The classic page script parses,
  and a clean reload reached `hudPresents=8,760`, `FPS 187.8` while the raw
  output continued to emit the same native sample lines.
- **VERIFIED (30-second preflight):** after the bridge repair, an external
  CDP window measured `5,545` direct Presents in `30,007.068 ms`, yielding
  `184.7898 FPS`; the document stayed visible and the canvas display was
  `1024x768` (backing store `640x480`).  The probe reported the available
  direct source as `D3D9WebDebug` on both ends.

## Boundary

This proves that the active desktop control is presently well above 50 FPS
and that its displayed HUD is again driven by a real renderer counter.  It is
**not** the final Gate 6 50-FPS acceptance result: this preflight intentionally
used zero scene-settle and zero warmup seconds and has no required clean
Control A/B/A (or drift A/B/A/B) comparison.  The 300-second post-launch scene
settle, rate-stability gate, sync-drain axis, and full A/B sequence remain
required before publishing a 50-FPS gate pass.
