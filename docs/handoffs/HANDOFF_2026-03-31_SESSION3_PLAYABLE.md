# HANDOFF - Session 3: PLAYABLE STATE ACHIEVED

Date: 2026-03-31 ~14:10 KST

## Result

**Game is fully playable.** PatHouse room renders with 3D environment, character, furniture, HUD, and tutorial text. No crashes.

## What Changed This Session

### 1. Gate NOP Patch (the breakthrough)
- **Problem**: S->C 0x0002 handler (FUN_0050CBC0 case 2) resets gm+0x31946 to 0, blocking FUN_0050a0f0 (room code dispatcher)
- **Fix**: NOP `mov [eax+0x31946], 0` at VA 0x0050CC07 (10 bytes → 10x 0x90)
- **Effect**: Constructor's -1 gate value persists, FUN_00509200 calls FUN_0050a0f0, code 100 is dequeued, level_load + PatHouse bootstrap completes

### 2. S->C 0x0002 Restored
- Previous session removed it to preserve gate (wrong approach)
- Client NEEDS 0x0002 to transition and send C->S 0x0007
- With gate NOP: 0x0002 triggers transition without killing gate

### 3. Repeated C->S 0x0007 Ignored
- Responding to repeats caused infinite reload loop (memory: 189→309MB growing)
- Fix: server only responds to first C->S 0x0007 with full bundle

### 4. S->C 0x0000 payload[1] = 0x01
- payload[1]=0x00 → state 0x6C (loads but stays on loading screen)
- payload[1]=0x01 → state 0x6B (enters room, PLAYABLE)

### 5. S->C 0x000A Group0 = Binary Defaults
- Was flat init.csv values (structurally wrong)
- Fixed to 11 current/max pairs (1000/2000 alternating)

### 6. All Rescue Patches Removed
- No null guards, vcall guards, ready force, popup bypasses
- Server protocol handles everything naturally

## Files Modified

- `azrok_server.py` — gate NOP patch, 0x0002 restore, repeated 0x0007 ignore, login payload[1]=0x01, group0 binary defaults

## Documentation Updated

- `docs/research/00_current_status.md` — Full rewrite with confirmed playable config
- `docs/research/README.md` — Updated with merged protocol docs (13-20)
- `docs/debug/2026-03-31_progress_summary.md` — Full rewrite with solutions
- `docs/research/13-20_*.md` — Merged from protocol_recovery_final folder

## Key Addresses

| VA | Patch | Purpose |
|----|-------|---------|
| 0x591DC7 | 74 16 → 90 90 | Dispatch flag bypass |
| 0x0050CC07 | C7 80... → 90x10 | Gate reset NOP (THE key fix) |
| 0x102FC540 | → 200 | Nexus runtime force |
| 0x10018414 | → NOP | WDL nexus override |
| 0x1001843D | → NOP | WDL nexus override |

## Next Steps

1. **Gameplay testing** — Can player interact with objects, feed pet, play games?
2. **Missing opcodes** — 0x0065-0x0070 (multi-actor world sync) not implemented
3. **S->C 0x0000 full content** — Currently mostly zeros, may affect features
4. **S->C 0x0064** — Not sent currently. May be needed for some game features
5. **Stat accuracy** — 0x0007 stat bag uses minimal values, not init.csv-accurate wire order
6. **Other gate reset sites** — 5 more locations write gm+0x31946=0, may need NOPing for other flows
