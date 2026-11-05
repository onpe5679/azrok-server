# Protocol And State-1 Flow

## Transport And Runtime Dispatch

Packet framing is:

- `u16 payload_size`
- `u16 opcode`
- `payload[payload_size]`

Confirmed runtime path:

1. `CClientPeer` accumulates TCP bytes
2. `0x00593E40` dequeues packets
3. final opcode dispatch lands in `CLogicManager::0x00594310`

Important correction:

- `0x5927D0` is a real stub, but not the final live handler
- state-1 packet routing comes from `0x00594310 -> 0x00613740`

## Stable Observed Flow

Current stable client/server order is:

1. client `0x0000`
2. server heartbeat/login reply
3. client `0x0004`
4. server `0x0002`
5. server `0x0003("Data\\Space\\Plaza")` by default
6. client `0x0007`
7. server `0x0007`, `0x0005`, `0x0010`, `0x0011`
8. client `0x0001`
9. client `0x0017`
10. server state-1 follow-up

The first client `0x0017` is the current best pivot point for state-1
bootstrap.

## Important Packet Meanings

### Early State-0 Packets

- `0x0002`
  - real transition trigger
- `0x0003`
  - `[flag][NUL-terminated path string]`
  - current useful values: `Data\\Space\\Lobby`, `Data\\Space\\Plaza`
  - active default is now `Data\\Space\\Plaza`
  - reason:
    - `Data\\Space\\Plaza` has the matching world/environment assets
    - current local bootstrap also aligns with Plaza-oriented world strings
- `0x0007`
  - large setup blob
  - working size remains about `0x1D8`
  - newly confirmed high-value fields:
    - `+0x01`
      - copied to manager `+300`
      - later read by `FUN_006130B0 -> FUN_00545500`
      - becomes self model selector byte `player+0x9D`
    - `+0x02`
      - copied to manager `+0x130`
      - later read by `FUN_006130B0 -> FUN_005465C0`
      - becomes self model selector byte `player+0xA1`
    - `+0x03`
      - packed datetime code consumed by `FUN_005A8C90`
    - `+0x07`
      - written through `FUN_0059E300` to the same manager field updated by
        `0x0005[2:6]`
    - `+0x125..+0x12F`
      - 11 direct command bytes fed one-by-one to `FUN_0059A6E0`
      - `0x00` is not neutral here
      - `0xFF` is the safest current no-op sentinel
- `0x0010`, `0x0011`
  - stat/resource tables
  - they are not equally suspicious:
    - `0x0010` now appears to mirror the binary's built-in keyed registry
      defaults exactly
    - `0x0011` already matches the binary curve table more closely


### State-1 Packets

- `0x0064`
  - mandatory state-1 pivot
  - only confirmed network packet that reaches `FUN_0050A840()`
- `0x0065`
  - finalize/reset style support packet
- `0x0066`
  - actor-list record ingestion
- `0x0068`
  - actor position/cache update
- `0x0069`
  - actor position commit
- `0x006E`
  - meaningful setup path, but unsafe as an early network packet

### Client Signals

- `0x0016`
  - heartbeat
- `0x0017`
  - strongest current sign of room-entry/self-spawn phase
  - current stable payload: `07 01 00 00 00 00`
- `0x0064`
  - newly observed outbound client packet after local bootstrap progress
  - latest seen payload: `04`
  - currently treated as a progress/ack marker and logged without reply

## Opcode Index By Direction

This is the quickest current reference for every opcode we have materially
observed or used so far.

### Client To Server (`C->S`)

| Opcode | Status | Current meaning | Notes |
| --- | --- | --- | --- |
| `0x0000` | confirmed | initial hello / login-side open packet | first large client blob |
| `0x0001` | observed | disconnect-ish / state transition signal | do not echo back |
| `0x0004` | confirmed | character creation packet | includes type and name |
| `0x0007` | confirmed | large setup blob | current client payload around `0xC4` bytes |
| `0x0016` | confirmed | heartbeat | server currently answers with `0x0016(00)` |
| `0x0017` | confirmed | first strong state-1 progress signal | current stable payload `07 01 00 00 00 00` |
| `0x0064` | newly observed | state-1 progress / ack marker | latest outbound form is payload `04`; log only, no reply |

