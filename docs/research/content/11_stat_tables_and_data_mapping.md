# S->C 0x0005 + 0x000A + 0x000B Analysis: Stat Tables and init.csv Mapping

Date: 2026-03-31
Source: Ghidra decompilation + init.csv / lgc.tmp data file analysis

> **Wire opcodes: 0x000A (stat registry) and 0x000B (XP curve). Some older references use 0x0010/0x0011 which were the internal opcode numbers before correction.**

---

## 1. Overview

The client uses a **57-entry indexed stat system** (indices 0x00..0x38) that is populated from
three independent sources:

| Source | Mechanism | Scope |
|--------|-----------|-------|
| **init.csv** | StatSchema_LoadFallbackAndMapNames file parser at startup | 55 rows (index 1..56, no IQ) |
| **lgc.tmp** | Same parser, includes IQ + counters | 57 rows (index 0..56) |
| **0x0007 +0x0B** | Stats_StoreClampedValue per-index writer | 70 x u16 (indices 0..0x45) |
| **0x000A** | StatRegistry_WriteGroupedKeyValue keyed-registry writer | 7 groups, 75 u16 total |

Packets 0x0005 and 0x000B serve different roles (state dword and XP curve).

---

## 2. Packet 0x0005 (FUN_0059ebd0) -- Post-Load State

### Decompiled Logic

```c
void FUN_0059ebd0(char *param_1) {
    if (param_1[1] == 0x13) {        // subtype 0x13
        if (*param_1 == 0x00) {      // status == 0 (success)
            FUN_005a9b50();          // stat registry reload from 0x0007 data
            FUN_0059e300(*(u32*)(param_1 + 2));  // write state dword
        } else {
            FUN_005a9b20();          // error/reset path
        }
    }
    else if (param_1[1] == 0x12) {   // subtype 0x12
        if (*param_1 == 0x00) {
            FUN_0059e300(*(u32*)(param_1 + 2));  // write state dword only
        }
    }
    else if (param_1[1] == 0x00 && *param_1 == 0x00) {  // subtype 0x00
        FUN_0059e300(*(u32*)(param_1 + 2));              // write state dword only
    }
}
```

### Payload Layout (6 bytes)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| +0x00 | u8 | status | 0x00 = success, else error |
| +0x01 | u8 | subtype | 0x00, 0x12, 0x13 |
| +0x02 | u32 | state_dword | Written to manager+0x1EC |

### Subtype Behavior

| Subtype | status=0 | status!=0 |
|---------|----------|-----------|
| **0x00** | Write state_dword | No-op |
| **0x12** | Write state_dword | No-op |
| **0x13** | Reload stat registry + write state_dword | FUN_005a9b20 (error/reset) |

### FUN_005a9b50 (stat registry reload, called on subtype 0x13)

Iterates the 0x0007 payload's stat data (stored at manager+0x811) and calls
FUN_005aa360 for each non-zero entry. This effectively replays the stat values
from the last 0x0007 into the keyed registry system.

### Critical Issue: state_dword Clobbering

Both 0x0007 (+0x07..+0x0A) and 0x0005 (+0x02..+0x05) write to the same
`manager+0x1EC` field via FUN_0059e300. The server currently sends 0x0005
immediately after 0x0007, so 0x0005's state_dword **overwrites** 0x0007's value.

**Fix:** `_build_post_load_0005_draft(state_value=zone_state_word)` correctly
passes the zone state word from 0x0007, preserving consistency.

---

## 3. Packet 0x000A (FUN_0059eca0) -- Keyed Stat Registry

### Decompiled Logic

