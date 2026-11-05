# 0x0007 Deep Analysis: Full Handler Decompilation

Date: 2026-03-31
Source: Ghidra decompilation of HandleS2C_0007_LoadSetupBlob (0x0059E330) + all 25+ sub-functions

## 1. Main Handler: HandleS2C_0007_LoadSetupBlob (0x0059E330) (Complete Decompilation)

The handler takes `param_1` as a pointer to the 472-byte (0x1D8) payload.
Execution order with exact function signatures:

```
1. FUN_0059d860(param_1[1])      → this+300 = byte1 (species A)
2. FUN_0059e2d0(param_1[0])      → this+0x134 = byte0 (status/flag)
3. ProtocolState_SetField130Value(param_1[2])      → this+0x130 = byte2 (species B)
4. FUN_005a8c90(u32@+0x03)       → datetime unpack (YY*1e6+MM*1e4+DD*100+HH)
5. FUN_0059e300(u32@+0x07)       → this+0x1EC = state/phase dword
6. 16 hardcoded byte overwrites  → 0x1AC..0x1D1 region
7. DomainBank_ImportByteBank10(0..3, ...)×4     → 4-group byte array import
8. DomainSelector_ImportByteVector4(+0x1D4, 4)       → 4 bootstrap slot bytes
9. FUN_005a8d40() → FUN_00594b10 → recompose datetime → this+0x879
10. FUN_0059bc00(0x21, +0x97)    → 33-byte keyed list #1
11. FUN_0059bc00(0x0F, +0xB8)    → 15-byte keyed list #2
12. FUN_0059bc00(0x14, +0xC7)    → 20-byte keyed list #3
13. for i=0..10: DomainCode_EmitLocalEffect(+0x125+i) → 11 event bytes
14. for i=0..0x45: Stats_StoreClampedValue(i, u16@+0x0B+i*2) → 70 stat writes
15. virtual call (*vtable+0x28)()
16. FUN_0059bc00(0x26, +0xEA)    → 38-byte keyed list #4
17. FUN_0059bc00(0x03, +0x110)   → 3-byte keyed list #5
18. FUN_0059bc00(0x0A, +0x113)   → 10-byte keyed list #6
19. FUN_0059bc00(0x08, +0x11D)   → 8-byte keyed list #7
20. FUN_0059bc00(0x01, +0x131)   → 1-byte keyed list #8
21. FUN_0059c850(2/3,...) → conditional FUN_0059be80 calls
22. FUN_005a4df0() → evolution stage check (0/1/2/3)
23. for i=0..7: FUN_005aa6f0(i, mode, value) → 8 mode/value pairs
24. 10-slot tri-table filtering → RuntimeRowTable_ImportFrom0007()
25. FUN_005a8d40()==0 → FUN_005a8790(0xFFFFFFFF) fallback
```

## 2. Question 1: byte0 (status/flag) Exact Meaning

### FUN_0059e2d0 Decompilation
```c
void __thiscall FUN_0059e2d0(int this, undefined4 param_2) {
    *(undefined4 *)(this + 0x134) = param_2;
}
```

Simple store to `manager+0x134`. This field is read elsewhere as a status/flag.
The handler does NOT branch on byte0's value directly.

**Downstream usage in SendC2S_0064_LocalBootstrapStatus (0x006130B0) (bootstrap):**
- SendC2S_0064_LocalBootstrapStatus reads `FUN_00545500()` which returns `this+300` (species A = byte1)
- SendC2S_0064_LocalBootstrapStatus reads `FUN_005465c0()` which returns `this+0x130` (species B = byte2)
- byte0 at `this+0x134` is stored but not read during bootstrap

**Conclusion:** byte0 is a status flag that persists in the manager but does not
gate 0x0007 processing itself. Any value (including 0) is accepted. A non-zero
value may indicate "existing character" vs "new character" in later game logic,
but does NOT affect the handler's execution path.

**Recommended value:** `0x00` for new character creation, which is the current
server default.

## 3. Question 2: +0x07 State Dword Valid Values

### FUN_0059e300 Decompilation
```c
void __thiscall FUN_0059e300(int this, undefined4 param_2) {
    *(undefined4 *)(this + 0x1EC) = param_2;
}
```

Simple store to `manager+0x1EC`. This same field is also written by the 0x0005
handler (same function).

### Impact Analysis

