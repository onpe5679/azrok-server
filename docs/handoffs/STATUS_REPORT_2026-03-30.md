# Azrok Plaza Status Report (2026-03-30)

This is a one-off session report for the current pause point.

## Summary

- The client is not yet confirmed playable.
- The project is now in packet-first reconstruction mode, not patch-growth
  mode.
- The current blocker is no longer just late popup close.
  - the next real target is the native first-room path
    `PatHouse -> room.wmb -> 100`
  - and the matching wire data that keeps the client on that path
- Recent runs can progress deep enough to prove that rescue patches are not the
  whole answer; the remaining gap is now packet meaning and scene selection.

## Confirmed Working

- The local server reaches:
  - login
  - character creation
  - first client `0x0007`
  - first client `0x0017`
  - state-1 bootstrap
- `S->C 0x0064` is still alive as the mandatory state-1 pivot.
- Recent late-state telemetry can now reach:
  - `stage=9#10`
  - `popup+0x9C = 1`
  - `self id = 1`
  - `self ent != 0`
  - `ready = 1`
  - `model = 00/00`
- Repeated late client `0x0007` packets are now confirmed meaningful.

## Confirmed Not Working

- No run is yet confirmed as real 3D in-world gameplay.
- The purple selection-like background is still failure state.
- The full-screen move/drag tip image is still failure
  state.
- Top tutorial/help text by itself is not proof of gameplay.
- A raw `PatHouse` path-string change is not sufficient.
- `HIGH_RESOURCE_STATS` alone is not sufficient.

## Most Important Corrections From Today

- Earlier "almost in-game" reads were too optimistic.
- The visible tutorial/help text is part of the loading-screen composition.
- Popup/UI hard-bypass branches made some runs look worse and are now treated
  as opt-in only.
- `AZROK_SCENE_READY_FORCE=0` changed the loading image, but not the real
  outcome.

## Best Resume Baseline

- Leave `AZROK_POPUP_HARD_BYPASSES` off.
- Leave `AZROK_UI_POPUP_BYPASSES` off.
- Keep `AZROK_SCENE_READY_FORCE=1`.
- Do not silently coerce `Lobby` to `Plaza`.
  - legacy fallback now exists only behind
    `AZROK_LEGACY_FORCE_PLAZA_ON_LOBBY=1`
- Treat `AZROK_LATE_ZONE_0007_REPLY=1` as an experiment branch, not a proven
  fix.
- `0x0010` now has two usable baselines:
  - packet-first candidate values from `lgc.tmp` + `init.csv`
  - exact binary defaults via `AZROK_USE_BINARY_0010_DEFAULTS=1`

## Current Strongest Reading

- `0x0010` is a real keyed registry update, not filler.
- The current binary-default `0x0010` values are exact native defaults, but
  the row structure also lines up strongly with the local `lgc.tmp` schema.
- `init.csv` is likely a current-value source, not a clean direct wire-order
  source by itself.
- `FUN_0050a0f0` now makes the first room path much clearer:
  - case `0` -> `room.wmb` -> queue `100`
  - case `8` -> `lobby.wmb`
  - case `0xb` -> `hansol.wmb`
- This makes `Data\\Space\\PatHouse` the strongest current candidate for the
  first real indoor tutorial room, and `Plaza/hansol` a stronger fit for a hub
  path.

## Most Relevant Negative Results

- `AZROK_HIGH_RESOURCE_STATS=1`
  - did not fix the bond-energy popup
  - did not fix the wrong-screen state
- `AZROK_SCENE_READY_FORCE=0`
  - did not produce confirmed gameplay
  - only changed the visible loading image
- `Data\\Space\\PatHouse`
  - path string alone did not fix the transition

## Most Relevant Positive Results

- Less invasive popup policy reduced misleading UI regressions.
- The confirm popup no longer looks like the primary root cause by itself.
- Later repeated client `0x0007` messages do matter.
- Self-id reconciliation back to `1` can now happen after local bootstrap.

## Useful Artifacts

- `<home>\Documents\<project-dir>\Azrok_Plaza\artifacts\ui-probes\cycle_20260330_193016.final.bmp`
- `<home>\Documents\<project-dir>\Azrok_Plaza\artifacts\ui-probes\cycle_20260330_193242.post_confirm.bmp`
- `<home>\Documents\<project-dir>\Azrok_Plaza\artifacts\ui-probes\cycle_20260330_193730.final.bmp`
- `<home>\Documents\<project-dir>\Azrok_Plaza\artifacts\ui-probes\cycle_20260330_194123.final.bmp`
- `<home>\Documents\<project-dir>\Azrok_Plaza\artifacts\ui-probes\cycle_20260330_194345.final.bmp`

## Best Next Resume Questions

1. What exact late scene/tutorial step is still missing after
   `stage=9#10` and `popup+0x9C = 1`?
2. Is the remaining blocker a later scene/tutorial event rather than the early
   room-entry bundle?
3. Which real room asset chain is supposed to replace the baked loading screen
   with the actual 3D room?
