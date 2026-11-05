# Shipped-content profile: dynamic A/B verification

Date: 2026-07-17

This note records a read-only runtime comparison of the native, unpatched
`Nexus=40` client before and after the recovered `S2C 0x0007` character-state
profile and `S2C 0x000A` item-domain registry are corrected.  The test keeps
the bootstrap evolution selector at stage `0`; it deliberately does not mix
the separate evolution-1 / E1201 problem into the content-state experiment.

## 1. Pre-change control

The control is the clean PatHouse run captured in
`captures/packets_20260717_171158.txt`.

Runtime state at the observation point:

| Signal | Control value |
|---|---|
| process | `Azrok.exe`, PID `118740`, `Responding=True` |
| scene / phase | `100 / 2` (PatHouse ready) |
| dispatch mode | `0` (state-0 local room) |
| Nexus | `40` (native, no binary patch) |
| bootstrap evolution | `S2C 0007[2] = 0` |
| transport liveness | `C2S 0016[00] -> S2C 0016[00]` every 10 seconds |
| first periodic property snapshot | one `C2S 0007`, 196 bytes |

The corresponding client-area screenshot is
`artifacts/dynamic-analysis/content_profile_stage0_baseline_20260717_1720.bmp`.
Its visible state is:

- portrait name `블루론`, badge `01`;
- top HUD name field blank and money `소지금 0`;
- EXP nearly empty; hunger/hygiene/energy/fun about half and stress low;
- three visible quest slots, all blank;
- three room-floor labels reading `이름:` with no name, `레벨: 0`, and
  `단계: 블루론`;
- no inventory window is open, so packet fields below are the authoritative
  non-invasive inventory control.

### 1.1 Control packet fields

`S2C 0007` is 472 bytes, SHA-256
`646d15e4166484fa3dbae6be56e355eb70df047e0453fce492b541b6acfa2737`.
The generated date word is expected to vary across launches; the functional
fields are:

```text
header [status, species, bootstrap evolution] = [0, 2, 0]
stats[0..9] = [0, 1, 0, 50, 50, 50, 50, 10, 50, 100]
stats[25..56] = all zero
inventory domains = furniture/drug/energy/food/ingredient/toy/gym/book all zero
immediate local-effect codes = FF * 11
quest ids = 00FF * 10
quest progress = 00FF * 10
quest values = 0 * 10
mode kinds = FF * 8
mode values = 0 * 8
```

`S2C 000A` is 150 bytes, SHA-256
`f4437e504b0f6b406252bd2d62e6c116838630b848438e782b82b321e2227544`.
It is the old diagnostic/custom item-domain table.  The mismatching groups are:

```text
Toy        = [500, 600, 500, 600, 500, 600]
Food       = [500, 0, 500, 500, 80, 500, ... 30/70/110 ..., 1, 2]
Ingredient = [80, 80, 0]
```

The first `C2S 0007` property snapshot is 196 bytes.  It contains:

```text
stats[0..9] = [0, 1, 0, 40, 45, 40, 50, 30, 55, 100]
selected content stats 25..33, 55, 56 = zero except stat 25 = 1
mode bytes = 00 00 00 00 00 02 02 02
```

The client changing the live gauges between `S2C` load and `C2S` save is
expected and proves that `C2S 0007` is a live periodic property snapshot, not
a byte-for-byte ACK.

## 2. Expected post-change checklist

The repaired shipped/demo profile must satisfy all of the following in one
clean restart:

1. **No bootstrap regression**
   - no `Error E1201` or startup-failure dialog;
   - `Nexus=40`, `S2C 0007[2]=0`;
   - client reaches `scene=100 / phase=2` and remains `Responding=True`.
2. **Transport remains live**
   - capture file continues to advance;
   - at least three consecutive 10-second `0016[00]` heartbeat round trips.
3. **Correct shipped stat alignment**
   - `S2C 0007` stats use `IQ + init.csv[0..24] + meal-counter +
     init.csv[25..54]`;
   - checkpoints: level index 1=`25`, EXP index 2=`33000`, meal counter index
     26=`0`, dumbbell EXP index 32=`500`, pet-evolution stat index 55=`1`,
     pet/species stat index 56=`2`;
   - indices `57..69` remain zero;
   - header evolution byte remains `0` even though stat 55 is `1`.