```c
void FUN_0059eca0(int param_1) {
    FUN_005a9f10();  // clear all 7 registry groups to 0

    // Group 0: 22 entries at +0x00
    for (i = 0; i < 0x16; i++)
        StatRegistry_WriteGroupedKeyValue(0, key_table_0[i], *(u16*)(param_1 + i*2));

    // Group 1: 6 entries at +0x2C
    for (i = 0; i < 6; i++)
        StatRegistry_WriteGroupedKeyValue(1, key_table_1[i], *(u16*)(param_1 + 0x2C + i*2));

    // Group 2: 5 entries at +0x38
    for (i = 0; i < 5; i++)
        StatRegistry_WriteGroupedKeyValue(2, key_table_2[i], *(u16*)(param_1 + 0x38 + i*2));

    // Group 3: 32 entries at +0x42
    for (i = 0; i < 0x20; i++)
        StatRegistry_WriteGroupedKeyValue(3, key_table_3[i], *(u16*)(param_1 + 0x42 + i*2));

    // Group 4: 3 entries at +0x82
    for (i = 0; i < 3; i++)
        StatRegistry_WriteGroupedKeyValue(4, key_table_4[i], *(u16*)(param_1 + 0x82 + i*2));

    // Group 5: 1 entry at +0x88
    for (i = 0; i < 1; i++)
        StatRegistry_WriteGroupedKeyValue(5, key_table_5[i], *(u16*)(param_1 + 0x88 + i*2));

    // Group 6: 6 entries at +0x8A
    for (i = 0; i < 6; i++)
        StatRegistry_WriteGroupedKeyValue(6, key_table_6[i], *(u16*)(param_1 + 0x8A + i*2));
}
```

### StatRegistry_WriteGroupedKeyValue (keyed registry writer)

```c
void StatRegistry_WriteGroupedKeyValue(int group, int key, int value) {
    switch(group) {
        case 0: // DAT_006e1110, 33 slots, 8-byte stride [key, value]
        case 1: // DAT_006e1220, 10 slots
        case 2: // DAT_006e1270,  8 slots
        case 3: // DAT_006e12b0, 33 slots
        case 4: // DAT_006e13b0,  3 slots
        case 5: // DAT_006e13c8,  1 slot
        case 6: // DAT_006e13d0,  6 slots
    }
    // Linear search for matching key, then writes value at key+4
}
```

### FUN_005a9f10 (registry clear)

Zeros the value field of every slot in all 7 groups before populating from the packet.

### Payload Layout (0x96 = 150 bytes)

```
Offset  Size     Group  Count  Description
+0x00   44B (22*u16)  0    22   Core stat current/max pairs
+0x2C   12B (6*u16)   1     6   Counter set A (current/max pairs x3)
+0x38   10B (5*u16)   2     5   Counter set B
+0x42   64B (32*u16)  3    32   Action/activity counters
+0x82    6B (3*u16)   4     3   Cleanliness group
+0x88    2B (1*u16)   5     1   Instant food counter
+0x8A   12B (6*u16)   6     6   Misc counters
Total: 150 bytes (0x96)
```

### Group Key Tables (from memory)

#### Group 0 Keys (DAT_006dfb80 -> DAT_006e1110)

22 keys from a 33-slot registry. The registry stores keys 0..32 in
triplets: `[base, current, max]`. The packet sends only the `current`
and `max` keys (skipping `base` at positions 0, 3, 6, ...).

| Pkt Idx | Key | Registry Meaning | Stat Mapping |
|---------|-----|------------------|--------------|
| 0 | 1 | Triplet 0: current | IQ current |
| 1 | 2 | Triplet 0: max | IQ max |
| 2 | 4 | Triplet 1: current | Level current |
| 3 | 5 | Triplet 1: max | Level max |
| 4 | 7 | Triplet 2: current | EXP current |
| 5 | 8 | Triplet 2: max | EXP max |
| 6 | 10 | Triplet 3: current | Hunger current |
| 7 | 11 | Triplet 3: max | Hunger max |
| 8 | 13 | Triplet 4: current | Hygiene current |
| 9 | 14 | Triplet 4: max | Hygiene max |
| 10 | 16 | Triplet 5: current | Energy current |
| 11 | 17 | Triplet 5: max | Energy max |
| 12 | 19 | Triplet 6: current | Joy current |
| 13 | 20 | Triplet 6: max | Joy max |
| 14 | 22 | Triplet 7: current | Stress current |
| 15 | 23 | Triplet 7: max | Stress max |
| 16 | 25 | Triplet 8: current | Constipation current |
| 17 | 26 | Triplet 8: max | Constipation max |
| 18 | 28 | Triplet 9: current | Bond Energy current |
| 19 | 29 | Triplet 9: max | Bond Energy max |
| 20 | 31 | Triplet 10: current | Exercise current |
| 21 | 32 | Triplet 10: max | Exercise max |