The state dword at `this+0x1EC` is NOT directly checked by HandleS2C_0007_LoadSetupBlob.
It IS checked by downstream systems:

1. **FUN_005a4df0 (evolution stage):** Does NOT read 0x1EC. It reads:
   - `FUN_005465c0()` (species B, this+0x130)
   - `FUN_005a49b0(1)` (stat index 1 = level/age)
   - `FUN_005a4d40(0/1)` (sum of stat ranges 0x28..0x2F / 0x31..0x38)
   - virtual call via this+0x334

2. **DispatchState0Common_S2C case 7 → HandleS2C_0007_EmitPostSetupStateRequest (0x0050D290) (level_load):**
   - HandleS2C_0007_EmitPostSetupStateRequest checks `this+0x31C72` and `this+0x31C73`
   - If both zero → calls FUN_0050b090() → FUN_0050a7f0(100)
   - If `+0x31C72` != 0 → FUN_0050a7f0(0x6E) (opcode 110)
   - If `+0x31C73` != 0 → FUN_0050a7f0(0x6F) (opcode 111)

**Conclusion:** The state dword at +0x07 is stored but not directly branched on
during 0x0007 processing. However, 0x0005 also writes to the same location.
If 0x0005 sends state_dword=0 AFTER 0x0007, it clobbers the value.

**Recommended value:** `0x00000000` is safe. The field is a passive store during
0x0007 processing. The 0x0005 handler's state_dword should match.

## 4. Question 3: 70-Stat Bag Index-by-Index Meaning

### Stat Table Architecture

**StatSchema_LoadFallbackAndMapNames** builds a 57-entry schema table at `this+0x5F4`. Each entry is
a 0xC-byte record: `{current_value(4), min_value(4), max_value(4)}`.

**StatSchema_LookupIdByName** maps stat names to indices via a runtime name table at
`DAT_006ea57c` with 71 (0x47) entries, each 0x13 bytes (4-byte index + 15-byte
name string). The name table is populated at runtime from data files.

**Stats_StoreClampedValue** (stat writer) logic:
```c
void Stats_StoreClampedValue(int *this, int idx, int value) {
    if (idx < 0 || idx >= 0x47) return;  // bounds: 0..70

    int min = *(this[0x17d] + 4 + idx * 0xC);   // per-index min
    int max = FUN_005a4a50(idx);                  // per-index max

    if (min <= value && value <= max) {
        *(idx * 0xC + this[0x17d]) = value;       // accept as-is
    } else if (max < value) {
        *(idx * 0xC + this[0x17d]) = FUN_005a4a50(idx); // clamp to max
        (*vtable+0x14)(7, idx, value);            // notify overflow
    } else {
        *(idx * 0xC + this[0x17d]) = min;         // clamp to min
        (*vtable+0x14)(7, idx, value);            // notify underflow
    }
}
```

**FUN_005a4a50** (get max) has a special case for index 9:
```c
int FUN_005a4a50(int this, int idx) {
    if (idx == 9) {
        int evolution = (**(this+0x334+8))(10);  // get evolution level
        if (evolution == 0x1E) return 500;       // stage 30
        if (evolution == 0x1F) return 600;       // stage 31
        if (evolution == 0x20) return 700;       // stage 32
    }
    if (idx < 0 || idx > 0x46) return 0;
    return *(this+0x5F4 + 8 + idx*0xC);  // read max from schema table
}
```

### Complete 70-Slot Stat Index Map

The 57 schema entries from StatSchema_LoadFallbackAndMapNames, with their binary-hardcoded max values:

