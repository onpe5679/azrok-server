# Content-state contract audit: `S2C 0007/000A/000B` and persisted `C2S 0007`

Date: 2026-07-17

This began as a read-only audit of the then-current server builders against the
original client, current captures, `init.csv`, and `lgc.tmp`.  The P0 defects
identified here were implemented later on the same date; the implementation
status below supersedes present-tense descriptions in the audit baseline.  It
still deliberately separates a recovered wire layout from an unproven
original-account seed: a structurally valid item or quest ID is not, by itself,
proof that the original server granted it to a new character.

The primary binary used for the static checks was `Azrok_original.exe` in the
live Ghidra project.  The important functions are:

- `HandleS2C_0007_LoadSetupBlob @ 0x0059E330`
- `KeyedByteList_Import @ 0x0059BC00`
- `HandleS2C_000A_StatRegistry @ 0x0059ECA0`
- `StatRegistry_WriteGroupedKeyValue @ 0x005AA090`
- `HandleS2C_000B_XPCurve @ 0x0059EEE0`
- `FUN_005A4770`, the 196-byte `C2S 0x0007` snapshot copier/sender
- `FUN_0059DA00`, the periodic `C2S 0x0007` sender

## Implementation status: P0 applied on 2026-07-17

Implemented in `azrok_server.py`:

- `S2C 0x0007` now starts from a fresh 472-byte buffer.  The directional
  `C2S 0x0007` prefix is never copied.  Only the independently proven persisted
  stat and tuple mappings are overlaid.
- `AZROK_CONTENT_PROFILE=shipped` is the supported default.  It reads the 55
  current values from the installed CP949 `init.csv`, inserts `IQ` at index 0
  and the `lgc.tmp`-only meal counter at index 26, and leaves 57..69 zero.
  `AZROK_CONTENT_PROFILE=minimal` retains the old sparse profile solely for
  diagnostics.
- Corrected anchors are `idx26=meal counter`, `idx32=dumbbell experience`,
  `idx55=pet evolution`, and `idx56=pet`.
- `S2C 0x0007[2]` remains controlled only by `AZROK_EVOLUTION` (supported
  default 0).  The shipped value `stat[55]=1` does not change that header byte.
- `S2C 0x000A` is emitted by `_build_item_registry_000A_draft()` as the exact
  75-u16 client-binary item-domain table by default.  The historical guessed
  table requires `AZROK_000A_PROFILE=custom`; the high-value mutation remains
  a separate explicit diagnostic switch.
- `S2C 0x000B`, all eight zero inventory domains, and the ten `0x00FF` quest
  rows are unchanged because no starter grant/assignment evidence exists.

Verification command:

```powershell
python -m unittest tools.test_content_builders -v
python -m py_compile azrok_server.py tools/test_content_builders.py
```

The isolated suite has eight passing tests covering exact lengths, corrected
stat offsets, header-evolution independence, zero inventory/no C2S-tail leak,
empty quest sentinels, the exact 75-value `0x000A` table, and unchanged
`0x000B` XP values.

### Live A/B result

The clean live run also passed:

- capture: `captures/packets_20260717_172301.txt` (PID 98368);
- screenshot:
  `artifacts/dynamic-analysis/content_profile_shipped_live_20260717_1725.bmp`;
- native `Nexus=40`, `S2C 0007[2]=0`, scene 100, phase 2, Responding, and
  heartbeats continued beyond the ten-second boundary with no E1201;
- received stats included `idx1=25`, `idx2=33000`, `idx26=0`, `idx32=500`,
  `idx55=1`, and `idx56=2`;
- all eight inventory domains remained zero and all quest IDs remained
  `0x00FF`;
- `S2C 0x000A` SHA-256 became
  `e6cce93cbf66353f4f26973c34964d2e683c887e83296164ee3ed5e5cee467cd`,
  matching the isolated exact-binary builder;
- the visible UI changed to level 26 with a full EXP display and changed status
  bars, proving the new packet was consumed rather than merely emitted.

One new authority-boundary risk was exposed but is not folded into this P0:
the client sent 23 `C2S 0x0017` clamp/report packets, then a 196-byte
`C2S 0x0007` after about 8.25 seconds.  That snapshot contained `idx1=26`,
`idx25=400`, `idx27/28=400`, `idx31=400`, and `idx32=450`, but it held
`idx55=0` and `idx56=0` even though separate `C2S 0x0017` reports carried
stat 55 = 1 and stat 56 = 2.  This first snapshot was classified as bootstrap
(`client_0007_count=1`) and was not saved.  If an identical later snapshot is
persisted, the current all-70 restore overlay could erase the separately
reported 55/56 values.  Resolve per-field authority/persistence using the
observed `0x0017` reports before changing that overlay; do not guess an ACK.

