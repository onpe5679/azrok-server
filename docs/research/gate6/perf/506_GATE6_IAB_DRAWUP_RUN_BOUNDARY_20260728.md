# 506 Gate 6 in-app DrawUP run boundary (2026-07-28)

## VERIFIED

- A diagnostic-only `drawRunProbe=1` scan was added before command dispatch.
  It observes packet order only and is disabled by default; no draw was
  coalesced or reordered.
- The reused in-app browser tab naturally advanced through selection and the
  transition cutscene to the visible 3D PetHouse scene.  BGM remained active
  on the original `PetHouse.mp3` media route.
- The first settled 120-Present PetHouse sample reported `draws=19080`,
  `runs=18480`, `adjacent_pairs=600`, and `max_run=6`: 159 DrawPrimitiveUP
  calls per frame, but only five immediately adjacent pairs per frame.
- The same actual scene HUD was 36.5 FPS.  Selection and cutscene samples
  (2 and 29 DrawUP/frame respectively) were excluded from this result.

## Decision

- A strictly order-preserving host merge can only consume directly adjacent
  DrawUPs without additionally proving every intervening state command.  Its
  observed maximum is 5 of 159 calls/frame (about 3.1%), far below the roughly
  25% uplift required to turn the current sub-40-FPS scene into a 50-FPS scene.
  That narrow merge is therefore rejected rather than added as a risky,
  misleading optimization.
- The next viable performance work must reduce the state/bridge work between
  draws or improve the guest JIT/3D workload, while retaining command ordering.
