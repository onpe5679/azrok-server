# Plaza/Gym interaction direction split and progression boundary (2026-07-17)

This note combines live read-only packet evidence from the currently running
client with Ghidra decompilation. No executable or process memory was changed.
The most important correction is that opcodes `0x0065`, `0x0066`, and
`0x006C` have different wire layouts and meanings in each direction.

## Live boundary: the client is alive in Gym

The control panel reported:

```text
scene_opcode = 0x66 (102)
phase_31792  = 2
self_actor_id = 1
clients = 1
```

`GameManager_DispatchRoomCode @ 0x0050A0F0` maps local loader index `2` to
`gym.wmb`, post-load room code `0x66`, and phase 2. The client therefore did
not crash or remain in the Plaza loader; it completed the local Gym load.

The live capture `captures/packets_20260717_081659.txt` then showed:

```text
08:21:33 C->S 0065 10B  08 15 15 02 00 00 85 05 00 00
08:22:31 C->S 006C  4B  00 00 00 00
```

Before Gym entry there were many `C->S 0x0066` 22-byte movement records and
occasional `C->S 0x0067` 15-byte arrival/action records. No second
`C->S 0x0065` was emitted after Gym entry in the observed interval.

## C->S 0x0065 is a room-change report

Sender: `FUN_005AB760 @ 0x005AB760`.

Wire layout is exactly `<BBII>` (10 bytes):

| Offset | Type | Static role |
|---|---:|---|
| `+0x00` | `u8` | wire room kind |
| `+0x01` | `u8` | direction/orientation bucket |
| `+0x02` | `u32` | entry X |
| `+0x06` | `u32` | entry Y |

The main producer `FUN_006122C0 @ 0x006122C0` performs the room change locally
before sending the packet:

1. It calls `FUN_00530FE0(local_room_index)`.
2. That function enqueues the local loader/post-load room codes.
3. It maps the local room index to a wire room kind.
4. It sends `C->S 0x0065` with the kind, direction, and entry coordinates.

Relevant map recovered from the switch:

| Local loader index | Local room | C->S kind |
|---:|---|---:|
| `0` | playroom | `1` |
| `1` | library | `6` |
| `2` | **gym** | **`8`** |
| `3` | magic | `9` |
| `4` | kitchen | `7` |
| `5` | shop | `0x0B` |
| `6` | ground | `0x0A` |
| `0x0B` | magic-like mapped branch | `3` |
| `0x0C` | cook-like mapped branch | `4` |

The live packet decodes as kind `8`, direction `0x15`, X `0x215`, Y `0x585`,
which exactly agrees with the observed Gym scene.

Current server gap: `azrok_server.py` has no C->S `0x0065` branch, so this
valid room-change report falls through to unknown/log-only. A packet-faithful
room server should update the client's room membership, flush the previous
remote roster, and send the new room's non-self roster. For a single-client
room, no record-bearing S->C `0x0066` is needed unless real non-self actors
exist. **Superseded by doc 51:** an empty **S->C** `0x0065` is not a safe
active-Plaza roster marker. It tears down the fixed self actor as well as the
remote list, and the active minimap then faults at `0x005F3AF4`. It is also
not a required room-change acknowledgement.

There is no post-send wait in `FUN_006122C0`. Immediately after
`FUN_005AB760` returns, the client continues this local completion chain:

```text
FUN_0050D5D0()        clear remote actor roster locally
FUN_00530350()
FUN_0053A500()
FUN_00508F40()
FUN_00594100(0)       global +0x163E4 = 0
FUN_005E7F20(3)       global +0x31792 = 3 (transition phase)
FUN_00509C20()
FUN_005D85F0(room)    global +0x6D8 = local room index
```

`HandleS2C_0065_FlushRemoteActors @ 0x00615B20` calls `FUN_0050D5D0()`, but
doc 51's Ghidra re-check proves that routine clears `base+0x35C20` (self)
before the remote list. Therefore an empty S->C `0x0065` cannot be used as a
live roster marker or as the missing signal that advances the self client.

This omission does not explain failure to load Gym: the client already loaded
Gym locally before it sent the report. It can explain missing room membership,
remote occupants, and later server-authoritative room features.

## C->S 0x0066 and 0x0067 are local motion/action reports

`FUN_005AB7B0 @ 0x005AB7B0` serializes C->S `0x0066` as 22 bytes:

```text
u8 direction_or_angle
u32 current_x
u32 current_y
u32 target_x
u32 target_y
u32 duration_or_tick
u8 movement_flag
```

The producers at `0x0061A420`, `0x0061B510`, and `0x0061BCF0` build these
records while calculating movement vectors and timing. The repeated live
records are therefore evidence that movement and world hit processing were
running, not a repeated Gym transition request.

`FUN_005AB830 @ 0x005AB830` serializes C->S `0x0067` as 15 bytes:

```text
u8 direction_or_angle
u32 x
u32 y
u32 action_or_mode
u16 height_or_small_arg
```

Its producer `FUN_00619900 @ 0x00619900` emits it from a local actor action or
arrival path when actor field `+0x332 == -1`.

The current server has no C->S `0x0066` or `0x0067` handlers. In a multiplayer
implementation they should update authoritative position/action state and be
translated into the appropriate **S->C** remote-actor update family for other
clients. They should not be echoed byte-for-byte because the opposite
direction uses different layouts.

## C->S 0x006C is an E/community target request, not S->C 0x006C

Sender: `FUN_005AB950 @ 0x005AB950`, layout `u32 actor_id_or_zero`.

