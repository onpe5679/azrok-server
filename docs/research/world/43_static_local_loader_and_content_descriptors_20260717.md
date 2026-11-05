# Static local-room loader and content descriptor evidence (2026-07-17)

This note records a fresh read-only Ghidra headless pass over
`/Azrok_analyzed.exe`.  No executable bytes or live process memory were
modified.  The Ghidra MCP bridge had no running GUI instance at the time of
this pass, so the same analysed project was queried through
`analyzeHeadless.bat` and `DecompileAddresses.java`; the raw outputs are kept
in:

- `ghidra_temp/decompile_room_builders_new.log`
- `ghidra_temp/decompile_room_init_support_new.log`
- `ghidra_temp/decompile_remaining_room_init_new.log`

## 1. Local index to WMB/post-load mapping

`FUN_00530FE0(this, local_index)` stores the requested local index and pushes a
post-load room code.  The direct switch recovered from the binary is:

| Local index | Post-load code | `level_load` target (dispatch case) | Room role |
|---:|---:|---|---|
| 0 | 100 (`0x64`) | `room.wmb` | PatHouse/base room |
| 1 | `0x65` | `playroom.wmb` | Playroom |
| 2 | `0x66` | `gym.wmb` | Gym |
| 3 | `0x67` | `magic.wmb` | Magic |
| 4 | `0x68` | `cook.wmb` | Cook/kitchen |
| 5 | `0x69` | `shop.wmb` | Shop |
| 6 | `0x6A` | `library_1.wmb` | Library |
| 8 | `0x6C` | `lobby.wmb` | Lobby |
| 9 | `0x6B` | `pet.wmb` | Pet room |
| 10 | `0x6D` | `ground.wmb` | Ground/outmap |
| 12 | `0x6F` | `OXQuiz.wmb` | OX quiz |
| 13 | `0x64` | `hansol.wmb` | Hansol/Plaza route |

`GameManager_DispatchRoomCode @ 0x0050A0F0` performs the corresponding
`level_load` and pushes the local post-load code.  For indices 1--6 the calls
are:

```text
index 1 -> level_load("playroom.wmb") -> queue 0x65
index 2 -> level_load("gym.wmb")      -> queue 0x66
index 3 -> level_load("magic.wmb")    -> queue 0x67
index 4 -> level_load("cook.wmb")     -> queue 0x68
index 5 -> level_load("shop.wmb")     -> queue 0x69
index 6 -> level_load("library_1.wmb")-> queue 0x6A
```

`GameManager_ExecuteRoomInit @ 0x0050B400` then dispatches the post-load code
to a room-specific initializer.  This is a client-local path; no socket send
or inbound server response appears in either function.

## 2. Five-stage initializers and final content builders

Each normal local-room initializer runs five stages, calls `engine_frame()`
between stages, and closes the loading screen at the end.  The final stage
calls the room's content descriptor builder:

| Room | Initializer | Final builder | Local descriptor selector written at `descriptor + 0x10C` | Stat gates read |
|---|---|---|---:|---|
| Playroom | `0x005318C0` | `0x00548000` | 1 | `0x22`, `0x23`, `0x24`, then `3`/`5` thresholds |
| Library | `0x00532470` | `0x0054AC20` | 6 | `0x1E`, then `7`/`5` thresholds |
| Gym | `0x00531B10` | `0x00548B10` | 2 | `0x1F`, `0x20`, `0x21`, then `3`/`5` thresholds |
| Magic | `0x00531D60` | `0x00549650` | 3 | `0x25`, `0x26`, `0x27` |
| Cook | `0x00531FB0` | `0x00549EF0` | 4 | popup/effect ids `0x28..0x2C`, `0x31..0x35`, `0x3A..0x3E`, then `7`/`5`/`4` |
| Shop | `0x00532200` | `0x00547C70` | 5 | no `FUN_005A49B0` gate in the builder |

The selector values are written into the local 0x10C-byte world/action
descriptor.  They are not protocol fields.  A stat gate selecting a variant
therefore cannot be repaired by sending a guessed action ACK; the relevant
authoritative input is the initial persistent state (`S->C 0x0007`) and its
keyed registry (`S->C 0x000A`).

### Shop-specific boundary

Shop's five-stage initializer invokes `FUN_0055A650`, which calls
`FUN_00565CD0`.  The latter creates local `bingbing.mdl`,
`bingbing_L.MDL`, and `bingbing_R.MDL` entities and sets their local positions.
This proves that Shop's NPC/world setup is local.  It does not identify the
purchase request/result packet; that pair still requires one clean real
selection capture before adding a server response.

