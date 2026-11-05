# Loading Popup And Close Path

Important clarification:

- the current client loading screen is not modeled as a separate tooltip layer
- the visible help text is part of the loading-screen art / popup composition
- in code terms, this is still a `CPopupLoading` problem, not a distinct
  tutorial-overlay problem

## Main Close Chain

Current confirmed chain:

- `FUN_00615650`
- `-> FUN_0050A840`
- `-> FUN_005CA8B0`
- `-> FUN_005CA6C0`
- `-> FUN_005CAB30`

Meaning:

- `FUN_0050A840`
  - issues the loading-close request
- `FUN_005CA8B0`
  - hides loading-bar objects
  - sets `popup+0x9C = 1`
- `FUN_005CA6C0`
  - popup update tick
  - checks `+0x9B` first, then `+0x9C`
- `FUN_005CAB30`
  - performs the actual close behavior

## Open Path

Confirmed open/start chain:

- `FUN_0050A7F0`
- `-> FUN_005CA710`
- `-> FUN_005CA360`

Meaning:

- `FUN_0050A7F0`
  - stores the scene/load code in `gm+0x31AAD`
- `FUN_005CA710`
  - sets `popup+0x9B = 1`
  - sets `popup+0x93 = 100`
  - chooses the loading image index in `popup+0x97`
- `FUN_005CA360`
  - creates or refreshes the main loading popup
  - loads `Data\\Common\\Loading%d.wis` or `MainLoading_test.wis`

## Popup Fields That Matter

`popup = gm + 0xD98`

Important fields:

- `popup + 0x8F`
  - active popup object pointer
- `popup + 0x8A`
  - logo child panel/object
- `popup + 0x93`
  - shared open/close animation progress
- `popup + 0x9B`
  - open/update flag
- `popup + 0x9C`
  - close-latched flag
- `popup + 0x9D`, `popup + 0xA1`
  - loading-bar child objects

## Immediate vs Animated Close

The key gate is:

- `game + 0x31792`

If `logic_state != 3`:

- close is immediate
- `popup+0x9C` should drop back to `0`
- `popup+0x93` should reset to `0`

If `logic_state == 3`:

- close is animated
- `popup+0x93` is decremented until the final close helper runs
- final close goes through `FUN_005CA970`
- `FUN_005CA970` then calls the popup vtable `+0x0C` finalizer
- that finalizer resolves to `FUN_005CA510`, which destroys/nulls the popup and
  loading-bar child objects

## What Not To Assume

- `popup+0x9C = 1` does not mean gameplay is visible
- it only means the loading-screen close request fired
- an earlier visual interpretation of this state as "tutorial" or "almost
  gameplay" is no longer treated as reliable

## Practical Interpretation

- `popup+0x9C = 1` means the close request path definitely fired.
- `popup+0x9C` by itself does not guarantee the user-visible popup is already
  gone; the next popup tick still matters.
- `popup+0x9B` can still touch the active popup before `+0x9C` is consumed.
- a partially filled loading bar means the staged loader moved forward, but it
  does not prove the final close path completed.

## Current Patch Direction

- keep null guards that prevent scene/bootstrap crashes
- avoid aggressive popup hard-bypass patches by default
- reason:
  - the loading screen is the popup itself
  - skipping popup finalize/teardown too early can interfere with the real
    loading-screen exit path

## Current Investigation Read

The current blocker is no longer just "did `FUN_0050A840` ever run."

The harder question is:

- did the popup close path run on the active popup at the right time
- while the singleton self object and local scene bootstrap state were valid

That is why popup telemetry is useful, but still secondary to:

- `self entity ptr`
- `ready`
- model selector bytes

## 2026-03-30 Evening Addendum

- The visible loading/help screens were explicitly reclassified during live
  testing.
  - the top tutorial/help text is part of the baked loading composition
  - the full-screen move/drag tip art is also still loading state
- A confirm popup appearing on top of that background is not accepted as
  successful room entry.
- The current success condition remains:
  - real 3D room visibility
  - loading popup gone
  - controllable in-world input