Binary defaults: current=1000 (0x3E8), max=2000 (0x7D0) for all.

#### Group 1 Keys (DAT_006dfbd8 -> DAT_006e1220)

| Pkt Idx | Key | Binary Default | Meaning |
|---------|-----|----------------|---------|
| 0 | 2002 | 200 | Counter A.0 current |
| 1 | 2003 | 500 | Counter A.0 max |
| 2 | 2005 | 200 | Counter A.1 current |
| 3 | 2006 | 500 | Counter A.1 max |
| 4 | 2008 | 200 | Counter A.2 current |
| 5 | 2009 | 500 | Counter A.2 max |

10-slot registry (keys 2000..2009). Same triplet pattern: [base, current, max].

#### Group 2 Keys (DAT_006dfbf0 -> DAT_006e1270)

| Pkt Idx | Key | Binary Default | Meaning |
|---------|-----|----------------|---------|
| 0 | 2501 | 200 | Counter B.0 current |
| 1 | 2502 | 500 | Counter B.0 max |
| 2 | 2504 | 200 | Counter B.1 current |
| 3 | 2505 | 500 | Counter B.1 max |
| 4 | 2507 | 200 | Counter B.2 current? |

8-slot registry (keys 2500..2507). Asymmetric: only 5 values sent (missing one max).

#### Group 3 Keys (DAT_006dfc10 -> DAT_006e12b0)

32 sequential keys: 1001..1032. 33-slot registry.

Binary defaults follow a pattern by stat type:

| Keys | Count | Default | Init.csv Correspondence |
|------|-------|---------|------------------------|
| 1001..1003 | 3 | 30 | First tier activities |
| 1004..1005 | 2 | 40 | Second tier |
| 1006..1014 | 9 | 100 | Third tier (food/items) |
| 1015..1023 | 9 | 200 | Fourth tier |
| 1024..1032 | 9 | 300 (0x12C) | Fifth tier |

**This maps to init.csv rows 28..53** (activity/game counters + evolution tiers):

| Group3 Idx | Key | init.csv Row | Name | init.csv Value | Max |
|------------|-----|--------------|------|----------------|-----|
| 0 | 1001 | 28 | 걷기감정 | 500 | 600 |
| 1 | 1002 | 29 | 안궁..감정 | 500 | 600 |
| 2 | 1003 | 30 | 아름감정 | 500 | 600 |
| 3 | 1004 | 31 | 다넣감정 | 500 | 600 |
| 4 | 1005 | 32 | 건축물감정 | 500 | 600 |
| 5 | 1006 | 33 | 만들기감정 | 500 | 600 |
| 6 | 1007 | 34 | 운동감정 | 500 | 600 |
| 7 | 1008 | 35 | 바느질감정 | 500 | 600 |
| 8 | 1009 | 36 | 글쓰기감정 | 500 | 600 |
| 9 | 1010 | 37 | 수기감정 | 500 | 600 |
| 10..14 | 1011..1015 | 38..42 | 퍼스트..피프스감정 | 30 | 40 |
| 15..19 | 1016..1020 | 43..47 | 식스..텐감정 | 70 | 80 |
| 20..24 | 1021..1025 | 48..52 | 일레븐..피프틴감정 | 110 | 120 |
| 25..29 | 1026..1030 | -- | (overflow, not in init.csv) | -- | -- |
| 30 | 1031 | 53 | 펫진화 | 1 | 4 |
| 31 | 1032 | 54 | 펫 | 2 | 3 |

#### Group 4 Keys (DAT_006dfc04 -> DAT_006e13b0)

| Pkt Idx | Key | Binary Default | init.csv Correspondence |
|---------|-----|----------------|------------------------|
| 0 | 1500 | 100 | Row 17: 영어청소도 (80) |
| 1 | 1501 | 200 | Row 18: 칭찬청소도 (80) |
| 2 | 1502 | 300 | Row 23: 운동청소도 (0) |

#### Group 5 Key (DAT_006dfc90 -> DAT_006e13c8)