| Wire Idx | lgc.tmp Row | Name (Korean) | Min | Max | init.csv Default |
|----------|-------------|---------------|-----|-----|-----------------|
| 0 | 0 | IQ | 0 | 100 | (none, use 0) |
| 1 | 1 | 나이/레벨 | 1 | 30 | 25 |
| 2 | 2 | 건강치 | 0 | 60000 | 33000 |
| 3 | 3 | 행복치 | 0 | 100 | 10 |
| 4 | 4 | 의분치 | 0 | 100 | 80 |
| 5 | 5 | 운동충치 | 0 | 100 | 80 |
| 6 | 6 | 의치 | 0 | 100 | 80 |
| 7 | 7 | 스트레스 | 0 | 100 | 30 |
| 8 | 8 | 변비치 | 0 | 100 | 80 |
| 9 | 9 | 식사카운터 | 0 | 300* | 50 |
| 10 | 10 | 목욕횟수 | 0 | 100 | 50 |
| 11 | 11 | 수면횟수 | 0 | 100 | 50 |
| 12 | 12 | 배변카운터 | 0 | 100 | 50 |
| 13 | 13 | 놀이카운터 | 0 | 100 | 50 |
| 14 | 14 | 음악듣기카운터 | 0 | 100 | 50 |
| 15 | 15 | 세탁카운터 | 0 | 100 | 50 |
| 16 | 16 | 미용실카운터 | 0 | 100 | 50 |
| 17 | 17 | 미용실횟 | 0 | 100 | 50 |
| 18 | 18 | 공부청소도 | 0 | 100 | 80 |
| 19 | 19 | 침실청소도 | 0 | 100 | 80 |
| 20 | 20 | 욕실청소도 | 0 | 100 | 80 |
| 21 | 21 | 거실청소도 | 0 | 100 | 80 |
| 22 | 22 | 부엌청소도 | 0 | 100 | 80 |
| 23 | 23 | 주방청소도 | 0 | 100 | 80 |
| 24 | 24 | 마당청소도 | 0 | 100 | 0 |
| 25 | 25 | 체카카운터 | 0 | 400 | 500→clamped 400 |
| 26 | 26 | 사빈카운터 | 0 | 400 | 500→clamped 400 |
| 27 | 27 | 변비카운터 | 0 | 400 | 500→clamped 400 |
| 28 | 28 | 수면카운터 | 0 | 400 | 500→clamped 400 |
| 29 | 29 | 인스턴트 | 0 | 100 | 80 |
| 30 | 30 | 안기경험 | 0 | 600 | 500 |
| 31 | 31 | 안기카운터 | 0 | 400 | 500→clamped 400 |
| 32 | 32 | 아령경험 | 0 | 450 | 500→clamped 450 |
| 33 | 33 | 다나경험 | 0 | 450 | 500→clamped 450 |
| 34 | 34 | 걸음마경험 | 0 | 450 | 500→clamped 450 |
| 35 | 35 | 달리기경험 | 0 | 450 | 500→clamped 450 |
| 36 | 36 | 줄넘기경험 | 0 | 450 | 500→clamped 450 |
| 37 | 37 | 줄달리기경험 | 0 | 450 | 500→clamped 450 |
| 38 | 38 | 수영경험 | 0 | 450 | 500→clamped 450 |
| 39 | 39 | 스키경험 | 0 | 450 | 500→clamped 450 |
| 40 | 40 | 포스트경험1 | 0 | 40 | 30 |
| 41 | 41 | 포스트경험2 | 0 | 40 | 30 |
| 42 | 42 | 포스트경험3 | 0 | 40 | 30 |
| 43 | 43 | 포스트경험4 | 0 | 40 | 30 |
| 44 | 44 | 포스트경험5 | 0 | 40 | 30 |
| 45 | 45 | 성장경험1 | 0 | 80 | 70 |
| 46 | 46 | 성장경험2 | 0 | 80 | 70 |
| 47 | 47 | 성장경험3 | 0 | 80 | 70 |
| 48 | 48 | 성장경험4 | 0 | 80 | 70 |
| 49 | 49 | 성장경험5 | 0 | 80 | 70 |
| 50 | 50 | 소소경험1 | 0 | 120 | 110 |
| 51 | 51 | 소소경험2 | 0 | 120 | 110 |
| 52 | 52 | 소소경험3 | 0 | 120 | 110 |
| 53 | 53 | 소소경험4 | 0 | 120 | 110 |
| 54 | 54 | 소소경험5 | 0 | 120 | 110 |
| 55 | 55 | 펫진화 | 0 | 4 | 1 |
| 56 | 56 | 펫 | 0 | 3 | 2 |
| 57-69 | -- | (no schema entry) | 0 | 0 | 0 (only valid) |

*Index 9 max is dynamic: 300 (default), 500/600/700 based on evolution stage.

**Key insight:** Indices 57-69 have NO schema entries. FUN_005a4a50 returns 0
for their max. Stats_StoreClampedValue will clamp any non-zero value to 0. Sending 0 for
these is the only correct choice.

### init.csv Mapping

