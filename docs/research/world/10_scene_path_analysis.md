# Scene Path Analysis: 0x0003 + PatHouse Tutorial Room Entry

## Summary

The client's scene/room loading system operates through a two-stage pipeline:

1. **Path arming** (`S->C 0x0003`): sets the space root directory (e.g., `Data\Space\PatHouse`)
2. **Scene code dispatch** (`FUN_0050a0f0`): consumes a queued scene code and calls `level_load()` with a bare `.wmb` filename

The bare filename from `level_load()` resolves relative to the space root set by `0x0003`. The scene code also determines the post-load branch (e.g., `100` for PatHouse tutorial, `0x6e` for Plaza hub).

A critical decision point is `HandleS2C_0007_EmitPostSetupStateRequest` (0x0050D290) (the transition branch selector), called when `S->C 0x0007` arrives. Two flags at `gm+0x31c72` and `gm+0x31c73` determine which loading path opens:

- Both zero: opens loading with code `100` (PatHouse/room.wmb tutorial)
- `gm+0x31c72 != 0`: opens loading with code `0x6e` (Plaza/hansol.wmb)
- `gm+0x31c73 != 0`: opens loading with code `0x6f` (OXQuiz)

For a fresh new character, both flags default to zero, so the default path is **PatHouse tutorial (code 100)**.

---

## 1. S->C 0x0003 Handler: `FUN_0050d200`

```
Address: 0x0050d200
Prototype: void __thiscall FUN_0050d200(int gm, byte *payload)
```

### Decompiled Logic

```c
void FUN_0050d200(int gm, byte *payload) {
    *(uint *)(gm + 0x31c63) = (uint)*payload;   // flag byte
    payload = payload + 1;                        // skip flag
    thunk_FUN_0050c250(payload);                  // returns gm + 0x989 (space root buffer)
    thunk_FUN_005d4070(payload);                  // loading popup path setter
}
```

### Payload Format

| Offset | Size | Meaning |
|--------|------|---------|
| `+0x00` | 1 byte | Flag stored to `gm+0x31c63` |
| `+0x01` | NUL-terminated string | Space root path (e.g., `Data\Space\PatHouse`) |

### What Each Callee Does

- **`FUN_0050c250(payload+1)`**: Simple address computation `gm + 0x989`. This is the space root path buffer. The actual copy happens through the implicit string handling in the caller chain.

- **`FUN_005d4070(payload+1)`**: The loading popup path setter. Key behavior:
  - Guards against running during pet-select (`0x6b`) or lobby (`0x6c`) states
  - Calls `strcpy(popup + 0xdb, path_string)` to copy the space path into the loading popup state
  - Initiates a screen transition effect: `FUN_005d42c0(0x1d, 0xff, 0x8d, 0x21, 1)`
  - Sets a countdown timer: `popup + 0xd7 = 10`
  - Records tick count: `popup + 0xcc = GetTickCount()`

### Practical Meaning

`0x0003` arms the space root directory but does NOT directly trigger `level_load()`. It prepares the local state so that when the scene code dispatch runs later, `level_load("room.wmb")` resolves to `Data\Space\PatHouse\room.wmb`.

---

## 2. Space Switch / Scene Code Dispatch: `FUN_0050a0f0`

```
Address: 0x0050a0f0
Prototype: void FUN_0050a0f0(void)
```

This function consumes a queued scene code from `FUN_0050ffd0` and runs a two-phase switch:

### Phase 1: Level Loading (codes 0-0xc)

| Code | level_load() | Post-load code | Room |
|------|-------------|----------------|------|
| `0` | `room.wmb` | `100` | PatHouse tutorial |
| `1` | `playroom.wmb` | `0x65` | Playroom |
| `2` | `gym.wmb` | `0x66` | Gym |
| `3` | `magic.wmb` | `0x67` | Magic room |
| `4` | `cook.wmb` | `0x68` | Kitchen |
| `5` | `shop.wmb` | `0x69` | Shop |
| `6` | `library_1.wmb` | `0x6a` | Library |
| `8` | `lobby.wmb` | `0x6c` | Lobby |
| `9` | `pet.wmb` | `0x6b` | Pet select |
| `10` | `ground.wmb` | `0x6d` | Ground/outdoor |
| `0xb` | `hansol.wmb` | `0x6e` | Plaza (conditional) |
| `0xc` | `OXQuiz.wmb` | `0x6f` | OX Quiz |