| Pkt Idx | Key | Binary Default | Meaning |
|---------|-----|----------------|---------|
| 0 | 3000 | 200 | Instant food counter |

#### Group 6 Keys (DAT_006dfc94 -> DAT_006e13d0)

| Pkt Idx | Key | Binary Default | Meaning |
|---------|-----|----------------|---------|
| 0 | 4000 | 100 | Misc counter 0 |
| 1 | 4001 | 500 | Misc counter 1 |
| 2 | 4002 | 100 | Misc counter 2 |
| 3 | 4003 | 500 | Misc counter 3 |
| 4 | 4004 | 100 | Misc counter 4 |
| 5 | 4005 | 500 | Misc counter 5 |

Triplet pattern: [current=100, max=500] x 3.

---

## 4. Packet 0x000B (FUN_0059eee0) -- XP Level Curve

### Decompiled Logic

```c
void FUN_0059eee0(undefined4 param_1) {
    FUN_005a50f0(param_1);  // direct delegation
}

void FUN_005a50f0(int param_1) {
    for (i = 0; i < 0x1F; i++) {  // 31 entries
        DAT_006e0a88[i] = (uint)*(u16*)(param_1 + i*2);
    }
}
```

### Payload Layout (0x3E = 62 bytes)

31 x u16 little-endian values. Each u16 is zero-extended to u32 and stored in
`DAT_006e0a88[i]`. This is the **experience points required per level** table.

### XP Curve Values

| Level | XP Required | Delta |
|-------|-------------|-------|
| 0 | 0 | -- |
| 1 | 100 | +100 |
| 2 | 300 | +200 |
| 3 | 600 | +300 |
| 4 | 1000 | +400 |
| 5 | 1500 | +500 |
| 6 | 2100 | +600 |
| 7 | 2800 | +700 |
| 8 | 3600 | +800 |
| 9 | 4500 | +900 |
| 10 | 5500 | +1000 |
| 11 | 6600 | +1100 |
| 12 | 7800 | +1200 |
| 13 | 9100 | +1300 |
| 14 | 10500 | +1400 |
| 15 | 12000 | +1500 |
| 16 | 13600 | +1600 |
| 17 | 15300 | +1700 |
| 18 | 17100 | +1800 |
| 19 | 19000 | +1900 |
| 20 | 21000 | +2000 |
| 21 | 23100 | +2100 |
| 22 | 25300* | +2200 |
| 23 | 27600 | +2300 |
| 24 | 30000 | +2400 |
| 25 | 32500 | +2500 |
| 26 | 35100 | +2600 |
| 27 | 37800 | +2700 |
| 28 | 40600 | +2800 |
| 29 | 43500 | +2900 |
| 30 | 60001 | sentinel |

*Note: The binary default at index 22 is **25300**, but the server currently sends
**25500**. The binary value of 25300 follows the arithmetic progression (+2200
from 23100) more consistently. **Server should use 25300.**

### Relationship to Stats

The XP curve is consumed by `FUN_005a4a50` indirectly: stat index 9 (Bond Energy)
has a level-dependent max override at levels 30/31/32 (returning 500/600/700).
For all other stats, `FUN_005a4a50` simply reads the max from the stat schema
array at `manager+0x5f4 + index*0xc + 8`.

---

## 5. The 57-Entry Stat Schema (StatSchema_LoadFallbackAndMapNames)

This function initializes a 57-entry schema array. Each entry is a 16-byte
struct: `{ char* name, int default, int min, int max }`.

The function calls `StatSchema_LookupIdByName(name)` for each entry, which does a string
lookup in a 71-entry (0x47) name table at `DAT_006ea57c`. The lookup returns
a **stat index** (0..0x46), and two special cases:

- Index 0x45 (69): writes to `manager+0x6BC` (evolution stage A)
- Index 0x46 (70): writes to `manager+0x6C0` (evolution stage B)
- Index 0x43 (67): calls `ProtocolState_SetField130Value(0xFF)` (species B reset)
- Index 0x44 (68): no-op

For normal indices (0..0x42), the values are stored in a 12-byte-stride
array at `manager+0x5f4`:

```
index*0xc + offset -> default value
index*0xc + offset + 4 -> min value
index*0xc + offset + 8 -> max value
```

