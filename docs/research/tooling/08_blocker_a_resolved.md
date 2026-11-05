# Blocker A Resolved — UI Automation Without Physical Mouse

Date: 2026-03-31

## Solution

Universal button event injection via `FUN_0050ffd0` hook:
- Intercept the button event reader at `0x0050ffd0`
- Overwrite the return buffer with the desired button ID
- Filter by `returnAddress` to target specific handlers

### Key Addresses

| Address | Function | Role |
|---------|----------|------|
| `0x0050ffd0` | Button event reader | Returns `[buttonID, param2, param3]` from queue |
| `0x0050fe80` | Button event push | Pushes events into queue (thiscall, needs ECX) |
| `0x005e78d0` | SelectEgg handler | Handles egg selection + character creation |
| `0x005ea5b0` | SelectPet handler | Handles existing pet management |
| `0x00518d80` | Engine hit-test | Engine's per-frame button click detection |

### SelectEgg Handler Return Address

When `FUN_005e78d0` calls `thunk_FUN_0050ffd0`, the return address is `0x5e7901`.
Use this as `targetCaller` to inject events only for the SelectEgg handler.

### Button IDs

SelectEgg screen: 0x0e (Create), 0x0f-0x12 (egg slots), 0x13 (Yes), 0x14 (No), 0x17 (Back)
SelectPet screen: 4-11 (various buttons)

### Working Character Creation Flow

```bash
# 1. Move window to (0,0)
python tools/auto_azrok_ui.py --title AZROK move-window 0 0

# 2. Select egg (synthetic click)
python tools/azrok_frida_input.py --title AZROK click --x-ratio 0.60 --y-ratio 0.63 --hover-ms 150 --hold-ms 150 --settle-ms 1000 --move-top-left

# 3. Push Create button
python tools/azrok_frida_input.py --title AZROK push-button 0x0e --repeat 120 --target-caller 0x5e7901 --settle-ms 2000

# 4. Type name (WM_CHAR to main window + Edit children)
# Done programmatically via PostMessageW

# 5. Push Confirm button
python tools/azrok_frida_input.py --title AZROK push-button 0x13 --repeat 120 --target-caller 0x5e7901 --settle-ms 2000
```

### Result

C->S 0x0004 packet successfully sent with character type and name.
Full protocol flow proceeds: 0x0002 → 0x0003 → 0x0007 → 0x0005/0x0010/0x0011 → 0x0017 → 0x0064 etc.

### Why Synthetic Clicks Don't Work For Buttons

The Acknex engine's button hit-test (`FUN_00518d80`) reads mouse position from
internal state (DirectInput / engine mouse_pos), not from Win32 message queue
lParam. SendMessage WM_LBUTTONDOWN sets the message queue position but not the
engine's internal position.

Egg selection works because it uses a different input path (Acknex POINTER/mouse_left
system) that the Frida hook already patches.

### Files Modified

- `tools/azrok_input_hook.js` — Added `pushbutton` RPC + `FUN_0050ffd0` interceptor
- `tools/azrok_frida_input.py` — Added `push-button` CLI command with --repeat and --target-caller
