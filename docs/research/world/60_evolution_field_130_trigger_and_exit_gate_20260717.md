# Pet evolution field +0x130, its trigger, and the exit gate (2026-07-17)

> **SUPERSEDED by 61 and 62 in sections 3, 4, and the old verification list.**
> Sections 1 and 2 remain the static authority for the field and trigger.

> **VISIBLE-ASSET CORRECTION by 73 (supersedes 63):** `mirror_01` is the
> PatHouse wardrobe/mirror record. `dm_door_0003_057` is the bathroom/internal
> door. The strongest far-left outside candidate is `gate_mun_MDL_048` with
> `doorframe_01`; exact visible/action-descriptor binding remains unverified.

> **2026-07-17 20:34 dynamic correction:** Sections 1 and 2 correctly identify
> the field and the natural care-action trigger, but section 3's timing-based
> E1201 explanation is disproven.  A clean native-`Nexus=40` PatHouse client
> loaded the blob with byte 2 equal to zero, then naturally evolved through
> the sleep action.  The client visibly changed BlueRon to RedRon and persisted
> evolution value 1, but then opened a separate `Error E1201` dialog whose body
> was `Nexus too small! (3)`.  Therefore post-load natural promotion is real but
> is **not sufficient to avoid E1201**.  See note 61; the exact allocator caller
> is now the active question.

Parallel static trace (Ghidra, `Azrok_original.exe`) of what makes the pet evolve
(BlueRon → RedRon) and what gates leaving the house. Cross-checked against the live
A/B result in note 58. No binary patch. VERIFIED = seen in a decompiled body;
INFERRED = reasoned; NOT VERIFIED = needs dynamic confirmation.

## Headline correction

**Evolution is NOT stat 55.** It is a value 0/1/2/3 stored at **logic-object `+0x130`**.
stat 55 is only one summed INPUT to the tier calc, not the evolution store. This
overturns the earlier "evolution = stat 55" assumption (which note 58 already hinted at:
A/B had stat 55=1 yet the pet stayed BlueRon and could not leave).

## 1. The master gate — `+0x130` (VERIFIED)

`FUN_005a4df0` @ `0x005A4DF0` (content/display tier recalc) opens with:
```
if (FUN_005465c0() == 0) return 0;   // FUN_005465c0 reads +0x130
```
So **`+0x130 != 0` is the master gate for ALL evolution/tier content** — regardless of
level. Above it, tier2 rechecks level>10/care>150, tier3 level>20/care>300.

**Cross-check with live A/B (note 58):** the shipped profile had level 26 and stat 55=1
but header evolution byte = 0 → `+0x130 = 0` → master gate closed → pet stayed BlueRon,
exit stayed shut. This is exactly why leveling to 26 did not open the house. VERIFIED by
two independent sources (static gate + live A/B).

## 2. Evolution trigger — EXP/level thresholds, re-evaluated per care action (VERIFIED)

There is **no dedicated "evolve" button**. Evolution is a side effect of care/feed actions:

```
care/feed action  -> FUN_00596690 @0x00596690
   -> applies stat delta (EXP=stat2, etc.)
   -> FUN_005a6910(3,0,0)            // kind==3 path = evolution check
        -> scans the 10 runtime-rows at +0x70c; on row.kind==3:
        -> FUN_005a8070 @0x005a8070  // threshold evaluator, returns target stage
        -> FUN_005a7e40 @0x005a7e40  // writes +0x130 via ProtocolState_SetField130Value @0x00599150
             stage 0   -> +0x130 = 1   (first evolution, BlueRon->RedRon)
             stage 1-3 -> +0x130 = 2
             stage 4-6 -> +0x130 = 3
   -> FUN_005a51a0(EXP)  // level is DERIVED from EXP via bracket table DAT_006e0a88 (30 steps)
```

Thresholds in `FUN_005a8070`:
- stage 0: `EXP(stat2) > 349`
- stage 1-3: `level(stat1) > 11` AND `sum(stat30..65) > 999` AND bucket requirements
- stage 4-6: `level > 24` AND `sum > 3999` AND bucket requirements

**A `kind==3` runtime-row MUST exist** for evolution to fire. That row comes from the
0x0007 blob row table (offset `0x134` = kind, `0x148` = aux/target-stage) via
`RuntimeRowTable_ImportFrom0007`. This ties directly to note 58's quest-row finding: the
same 0x134 rows also drive evolution when kind==3.

Shipped profile (level 25, EXP 33000) with a kind==3 row (aux 4-6) and sum>3999 would
evaluate to `+0x130 = 3` (fully evolved) — well past the exit requirement.

## 3. E1201 timing hypothesis — SUPERSEDED by 61 and 62

The load ordering above is real and bootstrap evolution remains zero, but it is
not the E1201 root cause. Note 61 reproduced E1201 after a fully post-load,
client-owned evolution. Note 62 proves `(3)` is a failed allocation size in
KiB and that the same natural flow succeeds with the engine's native `-NX200`.

## 4. Exit / leaving the house — live correction in note 62

- **VERIFIED**: room transition runs `Plaza_TransitionFromRoom` @ `0x00568770` (enqueues
  room code 0x6e). Server drives it: `DispatchState0Common_S2C` @0x0050CBC0 case 0xD does
  `if (payload[0]==0) Plaza_TransitionFromRoom();`. So **S→C 0x000D (payload[0]=0) is the
  server "leave now" command** — matches the long-suspected 0x000D transition.
- **VERIFIED (note 54 static + note 62 live):** `ProtocolState+0x130 != 0`
  enables the PatHouse outside action. A manual door click then naturally emits
  `C→S 0x0019[00]`.
- **VERIFIED:** the server responds with `S→C 0x000D[00]`; the request-driven
  five-sample calibration and 0064-only reply produce Plaza.
- **INFERRED:** `mirror_01` is the exact asset behind the visibly clicked door;
  the mesh-name binding itself still lacks a dynamic entity trace.

## 5. Actionable conclusions

To evolve the pet and open exit content, client `logic+0x130` must become >= 1. Two paths:

- **Server re-implementation (zero client patch):** deliver, in 0x0007, threshold-meeting
  stats (level 25 / EXP 33000 / care sum) AND a `kind==3` runtime-row (aux = target stage),
  with `byte[2]=0`; then after load, let a care-type event flow so the CLIENT raises its own
  +0x130. Leaving is then a server `S→C 0x000D (payload[0]=0)`.
- **frida (runtime test harness):** after 0x0007 load, write `state+0x130 = 3` directly, or
  call `FUN_005a7e40(4)`.

## Remaining verification

- **VERIFIED:** post-load natural `+0x130: 0→1`, RedRon render/save, and natural
  `C→S 0x0019` through the visible outside interaction (62).
- **INFERRED:** exact visible mesh ↔ `mirror_01` descriptor binding.
- **NOT VERIFIED:** what in-game care actions raise each `sum(stat30..65)`
  bucket and how the higher-stage bucket requirements behave dynamically.

Related: [[project-multiplayer-milestone]], note 57 (E1201 A/B), note 58 (shipped profile
+ quest rows at 0x134), note 59 (stat 55/56 persistence).