### Complete Stat Index Map

| Idx | lgc.tmp Row | init.csv Row | Name (EUC-KR) | Default | Min | Max |
|-----|-------------|--------------|----------------|---------|-----|-----|
| 0 | 0 | -- | IQ | 0 | 0 | 100 |
| 1 | 1 | 0 | 레벨 | 0 | 1 | 30 |
| 2 | 2 | 1 | 경험치 | 0 | 0 | 60000 |
| 3 | 3 | 2 | 허기치 | 0 | 0 | 100 |
| 4 | 4 | 3 | 위생치 | 0 | 0 | 100 |
| 5 | 5 | 4 | 에너지치 | 0 | 0 | 100 |
| 6 | 6 | 5 | 즐거운치 | 0 | 0 | 100 |
| 7 | 7 | 6 | 스트레스 | 0 | 0 | 100 |
| 8 | 8 | 7 | 변비치 | 0 | 0 | 100 |
| 9 | 9 | 8 | 본드에너지 | 0 | 0 | 300 |
| 10 | 10 | 9 | 운동량 | 0 | 0 | 100 |
| 11 | 11 | 10 | 매력도 | 0 | 0 | 100 |
| 12 | 12 | 11 | 사회적지능 | 0 | 0 | 100 |
| 13 | 13 | 12 | 언어적지능 | 0 | 0 | 100 |
| 14 | 14 | 13 | 논리수학적지능 | 0 | 0 | 100 |
| 15 | 15 | 14 | 공간시각적지능 | 0 | 0 | 100 |
| 16 | 16 | 15 | 미술지능 | 0 | 0 | 100 |
| 17 | 17 | 16 | 미술도 | 0 | 0 | 100 |
| 18 | 18 | 17 | 영어청소도 | 0 | 0 | 100 |
| 19 | 19 | 18 | 칭찬청소도 | 0 | 0 | 100 |
| 20 | 20 | 19 | 놀이청소도 | 0 | 0 | 100 |
| 21 | 21 | 20 | 음악청소도 | 0 | 0 | 100 |
| 22 | 22 | 21 | 외출청소도 | 0 | 0 | 100 |
| 23 | 23 | 22 | 주방청소도 | 0 | 0 | 100 |
| 24 | 24 | 23 | 운동청소도 | 0 | 0 | 100 |
| 25 | 25 | 24 | 청소카운터 | 0 | 0 | 400 |
| 26 | 26 | 25* | 식사카운터 | 0 | 0 | 400 |
| 27 | 27 | 25 | 변비카운터 | 0 | 0 | 400 |
| 28 | 28 | 26 | 목욕카운터 | 0 | 0 | 400 |
| 29 | 29 | 27 | 인스턴트 | 0 | 0 | 100 |
| 30 | 30 | 28 | 걷기감정 | 0 | 0 | 600 |
| 31 | 31 | 29 | 안궁..감정 | 0 | 0 | 400 |
| 32 | 32 | 30 | 아름감정 | 0 | 0 | 450 |
| 33 | 33 | 31 | 다넣감정 | 0 | 0 | 450 |
| 34 | 34 | 32 | 건축물감정 | 0 | 0 | 450 |
| 35 | 35 | 33 | 만들기감정 | 0 | 0 | 450 |
| 36 | 36 | 34 | 운동감정 | 0 | 0 | 450 |
| 37 | 37 | 35 | 바느질감정 | 0 | 0 | 450 |
| 38 | 38 | 36 | 글쓰기감정 | 0 | 0 | 450 |
| 39 | 39 | 37 | 수기감정 | 0 | 0 | 450 |
| 40 | 40 | 38 | 퍼스트감정 | 0 | 0 | 40 |
| 41 | 41 | 39 | 세컨드감정 | 0 | 0 | 40 |
| 42 | 42 | 40 | 서드감정 | 0 | 0 | 40 |
| 43 | 43 | 41 | 포스감정 | 0 | 0 | 40 |
| 44 | 44 | 42 | 피프스감정 | 0 | 0 | 40 |
| 45 | 45 | 43 | 식스감정 | 0 | 0 | 80 |
| 46 | 46 | 44 | 세븐감정 | 0 | 0 | 80 |
| 47 | 47 | 45 | 에잇감정 | 0 | 0 | 80 |
| 48 | 48 | 46 | 나인감정 | 0 | 0 | 80 |
| 49 | 49 | 47 | 텐감정 | 0 | 0 | 80 |
| 50 | 50 | 48 | 일레븐감정 | 0 | 0 | 120 |
| 51 | 51 | 49 | 트웰브감정 | 0 | 0 | 120 |
| 52 | 52 | 50 | 써틴감정 | 0 | 0 | 120 |
| 53 | 53 | 51 | 포틴감정 | 0 | 0 | 120 |
| 54 | 54 | 52 | 피프틴감정 | 0 | 0 | 120 |
| 55 | 55 | 53 | 펫진화 | 0 | 0 | 4 |
| 56 | 56 | 54 | 펫 | 0 | 0 | 3 |