The live zero payload is explained by the exact input path:

```text
FUN_00535660 @ 0x00535660
  -> VK_E release edge
  -> FUN_005CE8E0 @ 0x005CE8E0
  -> if current room code == 0x6E, send self actor id
     else send 0
  -> FUN_005AB950(0)
  -> C->S 0x006C [00 00 00 00]
```

`FUN_005CE8E0` also toggles a local UI flag at `this+0x2BD`. On the first
activation it sets the flag and sends the request. On the second activation it
closes/toggles the UI locally and does not need another request.

This means the 08:22:31 packet was caused by the E/community UI while in Gym,
not by a door transition. If that overlay is the visible point at which play
appears stuck, pressing E once more is a safe local discriminator: the close
branch should run without a network reply. A genuine Gym door/portal selection
should instead reach `FUN_006122C0` and emit a second C->S `0x0065`.

Current server gap: C->S `0x006C` also falls through to unknown/log-only. The
static client proves only that it is a target/general-community request; the
exact authoritative list/profile reply is not yet recovered. Do not echo its
four bytes as S->C `0x006C`.

## Opposite-direction meanings (do not conflate them)

### S->C 0x0065

`HandleS2C_0065_FlushRemoteActors @ 0x00615B20` has no payload and calls
`FUN_0050D5D0` to clear the current remote-actor roster. A controlled empty
probe was safe and externally inert in a one-client session.

### S->C 0x0066

`HandleS2C_0066_BatchRemoteActorSpawn @ 0x00615B50` consumes an array of
`0x1A`-byte records:

| Offset | Type | Meaning |
|---|---:|---|
| `+0x00` | `u8` | record kind |
| `+0x01` | `u32` | actor id |
| `+0x05` | `u8` | species |
| `+0x06` | `u8` | subtype |
| `+0x07` | `char[13]` | name |
| `+0x14..+0x17` | `u8[4]` | appearance |
| `+0x18,+0x19` | `u8,u8` | selector pair (`0xFF` skips) |

Records matching the authoritative self id are ignored. This packet creates
or updates **non-self actors** and finalizes the remote list; it is not a Gym
content-completion acknowledgement.

### S->C 0x006C

`HandleS2C_006C_UpdateActorStateFields336_33A @ 0x00615410` consumes six bytes:

```text
+0x00 u8  actor field +0x336
+0x01 u8  actor field +0x33A / state (<2 is accepted)
+0x02 u32 actor id
```

It explicitly ignores the self actor. For a real remote actor, state `<2`
updates the two fields and raises UI/action event `0x30`; state `>=2` resets
the remote actor's `+0x32E/+0x332/+0x336/+0x33A` interaction fields. It cannot
unlock the current self actor or Gym progression when targeted at self.

## Plaza chair interaction (separate from Gym)

The actual Plaza world-click path is also direction-specific:

```text
Hansol_PerFrameUpdate @ 0x00613470
  -> FUN_00615090 (left-button edge and three screen regions)
  -> FUN_00615180 (world ray trace)
  -> compare tex_name against PLAZA_CHAIR_0.MDL .. PLAZA_CHAIR_5.MDL
  -> C->S 0x0069 [chair_index]
  -> optimistic local actor+0x336 = chair_index
```

The current server has no C->S `0x0069` branch. The most likely authority pair
is S->C `0x006B` for the requesting self's state and S->C `0x006C` for remote
observers, but this mapping remains an inference until a real-server capture
or controlled multi-client trace proves it.

## C->S 0x0017 is not the Gym/Plaza click packet

`FUN_0059DCD0 @ 0x0059DCD0` serializes six bytes `<BBI>`; the captured form is
`07 01 00 00 00 00`. It is slot `+0x14` of the `CJSLogic` vtable, and native
xrefs reach it through the script binding rather than a Plaza mouse handler.
Historical captures place it after the post-creation `C->S 0x0001`, so the
strong interpretation remains late readiness/status transition, not a chair,
Gym, or door click.

The present server's `0x0017` handler contains a separate hazard: it increments
`post_0017_repeat_count` from zero and sends successful S->C `0x006E[00,00]`
while `count <= 3`. Consequently even the first `0x0017` takes that branch,
despite the comment saying "Repeated". In the now-proven Plaza route that
packet queues OX. Plaza-safe behavior is log/state accounting only unless a
separately proven late reply is required.

## Ranked progression hypotheses and read-only checks

1. **Highest confidence: no Gym exit/portal event occurred.** There is no
   second C->S `0x0065` after Gym entry. Break on `FUN_006122C0` and
   `FUN_005AB760`; click the intended door. If neither fires, the issue is
   local hit-test/collision/UI state, not a missing server room reply.
2. **High confidence: the E/community overlay was activated.** Break on
   `FUN_005CE8E0`; pressing E again should take its local close branch. Then
   retry the door and watch for C->S `0x0065`.
3. **Medium confidence: server room membership is incomplete.** On the next
   C->S `0x0065`, record `<kind, direction, x, y>` and update the server-side
   room membership. Never answer it with empty S->C `0x0065`; use peer-only
   `0x0066+0x0068` upserts after state-1 Plaza admission. Do not synthesize a
   self S->C `0x0066`.
4. **Lower for single-client progression:** ignored C->S `0x0066/0x0067`
   movement reports. They matter for authority/multiplayer replication, but
   the client demonstrably moved and loaded Gym without their acknowledgement.
5. **Rejected shortcut:** echoing C->S `0x006C` as S->C `0x006C`. The wire
   lengths and semantics differ, and the inbound handler ignores self anyway.
