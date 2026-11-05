# Pre-GM Character Creation Debug Notes

Date: 2026-03-31
Scope: local live-debug notes for the character-creation screen only

This file is intentionally **not** part of the packet/server reverse-
engineering canon. It records debugger-side findings about the pre-`0x0004`
local UI flow.

## What is confirmed

### No-real-input slot commit works for all four eggs

Using the Frida input hook without moving the real OS mouse, the current
working commit points are:

- `무리 / Mury`: `(0.18, 0.66)`
- `새지 / Saezy`: `(0.35, 0.63)`
- `아링 / Aring`: `(0.60, 0.63)`
- `테로 / Tero`: `(0.88, 0.60)`

Evidence:

- `artifacts/ui-probes/live_run_20260331_slot_calib/11_mury_try_3.bmp`
- `artifacts/ui-probes/live_run_20260331_slot_calib/12_saezy_try_2.bmp`
- `artifacts/ui-probes/live_run_20260331_slot_calib/07_after_aring_try.bmp`
- `artifacts/ui-probes/live_run_20260331_slot_calib/13_tero_try_5.bmp`

### The create button is still the blocker

Current tested paths:

- Frida synthetic cursor + queued mouse messages
- synchronous `SendMessage` client clicks
- longer hover/hold timings
- left/right create-button sweeps across the lower-left blue button

Current result:

- no tested create point has opened the name popup yet

## Important separation from in-world name dialog hooks

The existing direct name-dialog helpers in `tools/azrok_input_hook.js` are
later-stage `GameManager` helpers, not the pre-gameplay character-creation
popup path.

Relevant addresses:

- `AZROK_GM_PTR_ADDR = 0x006e8430`
- `AZROK_NAME_EDIT_OFFSET = 0x0b93`
- `AZROK_SELECTED_EGG_OFFSET = 0x0d7b`
- `AZROK_NAME_DIALOG_FLAG_PTR = 0x005e7ae0`
- `AZROK_NAME_DIALOG_SHOW_PTR = 0x005e80b0`
- `AZROK_NAME_EDIT_FOCUS_PTR = 0x00507a30`
- `AZROK_NAME_COMMIT_PTR = 0x0050acb0`

Observed on the character-creation screen:

- `gm = null`
- `edit = null`
- `hwnd = null`

Conclusion:

- these helpers are not the real `Create -> name popup` activation path

## Pre-GM UI tracing added to Frida hook

The Frida hook now traces the following when `--observe` is enabled:

- `ShowWindow`
- `EnableWindow`
- `SetFocus`
- `SetWindowPos`

Observed failure pattern for create-button probes:

- `PeekMessage` activity happens
- injected `WM_MOUSEMOVE / WM_LBUTTONDOWN / WM_LBUTTONUP` happens
- but no observed:
  - hidden edit show
  - focus handoff
  - child control reposition

Best current reading:

- tested create points still miss the true handler, or
- the create button uses a different local controller/input gate than slot
  selection

## Hidden edit windows

At idle on the character-creation screen:

- three child `Edit` controls exist under `acknex_mainwin`
- they are invisible but enabled
- they do not visibly transition during failed create-button probes

## Files touched for this debug lane

- `tools/auto_azrok_ui.py`
  - slot defaults updated to the currently working no-real-input commit points
- `tools/azrok_input_hook.js`
  - added extra pre-GM UI observation hooks for `ShowWindow`,
    `EnableWindow`, `SetFocus`, `SetWindowPos`
- `tools/azrok_frida_input.py`
  - continues to be the main no-real-input injector/orchestrator

## Next suggested debugger steps

1. find the real pre-GM create-button handler or UI manager
2. identify what local state transitions must occur before the hidden name
   popup becomes visible
3. keep this work isolated from packet/server reverse-engineering docs