*Note: init.csv has 55 rows (no IQ). lgc.tmp has 57 rows (adds IQ at row 0
and 식사카운터 between 청소카운터 and 변비카운터).

### FUN_005a4a50 (per-index max lookup)

```c
int FUN_005a4a50(int param_1, int param_2) {
    if (param_2 == 9) {  // Bond Energy has level-dependent max
        int level = vtable_call(manager+0x334, 10);
        if (level == 30) return 500;
        if (level == 31) return 600;
        if (level == 32) return 700;
    }
    if (param_2 < 0 || param_2 > 0x46) return 0;
    return schema_array[param_2].max;  // manager+0x5f4 + param_2*0xc + 8
}
```

---

## 6. init.csv -> 0x0007 Stat Bag Mapping (+0x0B..+0x96)

The 0x0007 packet carries 70 x u16 values at offset +0x0B. Each u16 is written
to stat index `i` via `Stats_StoreClampedValue(i, value)` for `i = 0..0x45` (0..69).

The first 57 indices (0..56) correspond exactly to the stat schema above.
Indices 57..69 are additional slots (some used for evolution/special states).

### Recommended init.csv Values for 0x0007

| 0x0007 Offset | Stat Idx | init.csv Row | Name | Value | Max |
|---------------|----------|--------------|------|-------|-----|
| +0x0B | 0 | -- | IQ | 0 | 100 |
| +0x0D | 1 | 0 | 레벨 | 25 | 30 |
| +0x0F | 2 | 1 | 경험치 | 33000 | 60000 |
| +0x11 | 3 | 2 | 허기치 | 10 | 100 |
| +0x13 | 4 | 3 | 위생치 | 80 | 100 |
| +0x15 | 5 | 4 | 에너지치 | 80 | 100 |
| +0x17 | 6 | 5 | 즐거운치 | 80 | 100 |
| +0x19 | 7 | 6 | 스트레스 | 30 | 100 |
| +0x1B | 8 | 7 | 변비치 | 80 | 100 |
| +0x1D | 9 | 8 | 본드에너지 | 50 | 300 |
| +0x1F | 10 | 9 | 운동량 | 50 | 100 |
| +0x21 | 11 | 10 | 매력도 | 50 | 100 |
| +0x23 | 12 | 11 | 사회적지능 | 50 | 100 |
| +0x25 | 13 | 12 | 언어적지능 | 50 | 100 |
| +0x27 | 14 | 13 | 논리수학적지능 | 50 | 100 |
| +0x29 | 15 | 14 | 공간시각적지능 | 50 | 100 |
| +0x2B | 16 | 15 | 미술지능 | 50 | 100 |
| +0x2D | 17 | 16 | 미술도 | 50 | 100 |
| +0x2F | 18 | 17 | 영어청소도 | 80 | 100 |
| +0x31 | 19 | 18 | 칭찬청소도 | 80 | 100 |
| +0x33 | 20 | 19 | 놀이청소도 | 80 | 100 |
| +0x35 | 21 | 20 | 음악청소도 | 80 | 100 |
| +0x37 | 22 | 21 | 외출청소도 | 80 | 100 |
| +0x39 | 23 | 22 | 주방청소도 | 80 | 100 |
| +0x3B | 24 | 23 | 운동청소도 | 0 | 100 |
| +0x3D | 25 | 24 | 청소카운터 | 500 | 400* |
| +0x3F | 26 | 25 | 변비카운터 | 500 | 400* |
| +0x41 | 27 | 26 | 목욕카운터 | 500 | 400* |
| +0x43 | 28 | -- | (lgc.tmp-only) | 0 | 400 |
| +0x45 | 29 | 27 | 인스턴트 | 80 | 100 |
| +0x47 | 30..56 | 28..54 | (activity + evol) | ... | ... |
| +0x7D | 57..69 | -- | (extra slots) | 0 | -- |