**Case 0 (PatHouse tutorial) special behavior:**
- Sets `gm+0x31792 = 3` (logic state = loading)
- Sets `gm+0x3179a = 1`
- Runs two frame-engine flush cycles before and after `level_load`
- Then queues post-load code `100`

**Case 0xb (Plaza) conditional:**
- Only calls `level_load("hansol.wmb")` if `gm+0x31c71 != 0`
- If `gm+0x31c71 == 0`, re-queues code `0xb` (retries later)
- After loading, clears `gm+0x31c71 = 0`

### Phase 2: Post-Load Bootstrap (codes 100-0x6f)

| Code | Action | logic_state set to |
|------|--------|--------------------|
| `100` | `FUN_0050b400(100)` + tick init | `2` |
| `0x65`-`0x6a` | `FUN_0050b400(code)` | `2` |
| `0x6b` (pet) | `FUN_0050b400(0x6b)` | `0` |
| `0x6c` (lobby) | `FUN_0050b400(0x6c)` | `1` |
| `0x6d` (ground) | `FUN_0050b400(0x6d)` | `2` |
| `0x6e` (plaza) | `FUN_0050b400(0x6e)` | `4` |
| `0x6f` (quiz) | `FUN_0050b400(0x6f)` | `5` |

**Case 100 (PatHouse) is unique:** it additionally calls `FUN_00530330` and `FUN_00557390` with `GetTickCount() / 1000`, initializing time-based gameplay systems.

---

## 3. Transition Branch Selector: `HandleS2C_0007_EmitPostSetupStateRequest` (0x0050D290)

```
Address: 0x0050d290
Prototype: void __fastcall HandleS2C_0007_EmitPostSetupStateRequest(int gm)
```

### Decompiled Logic

```c
void HandleS2C_0007_EmitPostSetupStateRequest(int gm) {
    FUN_005094c0();           // pre-transition cleanup
    FUN_005eab20();           // UI cleanup

    if (*(char*)(gm + 0x31c72) != 0) {
        FUN_0050a7f0(0x6e);   // open loading -> Plaza/hansol
    }
    else if (*(char*)(gm + 0x31c73) != 0) {
        FUN_0050a7f0(0x6f);   // open loading -> OX Quiz
    }
    else {
        FUN_0050b090();        // -> FUN_0050a7f0(100) -> PatHouse tutorial
    }
}
```

### Decision Tree

```
HandleS2C_0007_EmitPostSetupStateRequest (called when S->C 0x0007 arrives via case 7)
  |
  +-- gm+0x31c72 != 0 ?
  |     YES -> FUN_0050a7f0(0x6e)  -> Plaza/hansol.wmb loading
  |
  +-- gm+0x31c73 != 0 ?
  |     YES -> FUN_0050a7f0(0x6f)  -> OX Quiz loading
  |
  +-- default (both zero)
        -> FUN_0050b090()
           -> FUN_0050a7f0(100)    -> PatHouse/room.wmb loading
```

### `FUN_0050a7f0` (Loading Opener)

```c
void FUN_0050a7f0(int gm, uint code) {
    *(uint*)(gm + 0x31aad) = code;  // store scene/load code
    FUN_004ed2a0(code);
    FUN_005ca710(code);              // open loading popup
}
```

Stores the load code in `gm+0x31aad` and opens the loading popup screen.

---

## 4. Flag Analysis: `gm+0x31c72` / `gm+0x31c73`

### Where Flags Are Set

**Initialization (zeroed):**
- `FUN_00507df0`: zeros all three flags (`0x31c71`, `0x31c72`, `0x31c73`) during game manager init
- `FUN_005283e0`: zeros both `0x31c72` and `0x31c73`, loads `BlackPan.tga` transition screen