### Server To Client (`S->C`)

| Opcode | Status | Current meaning | Notes |
| --- | --- | --- | --- |
| `0x0000` | confirmed | login reply draft | sent after early heartbeats |
| `0x0002` | confirmed | transition trigger | safe early state-0 reply |
| `0x0003` | confirmed | enter-space path packet | current useful values `Data\\Space\\Lobby` and `Data\\Space\\Plaza`; active default is Plaza unless strict mode is set |
| `0x0005` | confirmed | small state/refresh packet | currently sent after server `0x0007`; 6-byte meaningful layout |
| `0x0007` | confirmed | large zone/setup blob | current working size about `0x1D8` |
| `0x0010` | confirmed | keyed stat/resource table A | currently `150B`; current server values match the binary's built-in registry defaults |
| `0x0011` | confirmed | scalar curve table B | currently `62B`; current server values already match the binary curve table |
| `0x0016` | confirmed | heartbeat reply | current payload `00` |
| `0x0064` | confirmed | mandatory state-1 pivot | only confirmed network packet that reaches the loading-close path |
| `0x0065` | confirmed | finalize/reset support packet | low-risk support after `0x0064` |
| `0x0066` | confirmed | actor-list / scene actor record | useful support packet; not sufficient to build singleton self |
| `0x0068` | confirmed | actor position/cache update | support packet |
| `0x0069` | confirmed | actor position commit | support packet |
| `0x006E` | historical / unsafe early | meaningful setup path | local bootstrap uses internal `0x6E`, but early network `0x006E` is crash-prone |

### Notable Direction-Sensitive Rules

- `0x0003` means different things before and after state 1.
- `C->S 0x0064(04)` should not be echoed back as `S->C 0x0064`.
- `S->C 0x0064` is heavy and stateful; `C->S 0x0064` is currently treated as a
  progress signal, not a request packet.

## `0x0064` Working Layout

Current best map:

- `+0x00`: entry/state byte
- `+0x01`: self actor id
- `+0x06`: x
- `+0x0A`: y
- `+0x12/+0x13`: small appearance bytes
- `+0x14..+0x1A`: time block

Accepted first-byte values seen in code:

- `0x00`
- `0x0A`
- `0x0B`
- `0x14`

Best next safe candidate remains:

- neutral `0x00`

## Ordering Rules That Still Matter

- `0x0003` before `0x0064` is state-0 behavior; `0x0003` after `0x0064` is a
  different state-1 meaning.
- state-1 `0x0003` replay is currently unsafe and tied to crash
  `0x005D407F`.
- early network `0x006E` is currently unsafe and tied to crash `0x00616AD2`.
- `0x0066/0x0068/0x0069` are useful support packets, but they are not the
  singleton self-object creator path.
- unknown client packets should not be blindly echoed back, especially outbound
  `0x0064`, because that can re-enter the dangerous inbound opcode-100 path.

## High-Confidence Natural Transition Notes

### `0x0003` Is A Path/Loader-Arming Step, Not The Creator

State-0 `S->C 0x0003` flows through:

- `FUN_0050d200`
- `-> FUN_0050c250(param + 1)`
- `-> FUN_005d4070(param + 1)`

What this means:

- the first payload byte is a small mode/flag
- `payload + 1` is the actual NUL-terminated path string
- the handler copies that string into local loader state and arms follow-up
  loader/popup fields
- this path does not directly create the singleton self object

So `0x0003("Data\\Space\\...")` matters, but by itself it is not the step that
creates the local self entity.

### First `0x0007` Is More Than A Data Blob

State-0 `S->C 0x0007` runs in two layers:

1. generic handler:
   - `FUN_0059dd20(7, payload)`
   - `-> FUN_0059e330(payload)`
