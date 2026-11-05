# Server Experiments

## Stable Handshake So Far

Current stable early handshake:

- `0x0002`
- `0x0003("Data\\Space\\Plaza")` or `Lobby`
- after client `0x0007`, send:
  - `0x0007`
  - `0x0005`
  - `0x0010`
  - `0x0011`

This consistently gets the client to the post-create loading phase.

## State-1 Experiment Timeline

### Phase 1

- Tried `0x0066/0x0065/0x0068/0x0069` with `opcode 100` skipped entirely.
- Result: no crash, but infinite loading.

### Phase 2

- Restored real `0x0064` handling.
- Immediate crash at `0x0021571E`.
- Root cause: current-player singleton entity missing.

### Phase 3

- Added null-entity guard so `0x0064` could survive the first dereference.
- Result: no immediate crash, but loading still incomplete.

### Phase 4

- Tried `0x006E`.
- Crash at `0x00216AD2`.
- Result: ruled out early `0x006E`.

### Phase 5

- Tried state-1 `0x0003` replay after forced state-1.
- Crash at `0x001D407F`.
- Result: ruled out early `0x0003` replay.

### Phase 6

- Added singleton self bootstrap inside the `0x0064` null guard by calling the
  local self-creation helpers.
- Result: crash moved deeper to `0x001B6213`.

## Current Runtime Patches in `azrok_server.py`

- dispatch flag bypass at `0x591DC7`
- state-1 opcode 100 null-entity guard at `0x615709`
- full `0x0064` draft currently sent on first `0x0017`
- follow-up bootstrap currently:
  - `0x0064`
  - `0x0065`
  - `0x0066`
  - `0x0068`
  - `0x0069`

## Why The Latest Crash Matters

The latest crash shows the new singleton bootstrap patch was not pointless.
It pushed execution beyond the previous entity-null fault and into a later
manager path. That is better than the older immediate `0x0064` crash.
