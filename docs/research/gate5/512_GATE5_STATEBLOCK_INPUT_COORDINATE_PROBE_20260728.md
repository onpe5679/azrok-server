# 512 Gate 5 StateBlock input-coordinate probe (2026-07-28)

## VERIFIED (static)

- The URL-gated `d3d9WebInputPulse()` helper previously mapped a fixed
  `1024x768` guest coordinate space onto the CSS canvas.
- The current StateBlock page had exposed a `640x480` backing canvas, while
  the normal Emscripten path maps pointer input using the actual canvas backing
  width and height.  The diagnostic helper could therefore aim at a different
  canvas position from real browser input.
- The helper now obtains `canvas.width` and `canvas.height` before converting
  guest coordinates to CSS coordinates.  It is still URL-gated and is not a
  production input path.
- A second URL-gated `inputProbe=1` observer records trusted pointer/mouse
  event coordinates and their computed canvas coordinates in
  `#runtime-status[data-input-probe]`.  Its eight-event trail in
  `data-input-probe-trail` preserves the original trusted pointer event as
  well as any compatibility MouseEvent that follows it.  It neither dispatches
  nor suppresses events.
- `python tools\\test_d3d9web_page_contract.py` completed successfully after
  the change (4 tests, 2026-07-28).

## NOT VERIFIED

- No fresh StateBlock Plaza action has yet been performed with `inputProbe=1`.
  The probe must show the trusted physical browser event and the packet capture
  must show (or rule out) the natural `C2S 0x0019` path before attributing the
  missing Plaza packet to coordinate conversion.
