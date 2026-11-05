# Self Singleton And Local Bootstrap

## The Real Object `0x0064` Cares About

`0x0064` does not primarily care about the generic actor list. It uses the
singleton self/current-player object:

- `player = gm + 0x35C20`

Important fields:

- `player + 0x99`
  - self entity/model pointer
- `player + 0x2F8`
  - self actor id
- `player + 0x2FC`
  - owner/backpointer
- `player + 0x31A`
  - ready flag
- `player + 0x9D`, `player + 0xA1`
  - model selector bytes

Reset state is still:

- `+0x99 = 0`
- `+0x31A = 0`

## Confirmed Local Creator Chain

The strongest native creator path is:

- `FUN_0050B400(0x6E)`
- `-> FUN_00614370`
- `-> stage 0`
- `-> FUN_006130B0`

Inside `FUN_006130B0`:

1. `FUN_00524280` seeds:
   - `+0x9D`
   - `+0xA1`
   - `+0x2F8`
2. `FUN_00525A60` creates the local entity/model and stores it into `+0x99`
3. `FUN_005247F0(1)` latches the ready flag

Important detail:

- `FUN_005247F0` only writes `+0x31A`
- it does not create the entity by itself

## What Network Packets Do Not Do

- `0x0064`
  - uses the singleton
  - can reach the loading-close request path
  - does not create the singleton
- `0x0066`
  - handles actor-list records
  - on the self-id path it is not the real singleton creator
- `0x0068`
  - caches or updates coords
  - on the self-id path it is mostly support behavior, not creation
- `0x0069`
  - position/commit support
  - still not the local singleton creator

That is why these states are possible at the same time:

- self id is nonzero
- cached coords exist
- `entity ptr == 0`
- `ready == 0`
- loading progresses partway but never finishes

## Current Experimental Patch

The current runtime experiment hooks the `0x0064` null-entity path and tries to
enter the native local scene bootstrap:

- call `FUN_0050B400(0x6E)` from the guard
- force `ECX = gm` because the function is `thiscall`

This patch exists because packet flow alone has not been enough to create:

- `player + 0x99`
- `player + 0x31A`
- `player + 0x9D/+0xA1`

## Practical Reading Rule

If telemetry shows:

- `self id != 0`
- `entity ptr == 0`
- `ready == 0`
- `model = FF/FF`

then the client is still missing the real local singleton self object, even if
state 1 and popup logic moved farther forward.

## High-Confidence `0x0007` Dependencies For Natural Bootstrap

`FUN_006130B0` does not only depend on the fact that loading started. It also
consumes local fields that are populated by the earlier `0x0007` path.

### The Last Four Bytes Of `0x0007` Feed Bootstrap Slot Values

Inside `FUN_0059e330`:

- `FUN_005ab080(param_1 + 0x1d4, 4)` copies packet bytes
  `payload[0x1D4..0x1D7]`
- those four bytes become local object dwords at `+0x1D8..+0x1E4`

Inside `FUN_006130B0`:

- `FUN_005ab2b0(0..3)` reads those four dwords back
- each value is then fed into `FUN_00521e90(slot, value, 0)`

Meaning:

- these are not dead tail bytes
- they are direct natural-bootstrap inputs
- they look like four slot/category item selectors used during early self setup

Important consequence:

- `0` is not "empty" here
- `FUN_00521e90` maps slot values like this:
  - slot 0: `value + 10000`
  - slot 1: `value + 20000`
  - slot 2: `value + 30000`
  - slot 3: `value + 40000`
- only `0xFF` is treated as the explicit clear/sentinel path

So a builder that leaves `0x1D4..0x1D7 = 0` is not leaving the bootstrap empty;
it is selecting the lowest valid id in each bucket.

### `0x0007` Also Seeds Species/Appearance Inputs Used By `FUN_006130B0`

Natural bootstrap reads values that come from the earlier `0x0007` setup:

