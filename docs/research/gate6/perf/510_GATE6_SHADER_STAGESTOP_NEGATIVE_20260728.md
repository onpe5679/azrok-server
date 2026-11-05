# 510 Gate 6 fragment stage-stop negative result (2026-07-28)

## VERIFIED

- A fragment-shader variant stopped the fixed-function stage chain after the
  first `D3DTOP_DISABLE`, then compiled, linked, and completed a WebGL2 dummy
  draw in the project harness without GL errors.
- In the in-app browser it launched with active `PetHouse.mp3`, reached the
  visible 3D PetHouse, and completed `1,080 Presents / 30.006 s = 35.99 FPS`.
- The matched default-lean baseline was 40.00 FPS, so this shader branch is a
  10% regression despite preserving visible boot and music.

## Decision

- The fragment change was reverted immediately, and the retained user tab was
  reloaded onto the verified default-lean shader path with active BGM and the
  expected 94-group / 30,550-block JIT registration.
- Do not use dynamic stage-stop branching as a 50-FPS candidate.  Any future
  shader reduction requires a compiled specialization and a visible 30-second
  A/B result, not inferred inactive-stage arithmetic.