- This is why popup close flags and progressed text are now treated as useful
  but insufficient signals.

## 2026-03-30 First-World Resource Read

Workspace resource layout and current Ghidra findings now separate the early
UI/lobby assets from the first likely real 3D tutorial world.

### Small Selection/Transition Worlds

These are present, but look too small and too UI-adjacent to be the first full
tutorial room:

- `Data\\Space\\SelectPet\\pet.wmb`
  - about `182 KB`
  - strongly aligned with `Data\\Lobby\\SelectPet\\*.wis`
- `Data\\Space\\lobby\\lobby.wmb`
  - about `182 KB`
  - likely a lightweight lobby/selection background or transition scene

### Large World Candidates

- `Data\\Space\\Plaza\\hansol.wmb`
  - about `9.8 MB`
  - matches the Plaza-oriented `0x6E` bootstrap branch
- `Data\\Space\\PatHouse\\room.wmb`
  - about `7.1 MB`
  - matches the house/furniture/foodmaker-heavy `100` branch much better

### Current Best Read

High-confidence:

- `pet.wmb` is more likely the selection-screen 3D background than the first
  real playable room
- the Plaza-oriented `0x6E` branch is real, but it is not a good semantic fit
  for the baby-feeding tutorial
- `PatHouse\\room.wmb` is a plausible true first 3D tutorial room because the
  `100` branch directly manipulates PatHouse interior objects and `foodmaker`
  assets

Most likely packet-first interpretation:

- `0x0003("Data\\Space\\PatHouse")`
  - is the strongest current candidate for the first true tutorial-room path
- `0x0003("Data\\Space\\Plaza")`
  - is more likely the Plaza hub path or a later post-tutorial space path
- `0x0003("Data\\Space\\Lobby")`
  - does not currently fit the observed create/select UI strings as well as the
    dedicated `Data\\Lobby\\...` asset tree does

## 2026-03-30 `FUN_0050a0f0` Space Switch Clarification

`FUN_0050a0f0` is now confirmed as a local scene switcher that uses queued
space codes and then calls `level_load()` with bare WMB names.

Relevant confirmed cases:

- case `0`
  - `level_load(\"room.wmb\")`
  - then queues post-load code `100`
- case `8`
  - `level_load(\"lobby.wmb\")`
  - then queues post-load code `0x6c`
- case `9`
  - `level_load(\"pet.wmb\")`
  - then queues post-load code `0x6b`
- case `0xb`
  - if `gm+0x31c71 != 0`, `level_load(\"hansol.wmb\")`
  - then queues post-load code `0x6e`

This sharply strengthens the room-vs-Plaza read:

- case `0 -> room.wmb -> 100` is the best fit for the first indoor tutorial
  room
- case `0xb -> hansol.wmb -> 0x6e` is the best fit for Plaza/hub entry
- case `9 -> pet.wmb -> 0x6b` looks more like select/create-pet presentation
  than the real tutorial room

## What Most Likely Selects Case `0`

Current best packet-first reading:

1. `S->C 0x0003` sets the local space root such as `Data\\Space\\PatHouse`
2. some local create/new-pet transition queues scene code `0`
3. `FUN_0050a0f0` consumes that queued code and runs:
   - `level_load(\"room.wmb\")`
   - queue code `100`
4. the later first `S->C 0x0007` / local loader state then needs to remain on
   the `100` post-load path rather than getting diverted to `0x6e`

Why this is the strongest current read:

- `0x0007` itself only explains the post-load branch decision
  (`100 / 0x6e / 0x6f`)
- it does not explain the raw `room.wmb` level switch directly
- `room.wmb` is a bare filename, so it likely depends on the earlier `0x0003`
  space-root path being the correct folder
- a `PatHouse` root plus queued scene code `0` is the cleanest explanation for
  `room.wmb`

Practical implication:

- if the current packet flow says `Data\\Space\\Plaza` too early, but the
  client's natural first-room scene code is actually `0`, the client is pushed
  into a Plaza/PatHouse mismatch before local bootstrap even starts
