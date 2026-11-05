# Quest panel & money (소지금): where they actually come from (2026-07-17)

Parallel static trace (Ghidra, `Azrok_original.exe`) of the empty quest window and 소지금 0,
cross-checked against server code and a live capture. Done while Codex worked the
E1201/evolution track. No binary patch.

## Headline correction

The prior "next candidate" note said quest/money come from **0x000A/0x000B**. That is WRONG:

- **Quest panel comes from the big S→C `0x0007` setup blob**, not 0x000A/0x000B.
- `0x000A` = character-status **stat registry** (7 keyed groups). `0x000B` = level→XP curve.
- **Money is in NEITHER**, and could not be located statically at all (see §2).

## 1. Quest panel = S→C 0x0007 blob, offset 0x134 — VERIFIED (triple-confirmed)

Client handler `HandleS2C_0007_LoadSetupBlob` @ `0059e330`, disasm `0059e717–0059e810`:
- 10 quest rows read from the blob:
  - `id       = blob[0x134 + i*2]` (u16), kept only if `id < 6` OR `id == 0xFF` (empty)
  - `progress = blob[0x148 + i*2]` (u16)
  - `value    = blob[0x15c + i*4]` (u32)
- stored to `mainobj+0x70c`, stride 0xC. `0xFF` = empty slot; the 3 on-screen slots = 3
  non-0xFF rows. Renderer `FUN_00546740` uses local catalog `DAT_006dae98` (stride 0x5C) for the
  text; the server sends only ids/progress, not text.

**Confirmed three independent ways:**
1. Ghidra decompile (above).
2. Our own server already knows this offset: `azrok_server.py:_build_zone_0007_draft` docstring
   literally lists `+0x134: 10 * u16` (near line 3793).
3. Live capture `captures/packets_20260717_140843.txt` S→C 0x0007 (472B payload): bytes at
   payload `0x134..0x14B` are `FF 00` ×10 → every quest-row id = `0x00FF` = empty slot.

**Root cause of empty quest window: the server sends all 10 quest rows as 0xFF.** To populate
quests, write category ids `0..5` into `blob[0x134 + i*2]`, with progress at `+0x148`, value/time
at `+0x15c`. No client patch. (Layout VERIFIED; "server sends 0xFF" VERIFIED from capture.)

Not confirmed: whether the quest catalog `DAT_006dae98` is loaded from init.csv or hardcoded.

## 2. Money (소지금) — NOT found statically; needs the debugger

Ruled out (all VERIFIED):
- Pet-stat schema (71 entries from lgc.tmp → `DAT_006ea57c`, loader `StatSchema_LoadFallbackAndMapNames`
  @ `005a37a0`) has NO money stat — the 61 fallback names are food/activity/재미/에너지/위생/허기/레벨/IQ.
- Special stat ids 0x43–0x46 = 펫진화 / 펫 / 턴횟수 / 명령횟수. Not money.
- `0x000B` = `XPCurve_StoreValues` @ `005a50f0` (31×u16 level→XP). Not money.
- The string "소지금" (CP949 `BC D2 C1 F6 B1 DD`) is NOT in the .exe → HUD label lives in a UI/WIS
  resource, not .rdata. ("골드" hits = the pet name "골드론/Goldron", not currency.)
- Near-miss: the large-number HUD formatter `FUN_005a8c90` (splits by /1e6,/1e4,/1e2) looked like
  money but its paired getter `FUN_004da6c9` = `PackedDate_BuildYMDH` — it is a **packed-date**
  decomposer writing `mainobj+0x5d7`. So `0x0007 blob[+3]` = packed Y/M/D/H date, NOT money.

Unconfirmed candidates (NOT asserted, per AGENTS.md — no concluding from indirect evidence):
- `0x000A` StatRegistry keyed slots (`HandleS2C_000A_StatRegistry` @ `0059eca0`) — money could be one
  keyed uint16, but nothing ties a key to money and u16 money would be odd.
- `0x0007 blob[+7]` → `FUN_0059e300` stores a plain u32 at `mainobj+0x1ec` — unidentified.

**Money needs a dynamic trace:** in x32dbg, hardware-write BP on the HUD money integer (or trace the
"소지금" label draw and read the adjacent number's source), then walk back to the inbound
opcode/offset. Static alone cannot resolve it without violating the "no indirect evidence" rule.
Deferred until the x32dbg session is free (Codex currently uses it).

## 3. Opcode reference (VERIFIED bodies)
- `0x0007` @ `0059e330` — master setup blob (>0x1d8B): 70 pet-stats (u16 @ blob+0xb, clamped),
  10 quest rows (§1), packed date (blob+3), byte-banks (0x1ac/0x1b6/0x1c0/0x1ca), 8 mode-pairs
  ({byte@0x184,u32@0x18c} → mainobj+0x6c8).
- `0x000A` @ `0059eca0` — 7-group keyed status registry (~0x96B). Character-status window.
- `0x000B` @ `0059eee0` — 31×u16 level→XP table.

## Overlap note
Codex's "Content contract audit" subagent is cross-checking 0x0007/0x000A/0x000B serialization vs
captures on the growth/item-data angle. This note is the quest-render/money angle — complementary,
same opcodes. Reconcile if both produce field maps for 0x0007.

Related: [[project-multiplayer-milestone]], note 11 (stat tables), note 49 (0x0007 content schema).