2. secondary transition handler:
   - `FUN_0050cbc0(7, payload)`
   - `-> FUN_0050d290()`
   - `-> FUN_0050a7f0(100 / 0x6e / 0x6f)`

This is the strongest current evidence that the first server `0x0007` is part
of the natural local loading path itself, not just a static configuration blob.

Current reading:

- if packet semantics are correct, this is the path that should naturally open
  the correct loading flow and eventually reach the local scene bootstrap
- if packet semantics are wrong, the client still opens a loading path, but
  later local scene/bootstrap state becomes inconsistent

Important refinement:

- the first `0x0007` does not appear to directly choose the raw `level_load`
  target such as `room.wmb` or `hansol.wmb`
- instead, it chooses the follow-on post-load branch code:
  - `100`
  - `0x6e`
  - `0x6f`
- the actual `level_load("room.wmb" / "lobby.wmb" / "hansol.wmb" ...)` switch is
  handled elsewhere by `FUN_0050a0f0`
- this means path selection and post-load bootstrap selection are related, but
  they are not the same decision point

### `0x0007 + 0x07` And `0x0005 + 0x02` Feed The Same State Field

Two different packets write the same local field through `FUN_0059e300`:

- `0x0007`
  - dword at `payload + 0x07`
- `0x0005`
  - dword at `payload + 0x02`

This means `0x0005` is not independent filler.

High-confidence interpretation:

- `0x0007` seeds a scene/tutorial-related state value
- `0x0005` can later confirm, override, or advance that same value depending on
  subtype/status

Current builder risk:

- we currently leave `0x0007 + 0x07` at the echoed client value or `0`
- we currently send a very conservative `0x0005`
- that is likely too weak to match the original server's progression semantics

## 2026-03-30 Evening Addendum

- Repeated late client `0x0007` packets are now confirmed after state-1
  bootstrap on some runs.
- Experimental server behavior:
  - first client `0x0007` still receives the full startup bundle
  - later client `0x0007` can optionally receive a minimal `S->C 0x0007`-only
    reply
- Current reading of that late `0x0007` branch:
  - it can advance top tutorial/help text
  - it does not yet prove or force the real 3D room transition
- `C->S 0x0064(04)` remains log-only.
  - echoing it back was already shown to be dangerous

## 2026-03-30 Packet-First Addendum

- `0x0007 byte1/byte2` are now promoted from "unknown header bytes" to
  first-class model/bootstrap selectors.
- This means mirroring the client request's zero-filled values there is
  probably wrong once the user has already chosen an Azron type.
- `0x0007 +0x07` and `0x0005[2:6]` update the same manager-side dword through
  `FUN_0059E300`.
  - practical implication:
    - `0x0005` is not just an unrelated support blob
    - it may be a later state/timer/tutorial update that must stay coherent
      with the original `0x0007`

## 2026-03-30 Packet-First Handler Notes

High-confidence findings from the native handlers:

- `S->C 0x0005` (`FUN_0059ebd0`)
  - meaningful size is 6 bytes
  - layout:
    - `+0x00`: status byte
    - `+0x01`: subtype byte
    - `+0x02..+0x05`: little-endian dword
  - important coupling:
    - this dword goes through the same setter (`FUN_0059e300`) as
      `S->C 0x0007 + 0x07`
    - a zero-filled `0x0005` can therefore clobber the state just written by
      `0x0007`
  - subtype `0x13` has extra behavior beyond just storing the dword
  - subtype `0x00` is the plainest form
- `S->C 0x0010` (`FUN_0059eca0`)
  - resets seven keyed global tables and refills them from grouped `u16`
    ranges
  - group sizes / key families:
    - 22 entries keyed by scattered low IDs
    - 6 entries keyed near `2002..2009`
    - 5 entries keyed near `2501..2507`
    - 32 entries keyed `1001..1032`
    - 3 entries keyed `1500..1502`
    - 1 entry keyed `3000`
    - 6 entries keyed `4000..4005`
  - practical reading:
    - `0x0010` is a real structured registry, not filler
    - our current convenience values here are therefore suspicious