init.csv has 55 rows. It maps to stat indices 1..56 (skipping index 0 = IQ,
which has no init.csv row). The init.csv "default" column provides starting
current values. Values exceeding the binary max are clamped by Stats_StoreClampedValue.

**Clamping cases from init.csv:**
- Indices 25-28: init=500, max=400 → clamped to 400
- Index 31: init=500, max=400 → clamped to 400
- Indices 32-39: init=500, max=450 → clamped to 450

## 5. Question 4: FUN_005a4a50 Per-Index Max Table

### Architecture
```
this+0x5F4 → pointer to stat schema array
  each entry: 0xC bytes = {current(4), min(4), max(4)}
  max is at offset +8 within each entry

FUN_005a4a50(idx):
  if idx == 9:  // special dynamic max for 식사카운터
    evolution = vtable_call(10)
    if evolution == 30: return 500
    if evolution == 31: return 600
    if evolution == 32: return 700
  if idx < 0 or idx > 70: return 0
  return this+0x5F4[idx].max    // schema_ptr + 8 + idx*0xC
```

The table is populated by StatSchema_LoadFallbackAndMapNames which hardcodes all 57 max values.
The complete max table is listed in the stat index map above (Section 4).

### Schema-to-Wire Relationship
- StatSchema_LoadFallbackAndMapNames creates 57 schema entries
- StatSchema_LookupIdByName maps names → indices in a 71-slot runtime table
- The 0x0007 wire bag has 70 u16 slots (indices 0..69)
- Only indices 0..56 have schema-backed min/max
- Indices 57..69: max=0 from uninitialized schema → only value 0 accepted
- Special indices 0x43(67), 0x44(68) in StatSchema_LookupIdByName are name-matched but
  handled specially (species B set, pet skip) — NOT part of the stat array

## 6. Question 5: DispatchState0Common_S2C → HandleS2C_0007_EmitPostSetupStateRequest (0x0050D290) Level Load Branch

### DispatchState0Common_S2C (dispatcher, case 7)
```c
case 7:
    HandleS2C_0007_EmitPostSetupStateRequest(param_3);
    break;
```

### HandleS2C_0007_EmitPostSetupStateRequest (0x0050D290) (level_load)
```c
void HandleS2C_0007_EmitPostSetupStateRequest(int this) {
    FUN_005094c0();    // pre-load cleanup
    FUN_005eab20();    // engine prep

    if (*(char*)(this + 0x31C72) == 0) {
        if (*(char*)(this + 0x31C73) == 0) {
            FUN_0050b090();           // → FUN_0050a7f0(100)
        } else {
            FUN_0050a7f0(0x6F);       // opcode 111
        }
    } else {
        FUN_0050a7f0(0x6E);           // opcode 110
    }
}
```

### Branch Conditions
- `this+0x31C72`: Set by DispatchState0Common_S2C case 4 when `*param_3 == -1 (0xFF)`:
  sets `this+0x31C71 = 1` and runs additional init
- `this+0x31C73`: Set elsewhere (not by 0x0007 handler)

### FUN_0050a7f0
```c
void FUN_0050a7f0(int this, int param_2) {
    *(this + 0x31AAD) = param_2;   // store level/scene ID
    FUN_004ed2a0(param_2);          // engine level load
    FUN_005ca710(param_2);          // post-load init
}
```

### FUN_0050b090
```c
void FUN_0050b090(void) {
    FUN_0050a7f0(100);   // load level 100 (= default/main scene)
}
```

**Conclusion:** The level_load path depends on `this+0x31C72` and `this+0x31C73`:
- Both zero → load level 100 (default main scene)
- `+0x31C72` set → load level 0x6E (110) — tutorial/intro scene
- `+0x31C73` set → load level 0x6F (111) — alternate scene

The 0x0007 handler does NOT directly set these flags. They are set by
other message handlers (case 4 of DispatchState0Common_S2C sets +0x31C72 when byte=0xFF).

## 7. Additional Sub-Function Analysis

### FUN_005a4df0 (Evolution Stage Calculator)
```c
int FUN_005a4df0(int this) {
    if (FUN_005465c0() == 0) return 0;  // species B == 0 → stage 0

    // Stage 3: level > 20 AND sum(stats 0x31..0x38) > 300 AND vtable(1) > 4
    if (FUN_005a49b0(1) > 20 &&
        FUN_005a4d40(1) > 300 &&
        vtable_call(1) > 4)
        return 3;

    // Stage 2: level > 10 AND sum(stats 0x28..0x2F) > 150 AND vtable(1) > 3
    if (FUN_005a49b0(1) > 10 &&
        FUN_005a4d40(0) > 150 &&
        vtable_call(1) > 3)
        return 2;

    return 1;  // default stage
}
```