**`gm+0x31c72` set to 1 (Plaza transition):**

| Function | Context |
|----------|---------|
| `FUN_005ecff0` | Room-door transition; conditional on room data `+0x42` == 3 |
| `FUN_005ee600` | Room-door transition; unconditional within the door handler |
| `FUN_00602830` | Direct Plaza entry; also calls `FUN_0050a7f0(0x6e)` |
| `FUN_00568770` | Direct Plaza entry; also calls `FUN_0050a7f0(0x6e)` |

**`gm+0x31c73` set to 1 (OX Quiz transition):**

| Function | Context |
|----------|---------|
| `FUN_005ee7b0` | Room-door transition; unconditional within the door handler |

### Key Insight

All the setters for `gm+0x31c72 = 1` are **in-game room transition functions** (door handlers, plaza-entry functions). They are NOT called during the initial login/character-creation flow.

For a fresh new character:
- `FUN_00507df0` (init) zeros both flags
- No room-door handler runs before the first `S->C 0x0007`
- Therefore both flags are guaranteed to be `0` at the time `HandleS2C_0007_EmitPostSetupStateRequest` runs
- Result: **default path is `FUN_0050b090()` -> `FUN_0050a7f0(100)` -> PatHouse tutorial**

---

## 5. `gm+0x31c71` (Plaza Level-Load Gate)

This is a separate flag used by `FUN_0050a0f0` case `0xb`:

```c
case 0xb:
    if (gm+0x31c71 == 0) {
        // re-queue code 0xb, try again later
        FUN_0050fe80(0xb, -1, -1);
    } else {
        level_load("hansol.wmb");
        FUN_0050fe80(0x6e, -1, -1);  // queue post-load code
        gm+0x31c71 = 0;              // clear gate
    }
```

**Where `gm+0x31c71` is set to 1:**
- `DispatchState0Common_S2C` case 4: when `payload[0] == 0xFF`, sets `gm+0x31c71 = 1`
  - This is `S->C opcode 4` in the secondary transition handler
  - Meaning: the server signals "character confirmed, Plaza resources ready"

**Where cleared:**
- `FUN_00507df0` (init): zeroed
- `FUN_0050a0f0` case `0xb`: cleared after `level_load("hansol.wmb")` succeeds

This creates a gating mechanism: Plaza's `hansol.wmb` cannot load until the server explicitly confirms readiness via opcode 4 with `payload[0] = 0xFF`.

---

## 6. Call Chain: How 0x0003 Path Reaches level_load

```
S->C 0x0003 packet arrives
  |
  v
FUN_0050d200 (0x0003 handler)
  |-- stores flag byte at gm+0x31c63
  |-- FUN_0050c250(path) -> gm+0x989 = space root buffer
  |-- FUN_005d4070(path) -> strcpy(popup+0xdb, path)
  |                         arms transition screen
  v
(later) S->C 0x0007 packet arrives
  |
  v
DispatchState0Common_S2C case 7
  |
  v
HandleS2C_0007_EmitPostSetupStateRequest (transition branch selector)
  |-- checks gm+0x31c72 (Plaza flag)
  |-- checks gm+0x31c73 (Quiz flag)
  |-- default: FUN_0050b090 -> FUN_0050a7f0(100)
  |
  v
FUN_0050a7f0(100)
  |-- stores code 100 in gm+0x31aad
  |-- opens loading popup via FUN_005ca710
  |
  v
(loading loop) FUN_0050a0f0 consumes queued scene codes
  |
  v
case 0: level_load("room.wmb") -> resolves to Data\Space\{root}\room.wmb
  |-- queues post-load code 100
  |
  v
case 100: FUN_0050b400(100) + time init
  |-- sets logic_state = 2
```

---

## 7. Practical Implications For Server Implementation

### Correct PatHouse Tutorial Entry

To make the client enter the PatHouse tutorial room:

1. **`S->C 0x0003`** payload: `[flag=0x00] + "Data\\Space\\PatHouse\0"`
   - Sets space root to PatHouse directory
   - `room.wmb` will resolve to `Data\Space\PatHouse\room.wmb` (7.1 MB, the real tutorial room)

