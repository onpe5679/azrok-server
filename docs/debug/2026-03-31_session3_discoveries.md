# Session 3 Discoveries — 2026-03-31

## Result: PLAYABLE (PatHouse room, NPC dialog, full HUD)

---

## 1. Gate Mechanism — THE Breakthrough

**Problem**: `FUN_00509200` (per-frame update) checks `if (gm+0x31946 != 0)` before calling `FUN_0050a0f0` (room code dispatcher). S->C 0x0002 handler (`DispatchState0Common_S2C` case 2) resets this to 0. Without the gate, code 100 (PatHouse bootstrap) is never dequeued → `level_load` never runs.

**Fix**: NOP `mov [eax+0x31946], 0` at VA 0x0050CC07 (10 bytes). Constructor's -1 value persists.

**Binary pattern search found 6 sites** that reset gm+0x31946:
- 0x0050AFBF, **0x0050CC07** (NOPed), 0x0050D395, 0x0050D3C2, 0x0050D4F8, 0x0060691F

Also: `HandleS2C_0001_ResetLatchOrRaiseError` (0x0050D360) kills the gate when payload byte = 1 or 2.

## 2. S->C 0x0002 Must Be Sent

Previous session removed 0x0002 to preserve gate. Wrong approach — client needs 0x0002 to transition and send C->S 0x0007. With gate NOP: both work together.

## 3. Repeated C->S 0x0007 = Reload Loop

Server responding to repeated C->S 0x0007 with full bundle causes infinite reload (memory: 189→309MB growing). Fix: ignore all but the first.

## 4. Login Response payload[1] = 0x01

`HandleS2C_0000_SelectLobbyEntryScene` (0x0050D0E0) decompilation confirms:
- `payload[1] == 0` → scene 0x6C
- `payload[1] != 0` → scene 0x6B (confirmed working, enters room)

## 5. 0x000A Group0 = current/max Pairs

Not flat init.csv values. 11 pairs × 2 = 22 u16. Binary defaults (1000/2000 alternating) confirmed working.

## 6. tuple_kind Must Be 0xFF

0x0007 +0x184 `tuple_kind[8]`: 0x00 is a live mode value processed by `FUN_005aa6f0`. Setting all 8 to 0xFF (NOP sentinel) **improved game state** — NPC dialog activated, memory 263→418MB.

## 7. header_02 (+0x02) Is NOT Species

Ghidra shows +0x02 feeds `ProtocolState_SetField130Value`, not species B. Changed from `char_type` to 0.

## 8. Calibration Does NOT Set Gate

`HandleS2C_0004_CalibrationSample` (0x0059DE50) sets `gm+0x9A5..0x9DB` region (RTT samples). Does NOT touch gm+0x31946. After 5 samples, sets `payload[0]=0xFF`. The dispatcher's case 4 then sets `gm+0x31C71=1` (different from gate).

## 9. S->C 0x0064 Struct Was Wrong in Docs

Old (wrong): actor_id at +0x01(u32), x at +0x06, y at +0x0A.
Correct (Ghidra-verified):

| Offset | Field | Type |
|--------|-------|------|
| +0x00 | entry_kind | u8 |
| +0x01 | selector_0 | u8 |
| +0x02 | selector_1 | u8 |
| +0x03 | self_id | u32 |
| +0x07 | pos_x_raw | u32 |
| +0x0B | pos_y_raw | u32 |
| +0x0F | tail_dword | u32 |
| +0x13 | room_domain | u8 |
| +0x18 | field_0x18 | 3B |

Currently NOT sent — natural bootstrap handles room entry.

## 10. Ghidra Analyzed Names

`Azrok_analyzed.exe` has 72 functions renamed + 18 struct types defined. Key mappings:

| Address | Name |
|---------|------|
| 0x00594310 | `DispatchInbound_ByClientMode` |
| 0x0050CBC0 | `DispatchState0Common_S2C` |
| 0x0059E070 | `HandleS2C_0000_LoadLobbySparseCache` |
| 0x0050D0E0 | `HandleS2C_0000_SelectLobbyEntryScene` |
| 0x0059DE50 | `HandleS2C_0004_CalibrationSample` |
| 0x0059E330 | `HandleS2C_0007_LoadSetupBlob` |
| 0x0050D290 | `HandleS2C_0007_EmitPostSetupStateRequest` |
| 0x00615650 | `HandleS2C_0064_ApplyAuthoritativeSelf` |
| 0x006169D0 | `HandleS2C_006E_CommitReadyMode` |
| 0x005A4880 | `Stats_StoreClampedValue` |
| 0x005A37A0 | `StatSchema_LoadFallbackAndMapNames` |
| 0x0059A6E0 | `DomainCode_EmitLocalEffect` |
| 0x006130B0 | `SendC2S_0064_LocalBootstrapStatus` |

Full list: `docs/research/21_ghidra_analyzed_reference.md`

## 11. Plaza (Outdoor) Transition