- `S->C 0x0011` (`FUN_0059eee0 -> FUN_005a50f0`)
  - plain 31-entry `u16` curve
  - copied directly into `DAT_006e0a88`
  - practical reading:
    - this packet still matters
    - but it is a lower-priority suspicion than `0x0010`, because the current
      server values already mirror the binary table

## 2026-03-30 Protocol-First Addendum

High-confidence `S->C 0x0007` findings from `FUN_0059e330` and key callees:

- `+0x03 : u32`
  - consumed by `FUN_005a8c90`
  - interpreted as packed `YYMMDDHH`
  - later recomposed by `FUN_005a8d40`
- `+0x07 : u32`
  - stored directly via `FUN_0059e300`
  - `S->C 0x0005` updates the same state dword
  - current reading:
    - this is a shared phase/state/timer field
    - always sending `0` is probably too conservative
- `+0x0B .. +0x96 : 0x46 * u16`
  - fed to `FUN_005a4880(index, value)`
  - `FUN_005a37a0` shows this table is a named property/stat bag, not padding
  - known names in the same property system include:
    - `레벨`
    - `IQ`
    - `경험치`
    - `허기치`
    - `위생치`
    - `위치_X`
    - `위치_Y`
    - `펫`
    - `펫진화`
    - `턴횟수`
    - `명령횟수`
- `+0x97`, `+0xB8`, `+0xC7`, `+0xEA`, `+0x110`, `+0x113`, `+0x11D`, `+0x131`
  - copied through `FUN_0059bc00`
  - only non-zero bytes are imported into internal registries
  - these look like keyed byte-list containers, not direct fixed-meaning dwords
- `+0x125 .. +0x12F : 11 raw bytes`
  - this region is special
  - `FUN_0059e330` sends each byte directly to `FUN_0059a6e0`
  - `0` is a live low-id stat/event, not an empty marker
  - strong implication:
    - zero-filling this region creates synthetic event processing
    - `0xFF` is the safer no-op sentinel than `0`
- `+0x134`, `+0x148`, `+0x15C`
  - 10-slot tri-table normalized into a local table, then passed to
    `FUN_005a5ab0`
  - current reading:
    - scheduled pet/tutorial/task-style slots with ids, aux values, and dword
      payloads
- `+0x184`, `+0x18C`
  - 8 mode/value pairs passed to `FUN_005aa6f0`

High-confidence `S->C 0x0005` findings from `FUN_0059ebd0`:

- layout is real:
  - `status = payload[0]`
  - `subtype = payload[1]`
  - `state = payload[2:6]`
- subtype behavior:
  - `0x00` with `status=0` only updates the shared state dword
  - `0x12` with `status=0` also only updates that dword
  - `0x13` with `status=0` additionally flushes an internal queued list via
    `FUN_005a9b50`
- practical implication:
  - current `0x0005(status=0, subtype=0x00, state=0)` is safe, but may be
    skipping real progression work

High-confidence `S->C 0x0010` / `0x0011` findings:

- `0x0010`
  - is not arbitrary padding
  - it updates several keyed u16 registries through `FUN_005aa090`
  - observed key groups are:
    - small stat ids such as `1,2,4,5,...,32`
    - `1001..1032`
    - `1500..1502`
    - `2002,2003,2005,2006,2008,2009`
    - `2501,2502,2504,2505,2507`
    - `3000`
    - `4000..4005`
- `0x0011`
  - is a direct 31-entry global u16 table copy via `FUN_005a50f0`

Best next packet-only experiments:

1. keep rescue patches out of the decision loop as much as possible
2. preserve full client-provided `0x0007` bytes whenever present
3. stop zero-filling `0x0007+0x125..0x12F`; use `0xFF` sentinel instead
4. investigate non-zero / real `0x0005` subtype and state-dword values
5. treat `0x0010` / `0x0011` as meaningful keyed registries, not cosmetic junk

## 2026-03-30 Local File Evidence For `0x0010` / `0x0011`

High-confidence result:

