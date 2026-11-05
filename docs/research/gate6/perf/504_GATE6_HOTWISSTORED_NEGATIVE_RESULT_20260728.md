# 504 Gate 6 hotwisstored package negative result (2026-07-28)

## VERIFIED

- The previously undocumented private package
  `Azrok_D3D9Web_pathouse_guesttexrecycle4_hotwisstored1` booted through the
  original selection and rendered the visible PatHouse room with the original
  PetHouse BGM fallback unpaused, unmuted, ready state 4 and advancing.
- Its visible narrow in-app PatHouse HUD measured `FPS 35.8`. This is below
  the active guesttex-recycle path's roughly 40-FPS boundary and below the
  required 50-FPS floor.

## Conclusion

The package is a rendering-compatible but slower candidate. It is not adopted
and the active page returns to `Azrok_D3D9Web_pathouse_guesttexrecycle4`.