**Critical:** If species B (byte2) is 0, evolution stage = 0. This means:
- The `if (iVar2 == 1)` and `if (iVar2 == 2)` branches in the main handler
  are BOTH skipped when byte2=0
- FUN_0059be80 calls (consuming keyed list entries) never execute
- FUN_0059b6d0(0,0) never executes
- This is a SAFE path but means evolution features are disabled

**Stat sums checked:**
- `FUN_005a4d40(0)`: sum of stat indices 0x28..0x2F (40..47) = 성장경험1..성장경험5 + 3 more
- `FUN_005a4d40(1)`: sum of stat indices 0x31..0x38 (49..56) = 소소경험1..소소경험5 + 3 more

### FUN_005aa6f0 (Mode/Value Pair Writer)
```c
void FUN_005aa6f0(int this, int idx, int mode, int value) {
    if (FUN_005465c0() == 0 && mode > 1) {
        mode = 2;  // clamp mode to max 2 when species B is 0
    }
    *(this + 0x6C8 + idx * 8) = mode;
    if (value != 0) {
        *(this + 0x6CC + idx * 8) = value;
    }
}
```

**Key behavior:** When species B (byte2) = 0, any mode > 1 is clamped to 2.
Mode 0 and value 0 are safe defaults.

### RuntimeRowTable_ImportFrom0007 (Tri-Table Import)
```c
int RuntimeRowTable_ImportFrom0007(int this, short* tri_data, int datetime) {
    this+0x7FC = FUN_005a8ea0(datetime, 200);  // add 200 days to datetime

    if (tri_data == NULL) return 0;

    for (i = 0; i < 10; i++) {
        if (tri_data[i] == 0xFF)
            id = 0xFF;
        else
            id = (uint)tri_data[i];

        *(this + 0x70C + i*0xC) = id;           // slot ID
        *(this + 0x710 + i*0xC) = tri_data[0x14 + i*2];  // aux
        *(this + 0x714 + i*0xC) = tri_data[0x28 + i*4];  // payload
    }
    return 1;
}
```

The main handler pre-filters: only entries with ID < 6 OR ID == 0xFF pass
through. Invalid entries (ID >= 6 and != 0xFF) are dropped and replaced with
0xFF sentinel entries.

### FUN_005a8ea0 (Date Arithmetic)
Adds two packed dates (YY*1e6+MM*1e4+DD*100+HH format) with proper
day/month/year rollover handling. Used to compute `datetime + 200 days`
for tri-table expiry.

### DomainCode_EmitLocalEffect (Event Byte Processor)
Groups via DomainCode_ClassifyBucket:
```
Value 0..32    → group 0 (stat triggers: 0→+5/+5, 1→+10/+10, 2→+15/+15,
                           18→+4/+3, 19→+7/+6, 20→+8/+7, 21→+5, 22→+10, 23→+15)
Value 1000..1032 → group 3 (action counters)
Value 1500..1502 → group 4
Value 2000..2009 → group 1
Value 2500..2507 → group 2
Value 3000       → group 5
Value 4000..4005 → group 6
Value 5000..5002 → group 7
Value 0xFF(255)  → returns -1 → IGNORED (safe sentinel)
```

**DANGER:** Value 0 maps to group 0 and triggers stat modifications (+5/+5 via
FUN_0059ab40). This is NOT a no-op! Use 0xFF as sentinel.

### FUN_0059bc00 (Keyed Byte-List Importer)
```c
for (i = 0; i < count; i++) {
    if (data[i] != 0 && (mode == 0 || slot[i] == 0)) {
        slot[i] = data[i];
        total += data[i];
    }
}
```
- Value 0 = skip (safe empty marker)
- Non-zero values only written if target slot is empty (when mode=1)
- Zero-filling these regions is safe

### DomainBank_ImportByteBank10 (4-Group Byte Array Import)
```c
void DomainBank_ImportByteBank10(int this, int group, byte* src, int count) {
    for (i = 0; i < count; i++) {
        *(this + 0x138 + group*0x28 + i*4) = (uint)src[i];
    }
}
```
Stores byte values as dwords at `this+0x138 + group*0x28`.