## Headline findings from the pre-P0 baseline

1. The empty bag is directly explained: every inventory-count byte in the
   current `S2C 0x0007` is zero.
2. The empty quest panel is directly explained: all ten quest row IDs at
   `S2C 0x0007 +0x134` are `0x00FF`, the empty sentinel.
3. The sparse level/progression state is directly explained: the builder
   defines a shipped-data candidate but ignores it and sends only nine sparse
   `MINIMAL_STATS` entries.
4. That unused candidate is itself misaligned after stat index 25.  The
   `lgc.tmp`-only meal counter belongs at index 26, not at index 56.
5. The current builder blindly copies the directional `C2S 0x0007` payload
   into the beginning of `S2C 0x0007`.  The two layouts are different.  In the
   non-zero request path, C2S checksum/mode/timestamp bytes become fake
   furniture and drug quantities.
6. `S2C 0x000A` is not a second character-stat array.  Its keys are the same
   item domains used by the eight inventories.  The values form an item-domain
   numeric/economic registry; their exact consumer is not yet directly traced.
   The server's default custom table nevertheless mixes `init.csv` progression
   values into this unrelated registry.
7. `S2C 0x000A` contains 75 `u16`, not 70.  The seven counts are
   `22+6+5+32+3+1+6 = 75` (`150` bytes).
8. `S2C 0x000B` is already the correct 31-entry XP curve.  It cannot populate
   inventory, quests, or names.
9. `C2S 0x0007` is a general periodic character-property snapshot, not a
   Gym-only completion ACK.  It preserves stats and eight mode/value pairs,
   but carries no inventory arrays or quest rows.
10. The self display name is not in `0007/000A/000B`; it remains a separate
    client-local name-entry problem.  Remote names remain `S2C 0x0066 +7`.

## 1. `S2C 0x0007`: field-by-field audit

The server emits 472 bytes.  This is the exact amount consumed by the client;
shortening it is not a safe fix.

> **SUPERSEDED by 113 (`+0x1AC` row only).** Domain-bank zero is not merely structurally accepted: the full-bank consumer treats every value except `0xFF` as live. Fresh wire state must use `0xFF * 40`; the client then overwrites its 16 fixed entries.

| Offset | Size | Direct client meaning | Current server value/source | Audit |
|---:|---:|---|---|---|
| `0x00` | 1 | setup status | `0` | structurally valid |
| `0x01` | 1 | species/model selector | configured species | valid independent field |
| `0x02` | 1 | bootstrap evolution/model stage | configured evolution, now default `0` | keep separate from stats; see E1201 section |
| `0x03` | 4 | packed date/time | generated valid value | valid |
| `0x07` | 4 | setup/state dword | copied selectively from request | retain only if its directional meaning is proven |
| `0x0B` | `70*2` | indexed character stats | sparse `MINIMAL_STATS` | primary progression defect |
| `0x97` | 33 | furniture quantities | zero, or accidentally copied C2S tail | empty/corrupt bag |
| `0xB8` | 15 | drug container; first 6 IDs are live | zero, or accidentally copied C2S tail | empty/corrupt bag |
| `0xC7` | 20 | energy-item container; first 3 IDs are live | zero | empty bag |
| `0xEA` | 38 | refrigerator food container; first 33 IDs are live | zero | empty refrigerator |
| `0x110` | 3 | ingredient quantities | zero | empty ingredients |
| `0x113` | 10 | toy quantities | zero | empty toy box |
| `0x11D` | 8 | Gym-item quantities | zero | empty Gym inventory |
| `0x125` | 11 | immediate local domain/effect codes | `0xFF` sentinel | correct safe no-op; zero is live and must not be used as empty |
| `0x131` | 1 | book quantity | zero | empty book case |
| `0x134` | `10*2` | quest/runtime row IDs | ten `0x00FF` | direct cause of empty quest slots |
| `0x148` | `10*2` | quest/runtime row auxiliary/progress | ten `0x00FF` | empty rows |
| `0x15C` | `10*4` | quest/runtime row value | zero | empty rows |
| `0x184` | 8 | mode-pair kinds | eight `0xFF` | safe empty sentinel |
| `0x18C` | `8*4` | mode-pair values | zero | coherent with empty kinds |
| `0x1AC` | `4*10` | four domain banks | zero | structurally accepted, semantics still unresolved |
| `0x1D4` | 4 | domain selector vector | four `0xFF` | correct explicit clear/sentinel |

