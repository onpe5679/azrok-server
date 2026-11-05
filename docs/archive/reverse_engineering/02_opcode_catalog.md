# Opcode Catalog

## Server -> Client

Confirmed meanings:

- `0x0001`
  Disconnect / termination style signal. Sending this from the server is bad.
- `0x0002`
  Required trigger to move the client into the load/enter-space phase.
- `0x0003`
  Not a 1-byte ACK. It is `[flag][NUL-terminated path string]`, for example
  `Data\\Space\\Plaza` or `Data\\Space\\Lobby`.
- `0x0005`
  Auxiliary control packet. It is valid in the base handshake, but there is no
  explicit `case 0x05` in the state-1 switch at `0x613740`.
- `0x0007`
  Large setup blob. Current safe draft size is `0x1D8` bytes.
- `0x0010`
  Stat/resource initialization table.
- `0x0011`
  Another stat/resource initialization table.
- `0x0064`
  Mandatory state-1 self/init packet. This is the only confirmed inbound
  state-1 network packet that reaches `FUN_0050A840()`.
- `0x0065`
  Actor-list flush/finalize.
- `0x0066`
  Actor-list record ingestion with scene/action branches.
- `0x0068`
  Position/update record for actor-list or cached coords.
- `0x0069`
  Position commit / snap for an actor.
- `0x006B`
  Small mode toggle packet.
- `0x006D`
  Conditional state packet gated on local state.
- `0x006E`
  Ready/setup packet, but too early in current experiments.

## Client -> Server

Observed meanings:

- `0x0000`
  Initial hello packet.
- `0x0004`
  Character creation request.
- `0x0007`
  Setup request after `0x0002/0x0003`.
- `0x0016`
  Heartbeat.
- `0x0017`
  Post-setup request that likely asks for self/room entry completion.

## Important Structure Notes

### `0x0003`

Current format:

- `payload[0] = flag`
- `payload[1..] = "Data\\Space\\NAME\\x00"`

### `0x0007`

Current working assumptions:

- size must be `0x1D8`
- `+0x03` request-derived dword should be sane, not synthetic garbage
- `+0x0B` stat table should default to zero values
- `+0x134/+0x148` table area uses `0x00FF` empty sentinels

### `0x0064`

Current inferred layout:

- `+0x00` entry/state byte
- `+0x01` self actor id
- `+0x06` x
- `+0x0A` y
- `+0x12/+0x13` small appearance bytes
- `+0x14..+0x1A` clock block:
  `year(u16), month-1, day, hour, minute, second`
