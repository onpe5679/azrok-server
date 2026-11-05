# 497 Gate 6 in-app BGM performance control (2026-07-28)

## VERIFIED

- The actual in-app viewport is `390x844`; automatic narrow-viewport
  containment now keeps source and overlay canvases at `347x260.25` (4:3)
  after Wine writes fixed 1024x768 inline styles.
- With BGM playing, the first valid visible window measured `125.1661 FPS`,
  but a later valid window measured `39.6510 FPS`.
- A same-tab control with only the web BGM fallback disabled (guest SFX path
  otherwise unchanged) measured `123.8239 FPS` in its first valid window and
  `39.6513 FPS` in a later valid window.
- The matching later decline rejects browser BGM fallback as the sufficient
  cause of the in-app performance regression.  The control is diagnostic
  only; it must not be used as a normal playable route because BGM is a goal
  requirement.

## INFERRED

- The nearly identical decay across BGM-on and BGM-off runs points to the
  in-app host/renderer scheduling path, not MP3 decode or audio output.

## NOT VERIFIED

- The exact host-level throttle or renderer queue condition still needs a
  non-hot-path timing probe.  Three valid sustained in-app 50 FPS windows are
  not yet available.
