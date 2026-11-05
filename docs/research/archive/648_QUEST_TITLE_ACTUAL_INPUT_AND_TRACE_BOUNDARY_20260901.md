> **SUPERSEDED by 649 for the zero-row/A4 inference.** The trace button armed the source canvas while runtime read the overlay. Correct arming identifies the upper title as A4. Actual input observations remain historical evidence.

# 648 — Quest-title actual input and trace boundary

Date: 2026-09-01 KST

## Evidence

- **VERIFIED:** an actual account-bound browser session reached PatHouse with
  the visible upper quest title corrupted while the lower title/body stayed
  legible.
- **VERIFIED:** the page's existing input-pulse control dispatched guest
  coordinates `(90,350)` then `(54,447)` and reached PatHouse.  The page input
  probe measured the matching canvas coordinates (`90,349.88` and
  `53.75,446.76`) for a 640x480 guest canvas.
- **VERIFIED:** a browser automation click moved the guest cursor but did not
  emit a selection C2S packet; input pulse is the accepted dynamic route for
  further trace runs.
- **VERIFIED / REJECTED:** the former trace's A4R4G4B4 filter yielded zero
  rows after it was armed on the live quest panel.  The title is therefore not
  established as that format.  The query-gated trace now accepts every
  texture format and retains screen/UV geometry for selection.

## Boundary

- **NOT VERIFIED:** the specific upper-row resource and a correcting renderer
  change have not yet been captured or accepted.
- Default gameplay remains unchanged: the trace is inert unless the launch
  URL requests it and the visible trace-start control is pressed.
