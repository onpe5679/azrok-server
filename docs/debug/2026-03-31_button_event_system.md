# Acknex Button Event System — Universal Input Injection

Date: 2026-03-31
Scope: Universal solution for programmatic button clicks without physical mouse input

## Core Discovery

The Acknex engine uses a centralized button event queue. All UI buttons across all
screens share the same registration, hit-testing, and event dispatch mechanism.

### Button Registration

`FUN_00518980` → `FUN_0051add0` registers buttons with:
- screen position (x, y)
- layer/z-order
- three bitmaps (down, normal, over)
- **callback ID** (the key identifier)

### Button Event Push (THE UNIVERSAL INJECTION POINT)

```
FUN_0050fe80(buttonID, param2, param3)
```

- Address: `0x0050fe80`
- Calling convention: cdecl (3 params on stack)
- `buttonID`: the callback ID registered during button setup
- `param2`: extra parameter (usually `0xFFFFFFFF` for simple clicks)
- `param3`: extra parameter (usually `0xFFFFFFFF` for simple clicks)

This is the **only function** that pushes events into the button queue.
It is called by the engine's hit-test loop (`FUN_00518d80`) when a physical
click matches a registered button's bounds.

### Button Event Read

```
FUN_0050ffd0(result_buffer)
```

- Address: `0x0050ffd0`
- Reads the next event from the queue
- `result_buffer[0]` = buttonID (`0xFFFFFFFF` if empty)
- `result_buffer[1]` = param2
- `result_buffer[2]` = param3

### Engine Hit-Test Loop

`FUN_00518d80(mouseX, mouseY)` is the engine's per-frame button check:
1. Iterates through registered buttons
2. `FUN_0051b1f0(mouseX, mouseY, &outParam)` performs bounds check
3. If hit, calls `FUN_0050fe80(buttonID, outParam, 0xFFFFFFFF)`

This is why synthetic WM_LBUTTONDOWN doesn't work: the engine's hit-test
reads mouse position from its own internal state (likely DirectInput / Acknex
`mouse_pos`), not from the Win32 message queue `lParam`.

## Why Synthetic Clicks Work For Eggs But Not Buttons

Egg selection likely uses Acknex's `POINTER` / `mouse_left` system which the
Frida hook already patches via DirectInput interception.

Panel buttons use a separate hit-test system (`FUN_00518d80` → `FUN_0051b1f0`)
that may read coordinates differently. The exact input source needs further
investigation, but it's now irrelevant because we can bypass the entire
hit-test by calling `FUN_0050fe80` directly.

## Frida Usage

```javascript
// Universal button click injection
const pushButtonEvent = new NativeFunction(
    ptr(0x0050fe80), 'void', ['uint32', 'uint32', 'uint32']
);

// Click any button by ID
function clickButton(id) {
    pushButtonEvent(id, 0xFFFFFFFF, 0xFFFFFFFF);
}
```

## Known Button IDs

### SelectEgg Screen (CPopupSelectEgg — new character creation)

Handler: `FUN_005e78d0`

| ID | Name | Notes |
|----|------|-------|
| `0x0e` (14) | CreatePet (생성) | Requires egg selected (`FUN_0050af80() != -1`) |
| `0x0f` (15) | Egg slot 0 select | |
| `0x10` (16) | Egg slot 1 select | |
| `0x11` (17) | Egg slot 2 select | |
| `0x12` (18) | Egg slot 3 select | |
| `0x13` (19) | Yes (이름 확인) | Commits name → sends C->S 0x0004 |
| `0x14` (20) | No (이름 취소) | Closes name dialog |
| `0x17` (23) | Back (뒤로) | Returns to SelectPet screen |

### SelectPet Screen (CPopupSelectPet — existing character)

Handler: `FUN_005ea5b0`

| ID | Name | Notes |
|----|------|-------|
| `4` | Unknown button | |
| `5` | EnterPlaza | Enters Plaza (may trigger `level_load`) |
| `6` | Connect | Network connect button |
| `7` | CreatePet (생성) | Goes to SelectEgg if <4 pets, else enters Plaza |
| `8` | DeletePet (삭제) | |
| `9` | Yes (확인) | Sends pet data to server |
| `10` | No (취소) | |
| `0xb` (11) | Exit (종료) | |

### Button Setup Functions

| Screen | Button Setup | Panel Creation |
|--------|-------------|----------------|
| SelectEgg | `FUN_005e95c0` | `FUN_005e8d00` |
| SelectPet | `FUN_005edde0` | (separate) |

### Key Sub-Functions Called by CreatePet (ID 0x0e)

```
FUN_005e7ae0(1)  — show/enable name dialog flag
FUN_005e80b0()   — configure name dialog UI
FUN_0050af50()   — state update (likely sets name input mode)
FUN_00507a30()   — focus the name Edit control
FUN_0050af80()   — returns selected egg index (-1 if none)
FUN_0050acb0()   — commit name (called by Yes button, ID 0x13)
```

## Automation Sequence

To automate character creation without physical mouse:

1. Select egg: synthetic click at calibrated coordinates (already working)
2. Click "Create": `pushButtonEvent(0x0e, 0xFFFFFFFF, 0xFFFFFFFF)`
3. Type name: use existing Edit control text injection
4. Click "Yes": `pushButtonEvent(0x13, 0xFFFFFFFF, 0xFFFFFFFF)`

Step 2 replaces the failing synthetic mouse click with direct event injection.