## 3. Descriptor reset and write contract

`FUN_0054C6C0` resets twenty descriptor slots by writing `0xFFFFFFFF` to each
slot's fields at `+0x108` and `+0x10C`, then calls `FUN_00547A80(0)`.  The common
writer `FUN_00547BF0(slot, name, value)` does exactly three local writes:

```text
descriptor + 0x008 : NUL-terminated name copy
descriptor + 0x108 : 0
descriptor + 0x110 : supplied value/descriptor id
```

The builders additionally add local sentinel/action descriptors with
`name="00"`, `value=0xFFFFFFFF`, and type/state values 2, 3, 4, or 5.  These
values are local scene bookkeeping and must not be serialized as synthetic
network packets.

## 4. Server boundary for full restoration

The static path narrows the implementation work:

1. To make Playroom, Gym, Magic, Cook, Library, and the local Shop scene load,
   the server must not invent a room ACK.  The client already selects the WMB,
   runs the five-stage initializer, and builds local content descriptors.
2. The server must provide coherent initial persistent state, because the
   builders query stats through `FUN_005A49B0`.  Keep `S->C 0x0007` indexed
   values and `S->C 0x000A` keyed registry values consistent; otherwise a
   valid room can still show locked/empty variants.
3. `S->C 0x000B` remains the XP curve table.  It is not a room-content ACK.
4. Shop purchase, exercise reward, cooking consumption, magic reward, and
   library/playroom progression remain **unproven** protocol boundaries.
   Capture the first real C→S sender and the matching inbound handler before
   implementing a reply.
5. The shared-room Hansol/Plaza path is separate: it is the route that
   promotes the dispatch mode and needs the room membership/remote-actor
   contracts already documented in research 40--42.

## 4A. Gym popup action boundary (static correction)

The Gym popup consumer was decompiled separately before treating the observed
client-to-server `0x0065` packet as an exercise-reward request.  In
`FUN_005E3EE0`, Gym popup IDs `0x41`, `0x42`, and `0x43` (content key `0x73`)
map the selected object IDs to local action codes:

| Popup | Selected object IDs | Local action codes |
|---|---|---|
| `0x41` | `0xF6`, `0xF7` | `0x1B`, `0x1C` |
| `0x42` | `0xF8`, `0xF9`, `0xFA` | `0x0C`, `0x0D`, `0x0E` |
| `0x43` | `0xFB`, `0xFC`, `0xFD` | `0x1E`, `0x1F`, `0x20` |

Each selected branch calls `FUN_0055BDB0(action_code)`.  That function resets
and updates local descriptor/animation state, then calls local queue/event
routines; no direct socket sender is present in the examined call path.  A
failed stat/availability gate maps to local action `0x1D`, also without a
network send.

This is direct static evidence that the Gym exercise controls are local action
dispatches.  It does not by itself prove that no indirect callback can later
emit a packet, so one clean dynamic capture remains useful.  Until that
capture exists, do **not** add a guessed server ACK or reward response for
`C->S 0x0065`.  The packet observed in the movement/session capture should
remain classified as a room/action report, as documented in research 36, not
as a confirmed exercise-reward request.

Supporting outputs:

* `ghidra_temp/decompile_popup_dispatch_xrefs_new.log`
* `ghidra_temp/decompile_popup_action_continuations_new.log`
* `ghidra_temp/xrefs_content_thunks_new.log`

The `FUN_0059DCD0` (`C->S 0x0017`) sender has no code xref from these popup
branches; the only found reference is a data/vtable reference.  Therefore the
static pass supplies no basis for inventing a `0x0017` gym reward packet.

## 5. Reproducible static command

The fresh builder pass used the existing analysed project and only emitted
decompiler text:

```text
B:\ghidra_12.0.4_PUBLIC\support\analyzeHeadless.bat \
  <home>\Documents\<project-dir>\Azrok_Plaza\ghidra_temp azrok_analysis \
  -process Azrok_analyzed.exe \
  -scriptPath <home>\Documents\<project-dir>\Azrok_Plaza\ghidra_scripts \
  -postScript DecompileAddresses.java \
  00530fe0 0050a0f0 0050b400 0054c6c0 \
  005318c0 00532470 00531b10 00531d60 00531fb0 00532200 \
  00548000 0054ac20 00548b10 00549650 00549ef0 00547c70 \
  0055a650 00565cd0
```

No patching, memory writes, or game input was used in this analysis pass.