### 1.1 The eight byte lists are inventories, not opaque padding

`CJSInventory` construction at `FUN_00599260`, item-domain setup at
`FUN_00599460`, `DomainCode_ClassifyBucket @ 0x0059A460`, and the UI resource
loader `FUN_005C4570` give the complete mapping:

| S2C offset | CJS object | Imported capacity | Live item IDs | UI/resource meaning |
|---:|---:|---:|---|---|
| `0x97` | `this+0x334` | 33 | `0..32` | Furniture |
| `0xB8` | `this+0x382` | 15 | `4000..4005` | Drug |
| `0xC7` | `this+0x3AB` | 20 | `5000..5002` | Energy selection/items |
| `0xEA` | `this+0x44F` (`CJSRefrigerator`) | 38 | `1000..1032` | Food |
| `0x110` | `this+0x478` | 3 | `1500..1502` | Ingredient |
| `0x113` | `this+0x3D4` | 10 | `2000..2009` | Toy |
| `0x11D` | `this+0x426` | 8 | `2500..2507` | Gym |
| `0x131` | `this+0x3FD` | 1 | `3000` | Book |

`KeyedByteList_Import` widens each non-zero byte into the positional `u32`
quantity slot and adds it to the container total.  A zero byte is empty.
These bytes are quantities, not item IDs; the item ID is determined by the
position and the configured base/domain.

The local resources independently match the live counts:

- `Data/Inventory/Furniture/MyBag_Item0..32.wis`
- `Data/Inventory/Food/Refri_0..32.wis`
- `Data/Inventory/Ingredient/Refri_Material0..2.wis`
- `Data/Inventory/Toy/ToyBox_0..9.wis`
- `Data/Inventory/Gym/Gym_0..7.wis` (the directory also contains an extra
  `Gym_8.wis`, but the live registry/domain has eight IDs)
- `Data/Inventory/Book/Book0.wis`
- `Data/Inventory/Etc/Drug_0..5.wis`
- `Data/Inventory/Etc/MyBag_EnergySelect0..2.wis`

This proves why all-zero lists render an empty bag.  It does **not** prove the
original new-character ownership quantities.  No original-server `S2C 0007`
capture in this workspace contains a starter inventory.

### 1.2 Directional-copy bug

The current builder begins with:

```python
payload[:min(len(client_payload), len(payload))] = client_payload[:min(len(client_payload), len(payload))]
```

That is not a preservation operation.  It copies a 196-byte C2S structure
into a different 472-byte S2C structure.

The verified C2S snapshot stores its 70 stats at `+0x0A`, followed by a sum
and mode/value/timestamp tail.  The S2C structure stores stats at `+0x0B` and
begins furniture quantities at `+0x97`.  The builder overwrites the stat area
later, but it leaves the collision at `S2C +0x97..+0xC3` intact.  Consequently:

- C2S sum/mode/value bytes can become furniture quantities;
- the final C2S dwords can become the first 12 bytes of the drug container;
- proactive calls that pass 196 zero bytes hide the defect, while a natural
  non-zero first C2S request can expose it.

The correct contract is a fresh zeroed S2C buffer plus explicit mappings for
proven equivalent fields.  Do not mirror the directional packet wholesale.

### 1.3 Stats: the current list is sparse, and the unused full list is shifted

The runtime loop uses only:

```text
idx 1=1, 3=50, 4=50, 5=50, 6=50, 7=10, 8=50, 9=100
all other indices = 0
```

This makes level 1, EXP 0, every local-room experience gate 0, and most
progression/counter fields 0.  It is sufficient to draw a room, not to restore
the content state.

The source also defines `INIT_CSV_STATS`, but never uses it.  Its intended
construction is `IQ + init.csv + meal-counter`, yet it appends the missing
meal counter at the end.  `lgc.tmp` and the stat-index consumers show that the
meal counter belongs at index 26.  This is the corrected 0..56 alignment:

