# Azrok Protocol Audit - Packet Layouts And Server Contract

Date: 2026-04-01
Source of truth: Ghidra decompilation of `Azrok.exe`

## 1. S->C packet layouts

### `0x0000` login lobby blob

Handlers:
- `HandleS2C_0000_LoadLobbySparseCache` @ `0x0059E070`
- `HandleS2C_0000_SelectLobbyEntryScene` @ `0x0050D0E0`

Verified structure:
- `+0x00` `u8 result_code`
- `+0x01` `u8 lobby_mode`
- `+0x56` `u8 sparse_count`
- `+0x57` sparse key array
- `+0xBB` sparse value array
- total blob copied locally: `0x183` bytes

Interpretation:
- sparse keys are `u16`
- sparse values are `u32`
- max sparse rows on wire: 50

### `0x0003` room/path payload

Handler:
- `HandleS2C_0003_StoreSpacePath` @ `0x0050D200`

Verified structure:
- `+0x00` `u8 mode_or_flag`
- `+0x01` NUL-terminated path/string payload

Evidence:
- The first byte is stored into `gm+0x31C63`.
- The remainder is forwarded as a pointer to two downstream consumers.

### `0x0004` calibration sample

Handler:
- `HandleS2C_0004_CalibrationSample` @ `0x0059DE50`

Verified structure:
- `+0x00` `u8 sample_kind`
- `+0x01` `u32 timestamp_ms`

Semantics:
- `sample_kind == 0x01` is the live sample path.
- After five samples, the handler mutates byte `0` to `0xFF`.
- State-0 common dispatch interprets `0xFF` as readiness-latched.

### `0x0005` post-load state

Handlers:
- `HandleS2C_0005_PostLoadState` @ `0x0059EBD0`
- `HandleS2C_0005_CommonWrapper` @ `0x0050CFF0`

Verified structure:
- `+0x00` `u8 status`
- `+0x01` `u8 subtype`
- `+0x02` `u32 state_value`

Observed subtype handling:
- `0x00`
- `0x12`
- `0x13`

Important dispatch detail:
- `DispatchInbound_ByClientMode` calls `HandleS2C_0005_PostLoadState` before the mode-specific/common dispatchers.
- Then, in state-0, the same packet can still hit `HandleS2C_0005_CommonWrapper`.

### `0x0006` reset local clock and seed

Handler:
- `HandleS2C_0006_ResetLocalClockAndSeed` @ `0x0059E1F0`

Verified structure:
- `+0x00` `u8 opcode_substatus`
- `+0x01` `u8 header_or_selector`

When `payload[0] == 0`:
- resets local timing and seed paths
- reapplies local archetype seed
- then emits `C->S 0x0007` through `FUN_005A4770`

Server contract:
- If the server ever sends `0x0006`, it must be ready to receive a new `C->S 0x0007`.

### `0x0007` setup blob

Handler:
- `HandleS2C_0007_LoadSetupBlob` @ `0x0059E330`

Verified touched layout:
- `+0x00` `u8 header_00`
- `+0x01` `u8 header_01`
- `+0x02` `u8 header_02`
- `+0x03` `u32 packed_seed_03`
- `+0x07` `u32 packed_clock_07`
- `+0x0B` `0x46 * u16 stat_words`
- `+0x97` `0x21` bytes
- `+0xB8` `0x0F` bytes
- `+0xC7` `0x14` bytes
- `+0xEA` `0x26` bytes
- `+0x110` `0x03` bytes
- `+0x113` `0x0A` bytes
- `+0x11D` `0x08` bytes
- `+0x125` `0x0B` local-effect bytes
- `+0x131` `0x01` byte
- `+0x134` `10 * u16 row_kind`
- `+0x148` `10 * u16 row_aux`
- `+0x15C` `10 * u32 row_value`
- `+0x184` `8 * kind bytes`
- `+0x18C` `8 * u32 tuple values`
- total touched size: `0x1D8`