### DomainSelector_ImportByteVector4 (Bootstrap Slot Copy)
```c
void DomainSelector_ImportByteVector4(int this, byte* src, int count) {
    for (i = 0; i < count; i++) {
        *(this + 0x1D8 + i*4) = (uint)src[i];
    }
}
```
These 4 values are later read by FUN_005ab2b0 in SendC2S_0064_LocalBootstrapStatus and passed to
FUN_00521e90(slot, value, 0). Value 0 selects lowest valid ID; 0xFF is clear.

## 8. SendC2S_0064_LocalBootstrapStatus (0x006130B0) Bootstrap Flow

The bootstrap function reads:
1. `FUN_00545500()` → species A (byte1) from this+300
2. `FUN_005465c0()` → species B (byte2) from this+0x130
3. `FUN_005286e0()` → 13-byte name string
4. `FUN_005ab2b0(0..3)` → 4 bootstrap slot values from +0x1D4
5. Calls `FUN_00521e90(slot, value, 0)` for each of the 4 slots
6. Calls `FUN_005270d0()` → if returns 0, runs additional init
7. Calls `FUN_005ab710()` and `FUN_006133b0(0x6E)` at the end

## 9. Server Payload Recommendations

> **SUPERSEDED by 113 (domain-bank recommendation only).** `+0x1AC..+0x1D3`의 “only 13 server bytes / zero-fill safe”는 틀렸습니다. 네 그룹 40개가 모두 import되고 downstream은 `0xFF`만 empty로 취급합니다. 이 절의 다른 역사적 권고도 최신 INDEX의 개별 정정을 우선합니다.

### Current Issues in azrok_server.py

1. **byte2 (species B) = 0 from client echo:**
   Current code echoes `client_payload[2]` which is typically 0.
   This disables evolution (FUN_005a4df0 returns 0) and clamps mode values.
   **Fix:** Set byte2 = byte1 (same species) for full feature enablement.

2. **+0x07 state dword = 0:**
   Currently echoed from client which sends 0. This is safe for 0x0007
   but 0x0005 should match. Current behavior is acceptable.

3. **Stat bag all zeros:**
   Current code keeps client-provided zeros. For a playable character,
   should use init.csv defaults (clamped to binary maxes).

### Recommended 0x0007 Payload Construction

```python
payload = bytearray(0x1D8)

# +0x00: status flag (0 = new character)
payload[0x00] = 0x00

# +0x01: species A (char_type)
payload[0x01] = char_type & 0xFF

# +0x02: species B (MUST be non-zero for evolution)
payload[0x02] = char_type & 0xFF  # same as byte1

# +0x03..0x06: packed datetime (current time)
dt = YY*1000000 + MM*10000 + DD*100 + HH
struct.pack_into('<I', payload, 0x03, dt)

# +0x07..0x0A: state dword (0 is safe)
struct.pack_into('<I', payload, 0x07, 0)

# +0x0B..0x96: 70 u16 stats from init.csv (indices 0..69)
# See stat table above for values. Indices 57-69 MUST be 0.
stat_defaults = [
    0,     # 0: IQ
    25,    # 1: level/age
    33000, # 2: health
    10,    # 3: happiness
    80,    # 4: loyalty
    80,    # 5: exercise
    80,    # 6: will
    30,    # 7: stress
    80,    # 8: constipation
    50,    # 9: meal counter (max 300, dynamic up to 700)
    50,    # 10: bath count
    50,    # 11: sleep count
    50,    # 12: excretion counter
    50,    # 13: play counter
    50,    # 14: music counter
    50,    # 15: laundry counter
    50,    # 16: salon counter
    50,    # 17: salon visits
    80,    # 18-23: room cleanliness (6 rooms)
    80, 80, 80, 80, 80,
    0,     # 24: yard cleanliness
    400,   # 25-28: cleaning counters (clamped from 500)
    400, 400, 400,
    80,    # 29: instant food
    500,   # 30: holding exp (max 600)
    400,   # 31: holding counter (clamped from 500)
    450,   # 32-39: skill exp (clamped from 500)
    450, 450, 450, 450, 450, 450, 450,
    30,    # 40-44: post exp
    30, 30, 30, 30,
    70,    # 45-49: growth exp
    70, 70, 70, 70,
    110,   # 50-54: social exp
    110, 110, 110, 110,
    1,     # 55: pet evolution
    2,     # 56: pet
    0,0,0,0,0,0,0,0,0,0,0,0,0  # 57-69: unused (MUST be 0)
]
for i, v in enumerate(stat_defaults):
    struct.pack_into('<H', payload, 0x0B + i*2, v)

# +0x97..+0x131: keyed byte lists (0 = skip, safe default)
# Already zero-filled

# +0x125..+0x12F: event bytes (0xFF = safe no-op)
for i in range(11):
    payload[0x125 + i] = 0xFF

# +0x131: keyed list #8 (0 = skip)
payload[0x131] = 0x00

# +0x134..+0x183: tri-table (0xFF = empty sentinel)
for i in range(10):
    struct.pack_into('<H', payload, 0x134 + i*2, 0x00FF)
    struct.pack_into('<H', payload, 0x148 + i*2, 0x00FF)
    struct.pack_into('<I', payload, 0x15C + i*4, 0)

# +0x184..+0x1AB: 8 mode/value pairs (0/0 = safe)
# Already zero-filled

# +0x1AC..+0x1D3: 4-group byte array
# 16 bytes are hardcode-overwritten, only 13 server bytes matter
# Zero-fill is safe

# +0x1D4..+0x1D7: bootstrap slots (0xFF = clear sentinel)
for i in range(4):
    payload[0x1D4 + i] = 0xFF
```

