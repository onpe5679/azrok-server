# Crash Diary

## `Azrok.exe + 0x0021571E`

Observed in earlier `0x0064` experiments.

Meaning:

- inside `0x00615650`
- write to `entity + 0x10`
- current-player entity pointer was null / invalid

What it proved:

- `0x0064` expects the singleton current-player entity to already exist
- actor-list packets alone are not enough

## `Azrok.exe + 0x00216AD2`

Observed when `0x006E` was sent too early.

Meaning:

- inside `0x006169D0 -> 0x00616AC0`
- object used by `0x006E` was not ready

What it proved:

- `0x006E` is not a first-stage bootstrap packet

## `Azrok.exe + 0x001D407F`

Observed when replaying state-1 `0x0003("Data\\Space\\Lobby")`.

Meaning:

- inside `0x005D4070`, reached from `0x00615610`

What it proved:

- state-1 `0x0003` is real and meaningful
- replaying it before the right object graph exists is unsafe

## `Azrok.exe + 0x001B6213`

Latest confirmed crash from WER.

Meaning:

- inside `FUN_005B61F0`
- instruction writes `mov [ecx+0xcb], eax`
- reached from the `0x0064` tail after the current-player null problem was
  partially addressed

What it likely proves:

- the current-player singleton problem was not the final blocker
- another runtime submanager under the `logic + 0x8` side is still missing or
  uninitialized
- this crash is deeper than the earlier `0x0021571E` crash and therefore marks
  real forward progress

## Practical Interpretation

Crash progression so far:

1. self entity missing
2. state-1 helper object missing
3. `0x006E` too early
4. state-1 `0x0003` too early
5. deeper `0x0064` submanager now missing

This progression is useful. Each later crash means the preceding blocker was
at least partially bypassed.