Verified semantics:
- 70 stat words are written through clamping logic.
- The 11 bytes at `+0x125` are not passive filler; each is emitted through `DomainCode_EmitLocalEffect`.
- Runtime rows are compacted: only `row_kind < 6` or `row_kind == 0xFF` survive.
- The handler calls the same `+0x28` vtable transition hook used to continue loading.

Server contract:
- `+0x125` should use `0xFF` for "no-op" style empty slots, not `0x00`.
- `+0x1D4..+0x1D7` are later consumed as bootstrap selector bytes through `FUN_005AB2B0(0..3)`.

### `0x000A` grouped stat registry

Handler:
- `HandleS2C_000A_StatRegistry` @ `0x0059ECA0`

Verified total size:
- `0x96` bytes = 75 `u16` values

Verified wire groups and ids:
- Group 0, 22 values at `+0x00`:
  - ids `1,2,4,5,7,8,10,11,13,14,16,17,19,20,22,23,25,26,28,29,31,32`
- Group 1, 6 values at `+0x2C`:
  - ids `2002,2003,2005,2006,2008,2009`
- Group 2, 5 values at `+0x38`:
  - ids `2501,2502,2504,2505,2507`
- Group 3, 32 values at `+0x42`:
  - ids `1001..1032`
- Group 4, 3 values at `+0x82`:
  - ids `1500,1501,1502`
- Group 5, 1 value at `+0x88`:
  - id `3000`
- Group 6, 6 values at `+0x8A`:
  - ids `4000..4005`

Correction:
- The on-wire `0x000A` groups are narrower than the broader domain/category ranges seen elsewhere in the binary.

### `0x000B` XP curve

Handler:
- `HandleS2C_000B_XPCurve` @ `0x0059EEE0`

Verified layout:
- 31 `u16` values
- total size `62` bytes

### `0x0064` authoritative self placement

Handler:
- `HandleS2C_0064_ApplyAuthoritativeSelf` @ `0x00615650`

Verified layout:
- `+0x00` `u8 entry_kind`
- `+0x01` `u8 selector_0`
- `+0x02` `u8 selector_1`
- `+0x03` `u32 self_id`
- `+0x07` `u32 pos_x_raw`
- `+0x0B` `u32 pos_y_raw`
- `+0x0F` `u32 tail_dword`
- `+0x13` `u8 room_domain`
- `+0x18..+0x1A` 3-byte tail triplet
- total size `0x1B`

Accepted `entry_kind` values:
- `0x00`
- `0x0A`
- `0x0B`
- `0x14`

Important semantics:
- Receiving this packet first forces `dispatch_state = 1`.
- `entry_kind 0x0A` maps to local scene path `0x2E`.
- `entry_kind 0x0B` maps to local scene path `0x2F`.
- The handler closes the loading screen at the end.

Server contract:
- Do not send this packet during early state-0 bootstrap.
- Use it only after room loading is sufficiently complete.

### `0x0065` remote actor flush

Handler:
- `HandleS2C_0065_FlushRemoteActors` @ `0x00615B20`

Layout:
- empty payload

### `0x0066` remote actor batch spawn

Handler:
- `HandleS2C_0066_BatchRemoteActorSpawn` @ `0x00615B50`

Record size:
- `0x1A` bytes per actor

Verified fields:
- `+0x00` `u8 record_kind`
- `+0x01` `u32 actor_id`
- `+0x18` `u8 pair_left`
- `+0x19` `u8 pair_right`

Important semantics:
- `record_kind 0x0A` -> local scene path `0x2E`
- `record_kind 0x0B` -> local scene path `0x2F`
- Otherwise `pair_left != 0xFF` triggers a selector/pair update path

### `0x0068` remote actor state batch

Handler:
- `HandleS2C_0068_BatchActorState` @ `0x00615D50`

Record size:
- `0x18` bytes = 6 dwords