- `init.csv` and `lgc.tmp` are useful semantic clues
- they are not a clean direct source for `S->C 0x0010`
- they do not justify a direct server rewrite of the current `0x0010` table yet
- the current `0x0010` defaults already match the binary's built-in keyed
  registry arrays
- `S->C 0x0011` already has a clean binary-derived source and should stay as-is

### Exact `0x0010` Field Map

Native handler `FUN_0059eca0` consumes exactly 150 payload bytes as 75 `u16`
values:

- `+0x00 .. +0x2B`
  - 22 entries
  - keys:
    - `1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17, 19, 20, 22, 23, 25, 26, 28, 29, 31, 32`
- `+0x2C .. +0x37`
  - 6 entries
  - keys:
    - `2002, 2003, 2005, 2006, 2008, 2009`
- `+0x38 .. +0x41`
  - 5 entries
  - keys:
    - `2501, 2502, 2504, 2505, 2507`
- `+0x42 .. +0x81`
  - 32 entries
  - keys:
    - `1001 .. 1032`
- `+0x82 .. +0x87`
  - 3 entries
  - keys:
    - `1500, 1501, 1502`
- `+0x88 .. +0x89`
  - 1 entry
  - keys:
    - `3000`
- `+0x8A .. +0x95`
  - 6 entries
  - keys:
    - `4000 .. 4005`

Handler behavior:

- `FUN_005a9f10()` zeroes all seven keyed registries first
- `FUN_005aa090(group, key, value)` then writes the new values into sparse
  per-group key tables
- this confirms `0x0010` is a real keyed registry update, not cosmetic padding

### Exact `0x0011` Field Map

Native handler `FUN_0059eee0 -> FUN_005a50f0` consumes exactly 62 payload bytes:

- 31 contiguous `u16` values
- copied directly into global table `DAT_006e0a88`

The binary table already matches the current server defaults:

- `0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500, 5500, 6600, 7800,`
  `9100, 10500, 12000, 13600, 15300, 17100, 19000, 21000, 23100, 25500,`
  `27600, 30000, 32500, 35100, 37800, 40600, 43500, 60001`

Practical implication:

- `0x0011` is not the table to rewrite from local csv/tmp files

### What `init.csv` / `lgc.tmp` Actually Match

Observed local files:

- `init.csv`
  - 55 rows
  - starting current values for named gameplay stats
- `lgc.tmp`
  - 57 rows
  - template/current-zero version of the same named stat schema

Examples from `lgc.tmp`:

- `IQ`
- `레벨`
- `경험치`
- need/threshold/memory rows
- cleaning rows
- action/food experience rows
- `펫진화`
- `펫`

High-confidence reading:

- these files line up with the native 57-entry named stat/property layer
  described elsewhere in the binary
- they do not line up directly with the seven sparse numeric key families used
  by `0x0010`
- the stronger live hypothesis is now that they are closer to the
  `0x0007 + 0x0B..0x96` `0x46 * u16` property/stat bag than to `0x0010`

Why this matters:

- `lgc.tmp` row count being close to one subset of `0x0010` group sizes is not
  enough proof of row-to-key identity
- `init.csv` is missing `IQ` and `식사카운터`, so it cannot be treated as a
  direct row-order source for a full `0x0010` rewrite
- the local files are much stronger evidence for semantic categories than for
  exact `0x0010` slot ordering

### Safe Current Conclusion

- keep `0x0011` unchanged
- keep the current `0x0010` defaults unless new native evidence contradicts the
  built-in registry arrays
- do not replace `0x0010` from `init.csv` / `lgc.tmp`
- shift local-file packet-first work toward the `0x0007 + 0x0B..0x96` bag

Best next packet-first work on `0x0010`:

1. recover where the sparse key families are read back in gameplay code
2. determine whether groups `1001..1032`, `1500..1502`, `3000`, and
   `4000..4005` map to action caps, scalar flags, or UI/tutorial gates
3. only then rewrite the server defaults group-by-group instead of swapping in
   guessed csv row order