## 10. Summary of Findings

| Question | Answer |
|----------|--------|
| byte0 meaning | Status flag stored at manager+0x134. 0=new char, does NOT gate handler logic. |
| +0x07 state dword | Stored at manager+0x1EC. 0 is safe. Not branched during 0x0007. |
| 70 stat indices | 57 schema-backed (idx 0-56, matching lgc.tmp). 13 unused (idx 57-69, MUST be 0). |
| Per-index max table | Hardcoded in StatSchema_LoadFallbackAndMapNames. 56/57 match lgc.tmp exactly. Idx 9 has dynamic max. |
| level_load branch | HandleS2C_0007_EmitPostSetupStateRequest checks +0x31C72/+0x31C73 flags. Both 0 → load level 100. NOT set by 0x0007. |
| byte2 importance | species B=0 disables evolution, clamps modes. Should be = byte1 for full features. |
| init.csv fit | Maps to stat indices 1-56. 13 values exceed binary max and get clamped. |

## Handler Hardcoded Overwrites (0x1AC region)

> **SUPERSEDED by 113 (server-meaningful range conclusion).** 아래 16개 overwrite 표 자체는 유효하지만, 나머지가 13바이트뿐이라는 결론은 틀렸습니다. count=10×4 import와 full-bank consumer에 따라 서버 제어 범위는 24바이트입니다.

(Merged from 07_0x0007_complete_field_map.md)

The handler overwrites 16 bytes with constants BEFORE `DomainBank_ImportByteBank10` processes
them. Server values at these offsets are ignored:

| Offset | Group | Index | Hardcoded Value |
|--------|-------|-------|-----------------|
| +0x1B0 | 0 | 4 | 4 |
| +0x1B1 | 0 | 5 | 5 |
| +0x1B2 | 0 | 6 | 6 |
| +0x1B3 | 0 | 7 | 7 |
| +0x1B4 | 0 | 8 | 8 |
| +0x1B5 | 0 | 9 | 9 |
| +0x1BB | 1 | 5 | 5 |
| +0x1BC | 1 | 6 | 6 |
| +0x1C3 | 2 | 3 | 3 |
| +0x1CB | 3 | 1 | 1 |
| +0x1CC | 3 | 2 | 2 |
| +0x1CD | 3 | 3 | 3 |
| +0x1CE | 3 | 4 | 4 |
| +0x1CF | 3 | 5 | 5 |
| +0x1D0 | 3 | 6 | 6 |
| +0x1D1 | 3 | 7 | 7 |

Server-meaningful bytes per group:
- Group 0 [+0x1AC..+0x1AF]: 4 bytes
- Group 1 [+0x1B6..+0x1BA]: 5 bytes
- Group 2 [+0x1C0..+0x1C2]: 3 bytes
- Group 3 [+0x1CA]: 1 byte