| Indices | Correct shipped-data candidate |
|---|---|
| `0` | IQ `0` (`lgc.tmp` only) |
| `1..25` | `init.csv` rows `0..24` |
| `26` | meal counter `0` (`lgc.tmp` only) |
| `27..56` | `init.csv` rows `25..54` |
| `57..69` | zero until a schema/source is proven |

Selected direct checkpoints are:

| Index | Meaning | Candidate current | Schema max |
|---:|---|---:|---:|
| `1` | level | 25 | 30 |
| `2` | EXP | 33000 | 60000 |
| `3` | hunger | 10 | 100 |
| `4` | hygiene | 80 | 100 |
| `5` | energy | 80 | 100 |
| `6` | fun | 80 | 100 |
| `7` | stress | 30 | 100 |
| `8` | toileting | 80 | 100 |
| `9` | bond energy | 50 | 300 |
| `25` | cleaning counter | 500, clamped by schema | 400 |
| `26` | meal counter | 0 | 400 |
| `27` | toileting counter | 500, clamped | 400 |
| `28` | bath counter | 500, clamped | 400 |
| `29` | instant-food stat | 80 | 100 |
| `30` | knowledge EXP | 500 | 450/600 depending verified schema source |
| `31` | push-up EXP | 500 | 400 |
| `32` | dumbbell EXP | 500 | 450 |
| `33` | rope-skipping EXP | 500 | 450 |
| `37..39` | magic-clone/funny-shield/air-hook EXP | 500 each | 450 each |
| `40..44` | low-tier cooking EXP | 30 each | 40 each |
| `45..49` | mid-tier cooking EXP | 70 each | 80 each |
| `50..54` | high-tier cooking EXP | 110 each | 120 each |
| `55` | pet evolution stat | 1 | 4 |
| `56` | pet/species stat | 2 | 3 |

The Gym trace is an independent alignment check: the dumbbell path uses stat
index `0x20` (32), exactly where `lgc.tmp` places `아령경험`.  The current
unused list places that value at 31 because of the missing index-26 insertion.

`init.csv` is a shipped high-progress/demo candidate, not proof of the
original new-account defaults.  `lgc.tmp` is authoritative for row ordering
and bounds but all of its current values are zero; it is not a playable saved
character.  A sensible implementation should name the `init.csv` state as an
opt-in shipped/demo seed until original-server account data is found.

### 1.4 Quest rows

The quest list is not in `0x000A` or `0x000B`.  `CJSQuestList` construction
and `HandleS2C_0007_LoadSetupBlob` place ten 12-byte rows at `this+0x70C`:

```text
id       = u16(payload + 0x134 + i*2)
progress = u16(payload + 0x148 + i*2)
value    = u32(payload + 0x15C + i*4)
```

The handler accepts IDs `0..5` or `0xFF`; `0xFF` is empty.  Current captures,
including `captures/packets_20260717_140843.txt`, contain ten `0x00FF` IDs,
so an empty panel is the expected rendering of the data sent by the server.

There is no original quest assignment in the captures, `init.csv`, or
`lgc.tmp`.  IDs `0..5` prove the valid catalog selector range, not which quest
must be active.  A one-row seed can be useful as an explicitly labelled
diagnostic, but must not be promoted to the recovered default without an
acquisition/completion trace.

## 2. `S2C 0x000A`: item-keyed numeric registry, not character status

The handler consumes exactly 75 `u16` values:

| Group | Offset | Count | Baked keys | Inventory domain |
|---:|---:|---:|---|---|
| 0 | `0x00` | 22 | `1,2,4,5,...,31,32` | Furniture `0..32` |
| 1 | `0x2C` | 6 | `2002,2003,2005,2006,2008,2009` | Toy `2000..2009` |
| 2 | `0x38` | 5 | `2501,2502,2504,2505,2507` | Gym `2500..2507` |
| 3 | `0x42` | 32 | `1001..1032` | Food `1000..1032` |
| 4 | `0x82` | 3 | `1500..1502` | Ingredient |
| 5 | `0x88` | 1 | `3000` | Book |
| 6 | `0x8A` | 6 | `4000..4005` | Drug |

The domain identity is exact, not inferred from approximate values.  The
client's baked `[item_id,value]` registries contain:

```text
Furniture: repeating base 0, then 1000, 2000
Toy:       repeating base 0, then 200, 500
Gym:       repeating base 0, then 200, 500
Food:      30,40,100,200,300 tiers across 1001..1032
Ingredient: 100,200,300
Book:       200
Drug:       100,500,100,500,100,500
```

