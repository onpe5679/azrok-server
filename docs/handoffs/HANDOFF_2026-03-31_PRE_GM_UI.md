# Handoff 2026-03-31

Target: `<home>\Documents\<project-dir>\Azrok_Plaza\Azrok.exe`
Goal: make the client reach real playable room entry against the local server

Note:

- this is a temporary handoff file
- debugger-side character-creation UI notes now live separately in:
  - `<home>\Documents\<project-dir>\Azrok_Plaza\docs\debug\2026-03-31_pre_gm_character_creation_debug.md`
- packet/server reverse-engineering canon remains under:
  - `<home>\Documents\<project-dir>\Azrok_Plaza\docs\research\`

## What changed this session

- no-real-input character selection now works for all four eggs
- `tools/auto_azrok_ui.py` slot defaults were updated to the currently working
  commit points
- `tools/azrok_input_hook.js` gained extra pre-GM UI observation hooks for:
  - `ShowWindow`
  - `EnableWindow`
  - `SetFocus`
  - `SetWindowPos`

## Confirmed working slot commit points

- `무리 / Mury`: `(0.18, 0.66)`
- `새지 / Saezy`: `(0.35, 0.63)`
- `아링 / Aring`: `(0.60, 0.63)`
- `테로 / Tero`: `(0.88, 0.60)`

Evidence screenshots:

- `<home>\Documents\<project-dir>\Azrok_Plaza\artifacts\ui-probes\live_run_20260331_slot_calib\11_mury_try_3.bmp`
- `<home>\Documents\<project-dir>\Azrok_Plaza\artifacts\ui-probes\live_run_20260331_slot_calib\12_saezy_try_2.bmp`
- `<home>\Documents\<project-dir>\Azrok_Plaza\artifacts\ui-probes\live_run_20260331_slot_calib\07_after_aring_try.bmp`
- `<home>\Documents\<project-dir>\Azrok_Plaza\artifacts\ui-probes\live_run_20260331_slot_calib\13_tero_try_5.bmp`

## Current blocker

The blocker is no longer slot selection.

The blocker is:

1. click lower-left `생성 / Create`
2. open name popup
3. submit name
4. let the client emit `C->S 0x0004`

Current result:

- synthetic clicks can select eggs
- synthetic clicks still do **not** open the name popup
- synchronous client-message clicks still do **not** open the name popup

## Important architectural finding

The existing direct name-dialog helpers in `tools/azrok_input_hook.js` are not
the character-creation popup path.

Current hooked addresses:

- `AZROK_GM_PTR_ADDR = 0x006e8430`
- `AZROK_NAME_EDIT_OFFSET = 0x0b93`
- `AZROK_SELECTED_EGG_OFFSET = 0x0d7b`
- `AZROK_NAME_DIALOG_FLAG_PTR = 0x005e7ae0`
- `AZROK_NAME_DIALOG_SHOW_PTR = 0x005e80b0`
- `AZROK_NAME_EDIT_FOCUS_PTR = 0x00507a30`
- `AZROK_NAME_COMMIT_PTR = 0x0050acb0`

On the character-creation screen they still report:

- `gm = null`
- `edit = null`
- `hwnd = null`

Conclusion:

- these helpers belong to the later in-world `GameManager` path
- the pre-gameplay `Create -> name popup` path is a separate pre-GM UI path

## Pre-GM UI observation result

Observed during synthetic create clicks:

- `PeekMessage` activity rises as expected
- injected `WM_MOUSEMOVE / WM_LBUTTONDOWN / WM_LBUTTONUP` is delivered
- but no observed:
  - `ShowWindow`
  - `EnableWindow`
  - `SetFocus`
  - `SetWindowPos`
  for hidden UI children

Meaning:

- tested create points are still missing the real handler, or
- the create button uses a different input/controller path than egg selection

## Hidden child-edit state

At idle on the character-creation screen:

- three child `Edit` windows exist under `acknex_mainwin`
- they are invisible but enabled
- they do not visibly transition during failed create clicks

## Current server/runtime context

- packet-side work is still relevant after `0x0004`
- but immediate live-debug blocker is local UI before `0x0004`
- do not confuse missing `0x0004` with network failure until the local create
  popup path has been reached

## Good commands to resume from

Move window and capture:

```powershell
python tools/auto_azrok_ui.py --title AZROK move-window 0 0
python tools/auto_azrok_ui.py --title AZROK capture artifacts\ui-probes\resume.bmp --client
```

Test one slot with no-real-input Frida click:

```powershell
python tools/azrok_frida_input.py --title AZROK click --x-ratio 0.60 --y-ratio 0.63 --hover-ms 110 --hold-ms 110 --settle-ms 450 --move-top-left
```

Observe one create click:

```powershell
python tools/azrok_frida_input.py --title AZROK click --x-ratio 0.070 --y-ratio 0.965 --hover-ms 180 --hold-ms 180 --settle-ms 650 --move-top-left --observe
```

## Next best steps

1. find the real pre-GM create-button handler or UI manager
2. identify the hidden name-popup activation path before `GameManager` exists
3. only after that, resume end-to-end `0x0004 -> 0x0007 -> 0x0017 -> state-1`
   validation

## Relevant permanent docs

- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\research\00_current_status.md`
- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\research\01_protocol_and_state1_flow.md`
- `<home>\Documents\<project-dir>\Azrok_Plaza\docs\research\04_runtime_patches_and_telemetry.md`
