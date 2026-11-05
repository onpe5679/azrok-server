# Runtime Structures

## Current-Player Singleton

This is the object `0x00615650` really cares about.

Confirmed fields:

- `+0x99`
  Entity/model pointer.
- `+0x31A`
  Entity-ready flag.
- `+0x2F8`
  Self actor id.
- `+0x11B / +0x11F`
  Cached coords used by `0x0068` when entity is not ready.
- `+0x12B / +0x12F`
  Cached coords used by `0x0069` when entity is not ready.

Confirmed behavior:

- constructor/reset path clears `+0x99` and `+0x31A`
- `0x0064` uses this singleton
- `0x0066/0x0068/0x0069` do not create this singleton
- local creation helpers such as `FUN_00525A60` and `FUN_005247F0` do set it up

## Actor-List Objects

These are separate from the singleton self object.

Important consequence:

- `0x0066` can create or update actor-list entities
- that does not mean the singleton self/current-player object is ready

This distinction explains why some experiments made visual progress but still
failed to finish loading.

## Loading Popup

Confirmed popup fields:

- `+0x9B`
  Entry/update flag.
- `+0x9C`
  Close request flag.
- `+0x9D`
  First bar object.
- `+0xA1`
  Fill bar object.

Confirmed close path:

1. `FUN_0050A840`
2. `FUN_005CA8B0`
3. `FUN_005CACE0`
4. `popup+0x9C = 1`
5. next update in `FUN_005CA6C0` closes the popup

If the bar remains visible, `FUN_0050A840()` likely did not run to completion.

## Scene / Local Mode Fields

Confirmed local-mode read:

- `FUN_00613690(param) -> *(param + 0x332)`

This field gates `0x006D`.

Confirmed global scene-close behavior:

- `FUN_0050A0F0` writes `game+0x31792`
- if `game+0x31792 != 3`, the loading popup should close immediately once the
  close path runs

## New Latest Candidate Structure

The latest crash at `Azrok.exe+0x001B6213` is inside `FUN_005B61F0`, which is
reached from the `0x0064` tail through the `[logic + 0x8]` side of the runtime
object. This strongly suggests there is another required submanager beyond the
current-player singleton itself.