2. **`S->C 0x0007`** must arrive with:
   - `gm+0x31c72 == 0` (default for new character -- no action needed)
   - `gm+0x31c73 == 0` (default for new character -- no action needed)
   - The transition branch selector will then take the default path to code `100`

3. **Do NOT send** `S->C opcode 4` with `payload[0] = 0xFF` before the first `0x0007`:
   - This sets `gm+0x31c71 = 1`, which is the Plaza level-load gate
   - Not harmful for PatHouse path, but unnecessary and confusing

### Why `Data\Space\Plaza` Is Wrong For First Entry

If `0x0003` sends `Data\Space\Plaza`:
- The transition branch selector still takes the default path (code `100`)
- `level_load("room.wmb")` runs but resolves to `Data\Space\Plaza\room.wmb`
- **There is no `room.wmb` in the Plaza directory** -- only `hansol.wmb` exists there
- This causes a resource mismatch: the loading code expects PatHouse room assets

### When `Data\Space\Plaza` Is Correct

Plaza path is correct ONLY when the client has already been through the tutorial and a room-door/transition function has set `gm+0x31c72 = 1`. In that case:
- Transition branch selector takes the `0x6e` path
- Scene code dispatch runs case `0xb`
- `level_load("hansol.wmb")` resolves to `Data\Space\Plaza\hansol.wmb`
- This is the correct Plaza hub entry

### 0x0003 Flag Byte (`gm+0x31c63`)

The first byte of the 0x0003 payload is stored at `gm+0x31c63`. Its exact meaning is not yet fully traced, but:
- It is stored as a `uint` (4-byte write, only bottom byte meaningful)
- Current safe value: `0x00`
- No branch logic has been found that reads this flag in the early loading path

---

## 8. Complete Scene Code Map

### Level-Load Phase (input codes)

| Code | WMB File | Post-load Code | Space Root |
|------|----------|----------------|------------|
| `0` | room.wmb | `100` | PatHouse |
| `1` | playroom.wmb | `0x65` | PatHouse |
| `2` | gym.wmb | `0x66` | PatHouse |
| `3` | magic.wmb | `0x67` | PatHouse |
| `4` | cook.wmb | `0x68` | PatHouse |
| `5` | shop.wmb | `0x69` | PatHouse |
| `6` | library_1.wmb | `0x6a` | PatHouse |
| `8` | lobby.wmb | `0x6c` | lobby |
| `9` | pet.wmb | `0x6b` | SelectPet |
| `10` | ground.wmb | `0x6d` | (unknown) |
| `0xb` | hansol.wmb | `0x6e` | Plaza |
| `0xc` | OXQuiz.wmb | `0x6f` | (unknown) |

### Post-Load Phase (logic_state outcomes)

| Post-load Code | logic_state | Meaning |
|----------------|-------------|---------|
| `100` | `2` | Normal gameplay (PatHouse tutorial) |
| `0x65`-`0x6a` | `2` | Normal gameplay (sub-rooms) |
| `0x6b` | `0` | Pet select screen |
| `0x6c` | `1` | Lobby state |
| `0x6d` | `2` | Normal gameplay (outdoor) |
| `0x6e` | `4` | Plaza state |
| `0x6f` | `5` | Quiz state |

---

## 9. Recommended Server Packet Sequence Change

**Current (incorrect):**
```
S->C 0x0003: [0x00] "Data\Space\Plaza"
```

**Correct for tutorial entry:**
```
S->C 0x0003: [0x00] "Data\Space\PatHouse"
```

No other packet changes are needed for the path selection itself. The transition branch selector defaults to code `100` (PatHouse) for new characters because both `gm+0x31c72` and `gm+0x31c73` are zero at init time.

The key constraint is that `S->C 0x0003` must be sent BEFORE `S->C 0x0007`, because `0x0007`'s secondary handler triggers `HandleS2C_0007_EmitPostSetupStateRequest` which opens the loading path that will later call `level_load("room.wmb")` against the space root set by `0x0003`.