- C->S 0x0019: door click / outdoor request (payload=0x00)
- S->C 0x000D with payload[0]=0 triggers `FUN_00568770` (Plaza transition) BUT crashes from PatHouse because `FUN_00568770` uses state-1 vtable calls that aren't initialized in state 2 (PatHouse mode)
- Correct approach: set `gm+0x31c72=1` via process memory, then send 0x0002 + 0x0003 (Plaza path)
- `gm+0x31c72` is the "hansol flag" checked by `HandleS2C_0007_EmitPostSetupStateRequest`
- If flag=1: room code 0x6e (`hansol.wmb` = Plaza outdoor), if flag=0: always code 100 (PatHouse)
- `CGameManager` vtable = 0x0069D0A4, used to find GM in memory via stack scan
- `find_real_gm()` scans process memory for vtable pointer, validates with `gm+0x31792` (scene mode) and `gm+0x31946` (gate)
- `FUN_00528490` = setter for `gm+0x31c72`, `FUN_005284c0` = setter for `gm+0x31c73` (OXQuiz)
- `FUN_0050b090` = "normal" path, just calls `FUN_0050a7f0(100)` - ALWAYS PatHouse
- Result: `hansol.wmb` loads (loading screen changes to outdoor scene), but infinite loading — needs S->C 0x0064 or scene stage handling
- 5 callers of `FUN_00568770` in 0x005Dxxxx range are OutMap UI handlers (not server-triggered)
- `gm+0x31c71` (hansol permission) ALSO needs to be set to 1 — `GameManager_DispatchRoomCode` code 11 is conditional on this flag
- Server port changed from 9000 to 9200 (Windows Hyper-V reserved port range 8951-9050)
- C->S 0x0064 echo as S->C 0x0064 crashes! C->S 0x0064 is bootstrap STATUS REPORT, S->C 0x0064 is actor PLACEMENT — different semantics. Protocol doc says "echo 금지"
- After fixing: C->S 0x0064 arrives (Stage 0 works!), server responds with 0x006E only, game at 486MB, no crash
- But still infinite loading — Stage 1 vtable+8 check blocks progress. Needs Ghidra analysis of what Stage 1 waits for
- `CGameManager` is stack-allocated in main loop (`FUN_004ecab0`), NOT global. Found at 0x00163280 via vtable scan (vtable=0x0069D0A4)

## 12. Evolution System