- `FUN_00545500()` reads the field written from `0x0007 + 0x01`
- `FUN_005465C0()` reads the field written from `0x0007 + 0x02`
- `FUN_00524280()` then seeds:
  - `player + 0x9D`
  - `player + 0xA1`
  - `player + 0x2F8`
- `FUN_00525A60()` uses `player + 0x9D/+0xA1` to pick the local Plaza model
  path such as:
  - `Data\\Plaza\\Model\\P_AK`
  - `Data\\Plaza\\Model\\P_AO`
  - `Data\\Plaza\\Model\\P_PZ`
  - `Data\\Plaza\\Model\\P_TO`

Current implication:

- wrong or too-empty `0x0007` values can make the natural bootstrap choose the
  wrong local model/species path even before state-1 `0x0064` arrives

### Packet-First Reading

The clean path is likely:

1. `0x0003` arms the path/loader state
2. first `0x0007` seeds local bootstrap inputs and opens the natural loading
   flow
3. local scene path reaches `FUN_00614370 -> FUN_006130B0`
4. only after that should state-1 packets such as `0x0064` operate on a valid
   singleton self object

That is why packet-first reconstruction should focus on the semantic contents of
`0x0007`, not just on keeping `0x0064` alive with rescue patches.

## 2026-03-30 Packet-First Addendum

High-confidence structure recovered from `FUN_006130B0`:

- the local bootstrap builds a small temporary struct and feeds it into
  `FUN_00524280`
- inside that struct:
  - `+1`
    - is a `GetTickCount()`-derived temporary id
    - this is why the local bootstrap alone produces a tickcount-like self id
      before later authoritative reconciliation
  - `+5`
    - comes from manager `+300`
    - originally loaded by `0x0007 byte1`
    - becomes `player+0x9D`
  - `+6`
    - comes from manager `+0x130`
    - originally loaded by `0x0007 byte2`
    - becomes `player+0xA1`
  - `+7`
    - is the copied local player name buffer

Practical implication:

- the current packet-first path should treat `0x0007 byte1` as selected Azron
  type, not a disposable mirrored request byte
- a later `0x0064` or equivalent authoritative step is still needed to replace
  the temporary local self id with the true actor id

## 2026-03-30 Scene-Branch Clarification

The client does not have only one natural local scene/bootstrap branch after the
first `0x0007`.

### `0x6E` Branch Is Plaza-Oriented

`FUN_0050d290` chooses `FUN_0050A7F0(0x6E)` when `gm+0x31C72 != 0`.

That branch reaches:

- `FUN_0050B400(0x6E)`
- `-> FUN_00614370`
- `-> FUN_006130B0`

High-confidence reading:

- this branch is Plaza-oriented, not house-oriented
- `FUN_006130B0` builds the self model from `Data\\Plaza\\Model\\P_*`
- later `FUN_00614370` stages touch Plaza-only scene assets such as:
  - `Data\\Plaza\\Mount\\MiniCar.MDL`
  - `Data\\Plaza\\Model\\staff.MDL`
  - `Data\\.\\Plaza\\bee.npc`

### `100` Branch Is PatHouse-Oriented

`FUN_0050d290` chooses `FUN_0050A7F0(100)` when both:

- `gm+0x31C72 == 0`
- `gm+0x31C73 == 0`

The `100` branch runs `FUN_00531640`. Its stage-1 helper `FUN_00557570`
directly creates and manages PatHouse assets, including:

- `Data\\Space\\PatHouse\\door.MDL`
- `foodmaker_01`
- many `PatHouse` furniture/object name tables
- local temporary character models for the selected Azron type

High-confidence reading:

- the `100` branch is the branch that matches the indoor baby-care / feeding
  tutorial better than the Plaza branch
- if the first real tutorial room is a house interior, this branch is the best
  native candidate

### Practical Consequence

If the server says `Data\\Space\\Plaza` in `0x0003`, but the client's early
loader state still chooses the `100` branch, the client is pushed into a mixed
state:

- path/level expectation points toward Plaza
- local bootstrap logic points toward PatHouse tutorial objects

That Plaza/PatHouse mismatch is now one of the strongest packet-first suspects.
