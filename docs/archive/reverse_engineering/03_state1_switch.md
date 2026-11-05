# State-1 Switch

## Dispatcher

State-1 packets are handled by:

- outer runtime handler: `0x594310`
- state-1 dispatcher: `0x613740`

Confirmed state-1 map:

- `0x0003 -> 0x00615610`
- `0x000C -> 0x006165B0`
- `0x0064 -> 0x00615650`
- `0x0065 -> 0x00615B20`
- `0x0066 -> 0x00615B50`
- `0x0067 -> 0x00615D00`
- `0x0068 -> 0x00615D50`
- `0x0069 -> 0x00615E70`
- `0x006A -> 0x00615FF0`
- `0x006B -> 0x00615340`
- `0x006C -> 0x00615410`
- `0x006D -> 0x006154E0`
- `0x006E -> 0x006169D0`
- `0x006F -> 0x00616B20`
- `0x0070 -> 0x00616860`
- `0x0071 -> 0x00616510`
- `1000 -> 0x006167E0`

There is no direct `case 0x05` in this switch.

## Priority Ranking

### Highest Priority

- `0x0064`
  Mandatory. It is the only confirmed state-1 inbound packet that reaches the
  loading close path through `FUN_0050A840()`.

### Medium Priority

- `0x0003`
  In state-1 it stores the string and flags through `0x005D4070`, but replaying
  it too early already caused a crash at `0x005D407F`.
- `0x0065`
  Low-risk actor-list finalize/reset.
- `0x0066`
  Important for actor-list scene/action setup, but it does not create the
  singleton current-player object used by `0x0064`.
- `0x0068`
  Useful for cached coords and actor placement. Also does not create the
  singleton current-player object.
- `0x0069`
  Stronger commit/snap candidate than `0x006E`. Safe in current experiments.

### Lower Priority

- `0x006B`
  Only a small mode toggle. It updates `0x006153E0` / `0x00527760` behavior,
  but there is no evidence that it directly closes loading.
- `0x006D`
  Gated by `FUN_00613690() == 2`, where `FUN_00613690` returns `*(obj+0x332)`.
  This is only useful if the local state has already reached that mode.
- `0x006E`
  Too early in current builds. It crashed in `0x00616AC0` because the target
  object was not ready.

## Important Comparisons

### `0x0003` vs `0x0005` in State 1

- `0x0003` has an explicit state-1 handler and does real work.
- `0x0005` has no explicit state-1 case in `0x613740`.

This is why state-1 `0x0003` is a meaningful candidate while state-1 `0x0005`
is a weak candidate.

### `0x006B` vs `0x006D` vs `0x006E`

- `0x006B` is lightweight and unlikely to be the primary missing load-complete
  event.
- `0x006D` is conditional on local state `+0x332 == 2`, so it is not an early
  bootstrap candidate.
- `0x006E` clearly does meaningful setup, but it is unsafe before additional
  internal objects exist.

## Current Best Read

The core problem is no longer "which extra packet exists at all." The core
problem is that `0x0064` still expects more internal state than our emulation
currently provides.
