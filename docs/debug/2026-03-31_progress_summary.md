# Progress Summary 2026-03-31

## CONFIRMED PLAYABLE

As of 2026-03-31 ~14:10 KST, the game reaches a fully playable PatHouse room:
- 3D room renders (floor, walls, windows, furniture)
- Character (pink Azrok) visible and positioned in room
- Full HUD active (top bar, bottom menu, left status panel)
- Tutorial text displaying
- Heartbeats stable, no crashes

## What Works
- Full protocol flow: 0x0002→0x0003→0x0007→0x0005→0x000A→0x000B
- level_load("room.wmb") IS called (memory 189MB→263MB)
- FUN_0050B400(100) PatHouse bootstrap completes naturally
- FUN_0050A840() loading close completes
- nexus=200 (patched, sufficient)
- Auto-create character at heartbeat #8
- S->C 0x0004 calibration (5 time samples)
- Game UI loads (stats, menus, tutorial text)
- NO S->C 0x0064 needed (natural post-load completes without it)
- NO rescue patches needed (all removed)

## What Was Fixed (This Session)

### Problem 1: Gate killed by S->C 0x0002
- S->C 0x0002 handler (FUN_0050CBC0 case 2) resets gm+0x31946 to 0
- gm+0x31946 gates FUN_0050a0f0 (room code dispatcher) via FUN_00509200
- FIX: NOP the `mov [eax+0x31946], 0` at VA 0x0050CC07 (10 bytes)

### Problem 2: C->S 0x0007 not sent without 0x0002
- Previous session removed S->C 0x0002 to preserve gate
- But client needs 0x0002 to transition and send C->S 0x0007
- FIX: Restore S->C 0x0002 + gate NOP patch = both work together

### Problem 3: Reload loop from repeated 0x0007
- Responding to repeated C->S 0x0007 with full bundle caused infinite reload
- Memory grew continuously (189→292→309MB)
- FIX: Server ignores repeated C->S 0x0007 (respond only to first)

### Problem 4: Login response state
- S->C 0x0000 payload[1]=0x00 → state 0x6C (game loads but stays on loading screen)
- S->C 0x0000 payload[1]=0x01 → state 0x6B (game fully enters room)
- FIX: Set payload[1]=0x01

### Problem 5: 0x000A group0 structure
- Was sending flat init.csv values (0, 25, 33000, 10, 80, ...)
- Should be 11 current/max pairs
- FIX: Use binary defaults (1000/2000 alternating)

## Root Cause (Previous Session - SOLVED)

FUN_0050B400(100) was never called because:
1. S->C 0x0002 reset gm+0x31946 to 0
2. FUN_00509200 checks `if (this+0x31946 != 0)` before calling FUN_0050a0f0
3. FUN_0050a0f0 dequeues code 100 from button queue → FUN_0050B400(100)
4. With gate=0, this entire chain was blocked

Solution: NOP the gate reset instruction so constructor's -1 value persists.

## Binary Patches (Minimal Set)

| VA | Size | Original | Patched | Purpose |
|----|------|----------|---------|---------|
| 0x591DC7 | 2B | 74 16 | 90 90 | Dispatch flag bypass |
| 0x0050CC07 | 10B | C7 80 46 19 03 00 00 00 00 00 | 90x10 | Gate reset NOP |
| 0x102FC540 | 4B | (varies) | C8 00 00 00 | Nexus=200 |
| 0x10018414 | 6B | (mov) | 90x6 | WDL nexus override NOP |
| 0x1001843D | 6B | (mov) | 90x6 | WDL nexus override NOP |

## Protocol Flow (Working)

```
#1  C->S 0x0000 (106B login hello)
#2  S->C 0x0016 + 0x0004 + 0x0000  (heartbeat + calib sample 1 + login 0x183B)
#3  S->C 0x0016 + 0x0004            (heartbeat + calib sample 2)
#4  S->C 0x0016 + 0x0004            (heartbeat + calib sample 3)
#5  S->C 0x0016 + 0x0004            (heartbeat + calib sample 4)
#6  S->C 0x0016 + 0x0004            (heartbeat + calib sample 5)
#7  S->C 0x0016                      (heartbeat only)
#8  S->C 0x0016                      (heartbeat only)
#9  S->C 0x0016 + 0x0002 + 0x0003   (heartbeat + transition + PatHouse path)
#10 C->S 0x0007 → S->C 0x0007+0x0005+0x000A+0x000B  (zone bundle)
#11 C->S 0x0001                      (transition ack, IGNORED)
#12 C->S 0x0008                      (state sync 41B, IGNORED)
#13 C->S 0x0007                      (repeated, IGNORED)
... heartbeats continue, game playable ...
```

## Key Gate Reset Sites in Binary

6 locations that write `mov [eax+0x31946], 0`:
- **0x0050CC07** — FUN_0050CBC0 case 2 (S->C 0x0002 handler) — **NOPed**
- 0x0050AFBF — unknown context
- 0x0050D395 — near FUN_0050D200 (S->C 0x0003 handler?)
- 0x0050D3C2 — near FUN_0050D200
- 0x0050D4F8 — near end of 0x0050D range
- 0x0060691F — different function

Only the 0x0002 handler site needed NOPing for current flow.