*Note: init.csv max (600) differs from lgc.tmp/schema max (400). The schema
max (from StatSchema_LoadFallbackAndMapNames) is authoritative; Stats_StoreClampedValue clamps to schema max.
Values exceeding the schema max will be clamped down.

---

## 7. 0x000A Group -> init.csv/lgc.tmp Mapping

### Group 0 (22 entries): Core Stats as current/max pairs

The 22 u16 values map to 11 stat triplets. Each triplet's current and max
are sent; the base is not included in the packet.

| Pkt Pair | Stat | init.csv Value | Suggested current | Suggested max |
|----------|------|----------------|-------------------|---------------|
| 0-1 | IQ | -- | 0 | 100 |
| 2-3 | 레벨 | 25 | 25 | 30 |
| 4-5 | 경험치 | 33000 | 33000 | 60000** |
| 6-7 | 허기치 | 10 | 10 | 100 |
| 8-9 | 위생치 | 80 | 80 | 100 |
| 10-11 | 에너지치 | 80 | 80 | 100 |
| 12-13 | 즐거운치 | 80 | 80 | 100 |
| 14-15 | 스트레스 | 30 | 30 | 100 |
| 16-17 | 변비치 | 80 | 80 | 100 |
| 18-19 | 본드에너지 | 50 | 50 | 300 |
| 20-21 | 운동량 | 50 | 50 | 100 |

**Note: 60000 exceeds u16 max (65535) but fits. The server currently sends
`[0, 25, 33000, 10, 80, 80, 80, 30, 80, 50, 50, 50, 50, 50, 50, 50, 50,
50, 80, 80, 80, 80]` which includes 22 values mapping indices 0..17 +
4 cleanliness values -- this needs correction (see section 8).

### Group 3 (32 entries): Activity Counters

Maps directly to init.csv rows 28..53 + 펫진화/펫:

Server `STAT_TABLE_000A_DEFAULTS['group3']` currently sends:
```python
[500, 0, 500, 500, 80, 500, 500, 500, 500, 500, 500, 500, 500, 500,
 500, 30, 30, 30, 30, 30, 70, 70, 70, 70, 70, 110, 110, 110, 110,
 110, 1, 2]
```

This matches init.csv values for the activity counters plus 펫진화=1, 펫=2.

### Group 4 (3 entries): Cleanliness Subset

Maps to specific cleanliness stats:
- Key 1500 -> 영어청소도 (init.csv: 80)
- Key 1501 -> 칭찬청소도 (init.csv: 80)
- Key 1502 -> 운동청소도 (init.csv: 0)

Server `STAT_TABLE_000A_DEFAULTS['group4']` = `[80, 80, 0]` -- **correct**.

---

## 8. Current Server Issues and Fixes

### Issue 1: 0x000B XP Table Index 22

**Binary default:** 25300
**Server sends:** 25500

The binary value follows the arithmetic progression (delta = level * 100 + 100)
more consistently. Fix: change `STAT_TABLE_000B_DEFAULTS[22]` from 25500 to 25300.

### Issue 2: 0x000A Group 0 Mapping

The server's `STAT_TABLE_000A_DEFAULTS['group0']` currently has 22 values:
```python
[0, 25, 33000, 10, 80, 80, 80, 30, 80, 50, 50,
 50, 50, 50, 50, 50, 50, 50, 80, 80, 80, 80]
```

This treats the 22 packet slots as a flat array matching lgc.tmp rows 0..21.
However, the packet actually maps to **registry keys** (1,2,4,5,...,31,32)
which are **current/max pairs** for 11 stat triplets.

