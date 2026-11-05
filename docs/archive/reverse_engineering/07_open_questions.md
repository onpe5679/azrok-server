# Open Questions

## Highest Priority

1. What object lives behind `logic + 0x8`, and where is it initialized?
2. Is there a local stage/init function that should run before or during
   network `0x0064` so that the `FUN_005B61F0` path becomes valid?
3. Should `0x0064[0]` use the neutral mode `0x00` instead of `0x0A` for the
   first room-entry packet?

## Secondary Questions

1. When is state-1 `0x0003` safe to replay?
2. Is there a safe point where `0x006E` becomes valid?
3. Does `0x006D` ever become relevant once local state `+0x332 == 2`?
4. Does `0x006B` need to be toggled after the self object exists, or is it
   unrelated to load completion?

## Runtime Instrumentation Wishlist

Useful values to log live from the process:

- current-player singleton:
  - self id `+0x2F8`
  - entity ptr `+0x99`
  - ready flag `+0x31A`
- loading popup:
  - `+0x9B`
  - `+0x9C`
- global scene/load state:
  - `game+0x31792`
- any pointer chain that proves the `logic + 0x8` submanager exists

## Immediate Next Investigation Options

1. Find and initialize the `logic + 0x8` submanager before the `0x005B61F0`
   call inside `0x00615650`.
2. Guard or postpone the `0x005B61F0` branch to confirm whether the load-close
   path is reachable without that subsystem.
3. Test `0x0064` with `entry_mode = 0x00` after the deeper submanager issue is
   understood.