4. **Visible state changes without E1201**
   - level/EXP and the five status gauges visibly differ from the minimal
     profile in the direction implied by the shipped values;
   - room-floor name labels are recorded but are not claimed as fixed by
     `0007/000A`, because their source is still unresolved.
5. **No inventory contamination**
   - all eight `S2C 0007` inventory quantity arrays remain exactly zero;
   - quest rows stay empty sentinels unless an explicit diagnostic seed was
     intentionally enabled;
   - no bytes from the 196-byte `C2S 0007` prefix appear in furniture/drug
     quantities after later saves or reconnects.
6. **Correct `S2C 000A` registry**
   - exactly 75 `u16` / 150 bytes;
   - byte-identical to the client binary-default item-domain values;
   - Toy `[200,500]` pairs, Food `30/40/100/200/300` tiers, Ingredient
     `[100,200,300]`.
7. **Periodic persistence boundary remains valid**
   - a 196-byte `C2S 0007` arrives after load and again on the periodic/forced
     save boundary when observed long enough;
   - it is decoded as a general property snapshot;
   - its 70 stats can be mapped to the next `S2C 0007` without copying its
     unrelated tail into inventory fields.

## 3. Post-change observation

The repaired server was started through the existing elevated scheduled task;
the old client and server were stopped first.  There was no saved-state file
in `server_state/`, so this run is a clean shipped-profile observation rather
than a restore of the old minimal snapshot.

Evidence:

- capture: `captures/packets_20260717_172301.txt`;
- process: PID `98368`;
- final client screenshot:
  `artifacts/dynamic-analysis/content_profile_shipped_live_20260717_1725.bmp`;
- transient character-selection screenshot:
  `artifacts/dynamic-analysis/content_profile_postrestart_scene107_20260717_1724.bmp`.

The client first stayed at `scene=107 / phase=0` while the normal eight
pre-create heartbeat samples completed.  It then entered PatHouse without
manual packet injection.  At `17:28:52`, more than four minutes after server
start, it was still:

```text
Responding=True
scene=100 / phase=2
Nexus=40
configured/header evolution=0
last opcode=0x0016
capture last write=17:28:47
E1201/startup-failure top-level windows=0
```

There are many consecutive heartbeat pairs at exactly the expected interval,
including `17:26:37`, `17:26:47`, `17:26:57`, and `17:27:07`.  The shipped
profile therefore does not reproduce the evolution-1 bootstrap hang.

### 3.1 Packet A/B result

The new `S2C 0007` is 472 bytes, SHA-256
`2127799caff9663217a049f725de5a96e6474d589a3ff083cdb044936076694a`.
The hash includes the generated date; field comparisons are authoritative:

```text
header [status, species, bootstrap evolution] = [0, 2, 0]
stats[0..9] = [0, 25, 33000, 10, 80, 80, 80, 30, 80, 50]
stat 25 cleaning counter       = 500
stat 26 meal counter           = 0
stat 27 toileting counter      = 500
stat 28 bath counter           = 500
stat 32 dumbbell EXP           = 500
stat 55 pet-evolution property = 1
stat 56 pet/species property   = 2
stats 57..69                   = 0
inventory nonzero counts       = [0,0,0,0,0,0,0,0]
quest IDs/progress             = 00FF * 10 / 00FF * 10
```

The inventory result is especially important: the server built this payload
from a fresh buffer, and no byte from the directional 196-byte request appeared
in furniture or drug quantities.

The new `S2C 000A` is exactly 150 bytes, SHA-256
`e6cce93cbf66353f4f26973c34964d2e683c887e83296164ee3ed5e5cee467cd`.
Direct group checks are:

```text
Toy        = [200,500,200,500,200,500]
Gym        = [200,500,200,500,200]
Food       = [30,30,30,40,40,100...,200...,300...]
Ingredient = [100,200,300]
```

### 3.2 Visible effect