`FUN_005AA360` separately shows that item acquisition compares a per-item
numeric result from `FUN_005AA300` to the player's resource balance before
adding the item.  That is consistent with interpreting these numbers as costs
or economic parameters.  However, a direct getter edge from the global
`0x000A` tables to `FUN_005AA300` has not yet been proven.  What *is* directly
proven is the exact item-domain key mapping, so this must be treated as an
item-keyed numeric/economic registry rather than a second copy of the 70
character stats.  Exact cost semantics remain a runtime/static follow-up.

The current default selection is inverted from the evidence:

```python
USE_BINARY_0010_DEFAULTS = env == '1'       # default False
defaults = custom_defaults if False         # actual supported default today
```

The custom table keeps groups 0, 2, 5, and 6 at their binary values, but
changes the following without matching item-domain evidence:

| Group | Binary values | Current default custom values | Result |
|---:|---|---|---|
| 1 Toy | `200,500` pairs | `500,600` pairs | wrong Toy item parameters |
| 3 Food | `30/40/100/200/300` tiers | progression-like `500,0,500,...,1,2` | severely wrong Food item parameters |
| 4 Ingredient | `100,200,300` | `80,80,0` | wrong Ingredient item parameters, including one zero |

`HIGH_RESOURCE_STATS` is also misnamed: its overrides modify item-domain
parameters, not character resources.  Until a real server table is captured,
the baked binary values are the strongest available defaults.  The client resets these tables
to zero before applying `0x000A`, so omitting or partially filling the packet
is not equivalent to keeping the baked defaults.

This supersedes the `70 u16` count in research note 49 and the character-stat
interpretation in portions of research note 11.

## 3. `S2C 0x000B`: XP curve is already coherent

`HandleS2C_000B_XPCurve` stores 31 `u16` thresholds.  The current server list
matches the client table, including index 22 = `25300` and final sentinel
`60001`.

No field in this packet is an inventory count, quest row, character name, or
current level.  It should remain unchanged while the other contracts are
repaired.

## 4. Persisted `C2S 0x0007`: what it can and cannot restore

`FUN_005A4770` copies/sends exactly `0xC4` bytes from the CJS property snapshot.
`FUN_0059DA00` sends it after more than 10,000 ticks while the state is active,
or on an explicit forced-save path.  Multiple content/stat mutation paths also
call the same sender.  Therefore the correct semantic label is **general
client property snapshot/save**, not `content-completion` or Gym-only save.

The current proven restore mappings are:

| C2S field | S2C field | Verdict |
|---|---|---|
| `+0x0A`, 70 `u16` | `+0x0B`, 70 `u16` | correct directional mapping |
| `+0x9C`, 8 mode bytes | `+0x184`, 8 kind bytes | correct mapping |
| `+0xA4`, 8 `u32` values | `+0x18C`, 8 `u32` values | correct mapping |

It does **not** contain the eight inventory quantity arrays, the ten quest
rows, the four domain banks, or selectors.  Consequently the current state
store cannot make acquired items or quest progress survive reconnect even
though character stats survive.  Those require server-owned persistent fields
and proven mutation/request boundaries; they cannot be reconstructed from the
196-byte snapshot by offset guessing.

Additional persistence risks:

- the server calls every later snapshot a content completion even though the
  client sends the same structure periodically;
- the recorded checksum/sum is logged but not used to reject a malformed
  snapshot;
- the filesystem key is the display-name bytes, while automated clients share
  the default `Azrok1`; two multiplayer clients can therefore select the same
  saved-state file unless identity is anchored to the login/account or another
  per-character identifier;
- the first snapshot on a connection is treated only as bootstrap; persistence
  starts with the next one.  That is acceptable for the reload boundary but
  should be documented as such.

## 5. Name and observed `level: 0`

No string field in `0007`, `000A`, or `000B` sets the local player's display
name.  The self name is initialized to `Guest` and is replaced by the local
name-entry UI.  Remote names are carried in `S2C 0x0066 +7`.  Filling an
unknown setup-blob byte with text would be corruption, not restoration.

