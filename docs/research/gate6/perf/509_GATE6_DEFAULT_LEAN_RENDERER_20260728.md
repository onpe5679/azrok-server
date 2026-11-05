# 509 Gate 6 default lean renderer (2026-07-28)

## VERIFIED

- The current accepted guesttex-recycle renderer was run with the existing
  `lean=1` observation mode while preserving its companion flags, original
  BGM (`PetHouse.mp3`, media-element transport), and the visible 3D PetHouse.
  Its direct window was `1,200 Presents / 30.004 s = 40.00 FPS`.
- The immediately preceding non-lean production window on the same in-app
  route was `1,080 / 30.003 s = 36.00 FPS`.  Lean observation removal is a
  real uplift, though still below the 50-FPS requirement.
- `runtimeDiagnosticsEnabled` now defaults to false.  All observation-only
  inventories/profiles require `diagnostics=1` (or their existing explicit
  trace/A-B query).  Renderer state, resource ownership, upload and draw
  caches are unchanged.  Existing `lean=1` URLs remain valid.
- `node --check` and `tools/test_d3d9web_page_contract.py` both pass after the
  default change.  A fresh launch after the change again reported active BGM
  and the expected 94-group / 30,550-block JIT registration.

## Boundary

- 40.00 FPS is not a 50-FPS acceptance result.  Three BGM-enabled 30-second
  PetHouse windows at or above 50 FPS, and physical mobile-device evidence,
  remain required.