The screen changed materially while the bootstrap selector stayed at stage 0:

- the badge is now `26` rather than the control's `01`;
- the EXP bar is full and the status bars reflect the shipped values after
  client-side normalization;
- the client displays the growth guidance that the current BlueRon must grow
  into RedRon before leaving the house;
- money remains `0`, the three floor labels still have blank names/level 0,
  and the quest panel is not populated.  These are separate unresolved data
  sources and were not falsely claimed as repaired by `0007/000A`;
- no inventory was granted, matching all-zero packet quantities.

The badge becoming 26 rather than 25 is not a wire mismatch: the server sent
level 25 plus EXP 33000 and the client immediately normalized the live level
against the supplied XP curve.

### 3.3 Client normalization reports and the 196-byte snapshot

Immediately after applying the new state, the client emitted 23
`C2S 0017` reports.  Their proven six-byte shape is
`<kind=07, stat_id, u32 value>`.  Examples include:

```text
stat 0x20 (dumbbell EXP) = 500
stat 0x37                = 1
stat 0x38                = 2
```

At `17:24:35.805`, 8.284 seconds after the `S2C 0007` at
`17:24:27.521`, the client sent one 196-byte `C2S 0007` property snapshot,
SHA-256
`f53b22361315c5b6d7f684b061505fd6774417b3a36a149e688a20812dc5c822`.
It proves the periodic/live snapshot path still runs.  Selected returned
values are:

```text
level=26, EXP=33000
stat 25=400, 27=400, 28=400       (client-schema clamps)
stat 31=400, stat 32=450
stats 33 and 37..39=450
snapshot sum=5040
```

One important asymmetry remains: this snapshot carries stat 55/56 as zero,
even though the adjacent `C2S 0017` reports explicitly carry stat IDs 55/56 as
`1/2`.  This is direct runtime evidence, but it does not by itself identify
whether those fields are intentionally outside the periodic snapshot's saved
property subset or whether the current C2S field map is incomplete.  The
server must not silently use the all-70 snapshot restore to erase the shipped
growth/species properties until that distinction is resolved.

The observed snapshot was `client_0007_count=1`, so the current server treated
it as the bootstrap-side request and did not increment `content_save_count`.
A later forced/periodic snapshot would enter the persistence branch.  This
means the packet path is live, but persistence of every one of the 70 words is
not yet proven safe.

## 4. Verdict

| Check | Result | Direct evidence |
|---|---|---|
| E1201 absent at native Nexus 40 | PASS | phase 2 for >4 min, no error window |
| heartbeat/capture liveness | PASS | uninterrupted 10-second `0016` pairs |
| shipped stat wire alignment | PASS | indices 1/2/26/32/55/56 decoded above |
| visible level/status change | PASS | final client screenshot, badge 26 |
| inventory remains ungranted/unpolluted | PASS | all eight quantity arrays zero |
| quests remain explicit empty sentinel | PASS | IDs/progress `00FF * 10` |
| `000A` binary item registry | PASS | 150 bytes, SHA and group checks above |
| 196-byte C2S property snapshot still emitted | PASS | packet at 17:24:35.805 |
| blind all-70 persisted restore is safe | **NOT PROVEN** | stat 55/56 asymmetry |

The P0 shipped-content profile is dynamically compatible with the unpatched
client and is a clear improvement over the sparse control.  The next dynamic
contract to resolve is how `C2S 0017` deltas and `C2S 0007` snapshots jointly
represent fields that do not round-trip in the snapshot, before reconnect
persistence is allowed to overwrite the shipped defaults.

## 5. Superseded persistence warning

The stat-55/56 authority question above was resolved later the same day.
The server now merges the verified `C2S 0x0017` values for exactly those two
fields before atomically persisting a periodic `C2S 0x0007` snapshot.  A clean
server/client restart restored `1/2` in the next real `S2C 0x0007` while the
independent model selector remained zero and PatHouse stayed stable at native
`Nexus=40`.  See `59_stat55_56_authority_persistence_20260717.md` for the
implementation and wire proof.  The `NOT PROVEN` verdict in section 4 is the
historical pre-fix result, not the current server state.