The character level itself is `S2C 0x0007` stat index 1.  The builder normally
sends 1, while the shipped/demo candidate is 25.  A label that still displays
0 should be traced to its exact draw/getter path before assigning it to
`0x000A`; `0x000A` is now proven item-keyed.  Also check whether a persisted
snapshot overwrote index 1 with zero.  The floating `이름:/레벨:0/단계:` labels
seen in a room are not sufficient by themselves to prove they are the main
character-status fields.

## 6. `E1201` / evolution is a separate contract

The current dynamic A/B in
`57_evolution1_e1201_dynamic_ab_20260717.md` directly proves:

- at native `Nexus=40`, changing only `S2C 0x0007 payload[2]` from 0 to 1
  reproduces `Error E1201 / Nexus too small (40)` during initial bootstrap;
- replaying the full 472-byte setup later with payload byte 2 = 1 also fails;
- the supported bootstrap must keep this header selector at 0 while the
  natural growth transition is recovered.

This result must not be folded into the item/stat audit.  In particular:

- `S2C 0x0007 payload[2]` is the bootstrap model/evolution selector that was
  A/B-tested;
- indexed stat 55 is a separate `펫진화` stat in the `lgc.tmp` schema;
- using the shipped `init.csv` stat candidate would put value 1 at stat 55,
  but that has not been A/B-tested independently of header byte 2.

Therefore test the corrected stat bag while holding header byte 2 at 0.  Do
not use full-blob replay as an evolution update and do not raise Nexus as the
supported protocol fix.

## 7. Evidence-ranked implementation order

### P0: remove data corruption before adding content

1. Delete the wholesale C2S-to-S2C prefix copy.  Build `S2C 0007` from a clean
   472-byte buffer and apply only explicit directional mappings.
2. Make the baked binary `0x000A` item-domain values the default.  Disable or
   rename the misleading high-resource overrides.
3. Keep `0x000B` unchanged.

### P1: restore coherent character stats

1. Construct the 70-entry candidate with the `lgc.tmp` index order, inserting
   meal counter at 26.
2. Keep indices 57..69 zero until a schema/source is proven.
3. Apply schema clamping deliberately and log the post-clamp values.
4. Test this stat change with `S2C 0007 payload[2]=0` so an E1201 regression is
   not misattributed to content data.
5. Label the high-progress `init.csv` profile as shipped/demo, not as a proven
   new-account default.

### P2: make inventory and quests persistent without inventing history

1. Add server-side inventory arrays using the eight proven domains and
   serialize them into the exact `0x0007` byte lists.
2. Add ten server-side quest rows using the proven ID/progress/value layout.
3. Discover each acquisition/use/completion request and reply independently;
   do not turn `C2S 0007` into an invented ACK.
4. Until original starter-state evidence exists, keep starter grants and a
   one-row quest as opt-in diagnostic/demo seeds.
5. Key saved state by a real per-client login/account identity, not the shared
   `Azrok1` fallback.

### P3: runtime verification matrix

For each change, capture both the packet and the visible result:

1. open the bag and verify one known quantity in each category;
2. buy/use an item and verify the cost and quantity delta;
3. reconnect and verify the quantity survives;
4. show one diagnostic quest row, update progress, reconnect, and verify it;
5. enter Gym/Cook/Magic/Library/Playroom and verify the corrected stat indices
   select the expected local content variants;
6. keep the client window at `(0,0)` during input tests because the engine's
   internal mouse coordinates otherwise diverge from visible coordinates;
7. run the E1201 negative control separately with header evolution 0.

## 8. What is directly recoverable now

The following are strong enough to implement without inventing an ACK:

- exact 472-byte `S2C 0007` structure;
- exact inventory domains, capacities, item IDs, and quantity encoding;
- exact ten-row quest serialization and empty sentinel;
- corrected 57-entry stat alignment using `lgc.tmp`, with `init.csv` as an
  explicitly labelled shipped/demo current-value candidate;
- exact 75-value `S2C 000A` item-domain table using the client binary defaults
  (the exact cost/economic consumer is still to be traced);
- exact 31-value `S2C 000B` XP curve;
- exact stats/mode subset that `C2S 0007` can restore.

The following remain deliberately unclaimed:

- original new-account starter inventory quantities;
- original active quest assignment and progress;
- the acquisition/use/completion request/response for every item/content type;
- whether stat 55 can safely be 1 while header evolution byte 2 stays 0;
- the exact source of the observed room-floating name/level labels.

Those gaps are narrower than before: they are gameplay state and mutation
contracts, not unknown packet shapes.