Correct mapping should be:
```python
'group0': [
    0, 100,      # IQ current=0, max=100
    25, 30,      # Level current=25, max=30
    33000, 60000, # EXP current=33000, max=60000 (u16 fits)
    10, 100,     # Hunger current=10, max=100
    80, 100,     # Hygiene current=80, max=100
    80, 100,     # Energy current=80, max=100
    80, 100,     # Joy current=80, max=100
    30, 100,     # Stress current=30, max=100
    80, 100,     # Constipation current=80, max=100
    50, 300,     # Bond Energy current=50, max=300
    50, 100,     # Exercise current=50, max=100
]
```

### Issue 3: 0x000A Group 1 and Group 2 Semantics

Groups 1 and 2 use the same triplet pattern (base/current/max) but the
server sends flat values. These groups likely correspond to counter
categories not present in init.csv.

Current binary defaults are reasonable placeholders:
- Group 1: `[200, 500, 200, 500, 200, 500]` (3 x [current=200, max=500])
- Group 2: `[200, 500, 200, 500, 200]` (2 x [current, max] + 1 extra)

### Issue 4: 0x0005 Subtype Selection

The server currently uses `subtype=0x00`. If the client needs the stat
registry reload (FUN_005a9b50) to propagate 0x0007 values into the keyed
registry, **subtype should be 0x13** with `status=0x00`.

However, since 0x000A independently writes to the same keyed registries,
subtype 0x00 may be sufficient if 0x000A is sent after 0x0007.

---

## 9. Memory Layout Summary

### Stat Value Storage (per-index, manager+0x5f4)

```
Base address: *(manager + 0x5f4)
Stride: 12 bytes per index (0xC)

offset + index*0xC + 0: current value (written by Stats_StoreClampedValue from 0x0007)
offset + index*0xC + 4: min value (from schema init)
offset + index*0xC + 8: max value (from schema init)
```

### Keyed Registry Storage (per-group, DAT_006e1110..)

```
Group 0: DAT_006e1110, 33 slots x 8B [key(u32), value(u32)]
Group 1: DAT_006e1220, 10 slots x 8B
Group 2: DAT_006e1270,  8 slots x 8B
Group 3: DAT_006e12b0, 33 slots x 8B
Group 4: DAT_006e13b0,  3 slots x 8B
Group 5: DAT_006e13c8,  1 slot  x 8B
Group 6: DAT_006e13d0,  6 slots x 8B
```

### XP Curve Storage

```
DAT_006e0a88: 31 x u32 (level 0..30 XP thresholds)
Written by 0x000B handler (u16 -> u32 zero-extension)
```

### State Dword

```
manager + 0x1EC: u32 (written by both 0x0005 and 0x0007)
```

---

## 10. Dual-Write Interaction: 0x0007 vs 0x000A

Both 0x0007 and 0x000A write stat values, but to **different storage**:

| Source | Storage | Mechanism |
|--------|---------|-----------|
| 0x0007 +0x0B | Indexed array at manager+0x5f4 | Stats_StoreClampedValue(idx, val) |
| 0x000A | Keyed registry at DAT_006e1110.. | StatRegistry_WriteGroupedKeyValue(group, key, val) |

These are **independent systems**. The indexed array is used for gameplay
clamping (min/max checks). The keyed registry is used for UI display and
possibly save/load. Both need to be consistent for correct behavior.

When 0x0005 subtype=0x13 is sent, FUN_005a9b50 copies data FROM the 0x0007
storage INTO the keyed registry, synchronizing the two systems.

### Recommended Packet Sequence

```
1. 0x0007 (full zone state with stat values at +0x0B)
2. 0x0005 subtype=0x13, status=0x00 (sync stats + set state dword)
   -- OR --
   0x0005 subtype=0x00/0x12 (just set state dword, no sync)
   + 0x000A (explicitly set keyed registry values)
3. 0x000B (XP curve table)
```

Current server sends: `0x0007 -> 0x0005(0x00) -> 0x000A -> 0x000B`

This is valid because 0x000A independently writes the keyed registry,
making the 0x0005 sync unnecessary. If 0x0005 subtype were changed to
0x13, the 0x000A send would overwrite the synced values anyway.