- 4 species: Ark(0), Abo(1), Paz(2), Tero(3)
- 4 stages implemented (0-3), stage 4 has no model assets (`_5.mdl` doesn't exist)
- Models: `_2.mdl` (stage 0-1), `_3.mdl` (stage 2), `_4.mdl` (stage 3)
- Evolution controlled by 0x0007 `header_01` (species) and `header_02` (evolution stage)
- Env vars: `AZROK_SPECIES`, `AZROK_EVOLUTION` (max 3)

---

## Working Protocol Flow

```
C->S 0x0000 (106B)
S->C 0x0016 + 0x0004 × 5 heartbeats (calibration)
S->C 0x0000 (0x183B, payload[1]=0x01)
S->C 0x0002 (empty) + 0x0003 (PatHouse)     @ heartbeat #9
C->S 0x0007 (196B)
S->C 0x0007 (472B) + 0x0005 + 0x000A + 0x000B
C->S 0x0001 (ignored) + 0x0008 (ignored)
C->S 0x0007 repeated (IGNORED)
... heartbeats, game playable ...
```

## Active Binary Patches (3 total)

| VA | Bytes | Purpose | Removable? |
|----|-------|---------|------------|
| 0x591DC7 | 74 16 → 90 90 | Dispatch flag bypass | No |
| 0x0050CC07 | C7 80... → 90×10 | Gate reset NOP | Investigate |
| 0x102FC540 | → 200 | Nexus force | No |

## Remaining Gaps

- S->C 0x0006 (ResetLocalClockAndSeed) — not implemented, may help time sync
- S->C 0x0064 — struct fixed but still disabled. Needed for multi-actor later
- Stat wire order — minimal values work, init.csv-accurate mapping TBD
- 10 missing S2C opcodes (0x000C, 0x0067, 0x006A-0x006D, 0x006F-0x0071, 0x03E8)

## Documentation Changes

- 22 → 13 research files (4 deleted, 1 merged, 5 archived)
- protocol_recovery_final folder deleted (verified preserved)
- All docs updated: FUN_ → Ghidra analyzed names (72 mappings)
- Doc conflicts resolved: 0x0064 offsets, 0x000A/0x000B opcodes, role separation

---

## 13. WDL Variable Injection — The Final Breakthrough

**Date: 2026-04-01**

### Root Cause: IAT Hook Was the Source of All Other Patches

The IAT hook on `connect()` caused `CClientPeer::OnConnect` to never be called,
because the hook made `connect()` return success synchronously, bypassing the
async `WSAEventSelect` / `WSAWaitForMultipleEvents` path that ultimately invokes
`OnConnect`. This was the root of a full domino chain:

```
IAT hook (connect() sync bypass)
  → OnConnect (FUN_00591CD0) never called
  → dispatch flag (this+0x4076) stays 0
  → NOP patch on dispatch check needed (VA 0x591DC7)
  → 0x0002 needed to trigger C->S 0x0007
  → 0x0002 handler resets gate (gm+0x31946 → 0)
  → gate NOP needed (VA 0x0050CC07)
```

Eliminating the IAT hook via WDL injection collapses all four patches to one (Nexus=200).

### autoLauncher.dll Analysis

- **Type**: COM ActiveX component
- **CLSID**: `{63875209-13A5-4586-8756-74FB690099CA}`
- **Two commands exposed to JavaScript**:
  - `"run"` → reads exe/workdir from registry, calls `ShellExecuteA` with args passed directly from JavaScript (IP:PORT user auth)
  - `"send"` → creates 512B shared memory named `"mooondal"`, copies 256B, then `FindWindowA` + `SendMessageA(0xBBB, 0x13F)`
- **Registry key for "run"**: `HKLM\SOFTWARE\<key>\autoLauncher` (REG_BINARY: `workdir\0exepath\0`)
- Args are passed directly from the JavaScript layer to `ShellExecuteA` — this is how `Azrok.exe` receives `"IP:PORT user auth"` on its command line

### open.exe Is NOT a Launcher for Azrok.exe

`open.exe` (741 KB) is a **separate mooondal-engine game client** — it runs its
own game loop and renders its own UI. It is not a thin launcher wrapper.
The actual launch of `Azrok.exe` happens via `autoLauncher.dll`'s `"run"` command
triggered from the JavaScript inside `open.exe`'s embedded IE WebBrowser control.

### starmaru.exe Is the Patcher

`starmaru.exe` (524 KB) handles patching: calls `regsvr32` to register
`autoLauncher.dll`, reads `version.dat`, and downloads patch files. It runs
first in the chain before `open.exe`.

### WDL String Variable Pointer Chain

```
0x006e8430          ; global pointer to Acknex engine object
  → engine object
    → +0x9a0        ; WDL STRING variable for IP:PORT
      → STRING struct
        → +0x0c     ; CString data pointer → char buffer
```

The STRING struct is `CFixedStringT<char,64>` — 64-byte inline buffer.
For empty (uninitialized) strings, `alloc_len = 0`, so a direct write to the
inline buffer at `+0x0c` is needed as a fallback rather than following the
pointer.

### Additional Findings (2026-04-01)

- **CString empty sentinel**: fallback writing to 0x102FCF84 corrupts ALL empty strings in the engine. Fixed by allocating new memory (VirtualAllocEx) with proper CStringData header.
- **Nexus default patch**: 0x10017EF6 contains MOV immediate 0x28 (40), must be patched to 0xC8 (200) BEFORE engine_open. Without this, level_load("pet.wmb") during startup fails.
- **ACKNEX.DLL load timing**: DLL loads at ~0.05s, engine_open completes at ~1.0s. Nexus patches must be applied between DLL load and engine_open.
- **S->C 0x0006 test results**: triggers C->S 0x0007 (confirmed), but crashes (0xC0000005) when sent before subsystems initialized or in same packet as 0x0007. Suitable only for post-room-load transitions.
- **S->C 0x0004 payload[0]=0x01**: works (binary-correct per archive docs), 0x00 also works. Both confirmed playable.
- **Evolution 3 limitation**: proactive 0x0007 flow works for evolution 0 but evolution 3 disconnects. Needs further investigation — may require 0x0002-triggered flow for higher evolutions.
- **C->S 0x006C observed during gameplay**: 4 bytes (all zeros), triggered by in-game action.

### S->C 0x0007 Can Be Sent Proactively

With WDL injection and the dispatch flag set correctly by `OnConnect`, the server
can send `S->C 0x0003 + S->C 0x0007` proactively without waiting for `C->S 0x0007`
and without sending `S->C 0x0002` first. The client processes the bundle correctly.

### HandleS2C_0002 → C->S 0x0007 Connection

`HandleS2C_0002_TransitionPrimary` sends `C->S 0x0007` via `FUN_005a4770(0,1,7)`
(vtable+0x10). This path is only needed if 0x0002 is sent. With proactive 0x0007
delivery it is never triggered.

### FUN_0050a880 — The Missing ButtonQueue Link

`FUN_0050a880` bridges `gm+0x31aad` → ButtonQueue. This was the previously
missing link explaining how the PatHouse bootstrap (room code 100) reaches the
dispatcher. Confirmed via Ghidra cross-reference analysis.

### Final Result

| Approach | Binary Patches Required |
|----------|------------------------|
| IAT hook (azrok_server.py) | 4 (IAT + dispatch NOP + 0x0002 restore + gate NOP + Nexus) |
| WDL injection (azrok_launcher.py) | **1 (Nexus=200 only)** |