Verified fields:
- `+0x00` `u32 actor_id`
- `+0x04` `u32 arg_04`
- `+0x08` `u32 arg_08`
- `+0x0C` `u32 arg_0C`
- `+0x10` `u32 arg_10`
- `+0x14` `u32 state_gate`

Semantics:
- `state_gate == 0` -> short coord/update path
- otherwise -> full record application path

### `0x0069` actor action state

Handler:
- `HandleS2C_0069_ApplyActorActionState` @ `0x00615E70`

Layout:
- four dwords

Verified fields:
- `+0x00` `u32 actor_id`
- `+0x04` `u32 arg_04`
- `+0x08` `u32 arg_08`
- `+0x0C` `u32 action_gate_or_control`

### `0x006A` actor text payload

Handler:
- `HandleS2C_006A_ApplyActorTextPayload` @ `0x00615FF0`

Verified touched layout:
- `+0x00` `u8 text_kind`
- `+0x01` `u8 text_mode`
- `+0x02` `u32 actor_id`
- `+0x06` primary string
- `+0x15` secondary string

### `0x006B`, `0x006C`, `0x006D`

Handlers:
- `HandleS2C_006B_UpdateSelfStateField33A` @ `0x00615340`
- `HandleS2C_006C_UpdateActorStateFields336_33A` @ `0x00615410`
- `HandleS2C_006D_AdvanceActorField332Stage` @ `0x006154E0`

Verified use:
- `0x006B` updates self-only state byte `field33A`
- `0x006C` updates remote actor bytes `field336` and `field33A`
- `0x006D` advances actor field332 from `2` to `3` and pushes scene code `0x31`

### `0x006E` ready commit

Handler:
- `HandleS2C_006E_CommitReadyMode` @ `0x006169D0`

Verified layout:
- `+0x00` `u8 mode_selector`
- `+0x01` `u8 ready_gate`

Semantics:
- `ready_gate == 0` -> success/ready path, sets local ready flag at `+0x129B`
- `ready_gate != 0` -> failure popup/event path

### `0x006F`

Handler:
- `HandleS2C_006F_SetSelectorPair` @ `0x00616B20`

Layout:
- `+0x00` `u8 selector_index`
- `+0x01` `u8 selector_value`

### `0x0070`

Handler:
- `HandleS2C_0070_HandleLatchedDualForm` @ `0x00616860`

Dual form:
- short form when latch is clear: byte `1` plus word at `+2`
- full form otherwise: byte `0`, word at `+2`, dwords at `+4` and `+8`

### `0x0071`

Handler:
- `HandleS2C_0071_SynthesizeLocalFE` @ `0x00616510`

Semantics:
- only acts when `payload[0] == 0`
- synthesizes a local FE/UI text/effect path

## 2. C->S packets the server must be prepared to receive

### Proven by binary

- `C->S 0x0007`
  - emitted after `S->C 0x0002`
  - emitted after `S->C 0x0006`
  - transport helper: `FUN_005A4770`

- `C->S 0x0064`
  - emitted by `SendC2S_0064_LocalBootstrapStatus` @ `0x006130B0`
  - this is a client status/bootstrap report, not the same as inbound `S->C 0x0064`

### Proven by live protocol handling but still partly opaque in binary

- `C->S 0x0000` login hello
- `C->S 0x0001` transition/disconnect-style ack
- `C->S 0x0004` character creation
- `C->S 0x0008` state sync
- `C->S 0x0017` later follow-up/state packet
- `C->S 0x0019` outdoor transition request
- `C->S 0x0016` heartbeat

## 3. Server behavior rules derived from the binary

- Ignore repeated `C->S 0x0007` once the first bootstrap response has already been sent.
- Never blindly echo `C->S 0x0001`.
- Never confuse client `0x0064` with server `0x0064`; they are different directions and meanings.
- Avoid early `S->C 0x0064` because it flips dispatcher mode to state-1.
- If using `0x0006` or `0x0002`, expect the client to emit `0x0007` afterward.
- Use true `0x0004` sample packets with byte `0 == 1` if the goal is packet-faithful readiness latching.
