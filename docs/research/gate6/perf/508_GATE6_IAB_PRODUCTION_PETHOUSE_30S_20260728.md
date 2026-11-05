# 508 Gate 6 in-app production PetHouse 30-second result (2026-07-28)

## VERIFIED

- The retained primary tab was reloaded without the diagnostic
  `drawRunProbe` query.  It was then relaunched through the visible
  audio-activation control and naturally traversed character selection and
  the transition scene into the visible 3D PetHouse.
- The page reported `webBgmFallback=playing`, track `PetHouse.mp3`, transport
  `media-element` during the settled 3D scene.
- The page's direct-Present control completed a fresh window:
  `1080 Presents / 30.003 s = 36.00 FPS`.

## Conclusion

- Removing the diagnostic scan does not restore the 50-FPS floor.  The
  current production in-app PetHouse route remains below target while music
  is active; no 50-FPS or mobile-50-FPS acceptance claim is valid from this
  run.
