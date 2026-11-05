# Static local-room loader and opcode contract audit (2026-07-17)

This note records a read-only Ghidra pass over `Azrok_original.exe` through
the local headless bridge (`127.0.0.1:8193`).  No executable bytes and no
live-process memory were changed.  It complements research notes 33--36 and
is deliberately conservative about server replies: a native client path is
not treated as a network contract unless the sender and wire layout are
identified.

## 1. The complete local-loader chain

`FUN_006122C0(this, local_index)` is the local room/content continuation.  For
all values other than its special OX branch (`local_index == 0x0C`) it first
selects the destination coordinates, queues the local loader with
`FUN_00530FE0(local_index)`, and then queues the corresponding room code.
The client performs `level_load` and its room initializer before the room
membership report is emitted.  The network call is therefore a report of a
completed local selection, not a self-client room-load acknowledgement.

`FUN_00530FE0` has this direct switch:

| Local index | Queued post-load code | `FUN_0050A0F0` level target |
|---:|---:|---|
| 0 | `0x64` | `room.wmb` (PatHouse/base) |
| 1 | `0x65` | `playroom.wmb` |
| 2 | `0x66` | `gym.wmb` |
| 3 | `0x67` | `magic.wmb` |
| 4 | `0x68` | `cook.wmb` |
| 5 | `0x69` | `shop.wmb` |
| 6 | `0x6A` | `library_1.wmb` |
| 9 | `0x6B` | `pet.wmb` |
| 10 | `0x6D` | `ground.wmb` |
| 12 | `0x6F` | `OXQuiz.wmb` |
| 13 | `0x64` | Hansol/Plaza route (`hansol.wmb` is selected by code 11) |

Indices 7, 8 and 11 have no initialized `local_c` case in this function;
they must not be presented as valid direct inputs to `FUN_00530FE0` without a
caller-specific precondition.  Lobby (`0x6C`) and Hansol (`0x6E`) can still be
queued by other code paths in `FUN_0050A0F0`.

`FUN_0050A0F0` confirms the destination-side switch:

* codes `0x00`, `0x01`--`0x06`, `0x08`, `0x09`, and `0x0A` call `level_load`
  for the base/local rooms, lobby, pet, and ground;
* code `0x0B` is a flag-gated transition; when `gm+0x31C71 != 0` it loads
  `hansol.wmb`, queues `0x6E`, and clears the flag, otherwise it only queues
  the local `0x0B` event;
* code `0x0C` loads `OXQuiz.wmb` and queues `0x6F`;
* codes `0x64`--`0x6F` call `FUN_0050B400(code)`, which invokes the
  room-specific initializer.

The post-load phase writes in `FUN_0050A0F0` are also direct evidence of the
state boundary: `0x64` and `0x65`--`0x6A` end at phase `2`; pet (`0x6B`) uses
phase `0`, lobby (`0x6C`) phase `1`, ground (`0x6D`) phase `2`, Hansol (`0x6E`)
phase `4`, and OX (`0x6F`) phase `5`.

`FUN_0050B400` dispatches the normal local initializers as follows:

| Post-load code | Initializer | Final content builder |
|---:|---|---|
| `0x65` | `FUN_005318C0` | `FUN_00548000` (playroom) |
| `0x66` | `FUN_00531B10` | `FUN_00548B10` (gym) |
| `0x67` | `FUN_00531D60` | `FUN_00549650` (magic) |
| `0x68` | `FUN_00531FB0` | `FUN_00549EF0` (cook) |
| `0x69` | `FUN_00532200` | `FUN_00547C70` (shop) |
| `0x6A` | `FUN_00532470` | `FUN_0054AC20` (library) |

The five-stage initializers and these builders are client-local.  Their stat
lookups and descriptor writes are covered by research 43; they do not justify
an invented reward/ACK packet.

## 2. Direction-specific client senders

The following functions were decompiled directly.  The payload sizes are the
literal lengths passed to the common send helper (`FUN_005AB6A0`), not inferred
from packet captures.

| Sender | Direction/opcode | Exact payload | Native producer and proven role |
|---|---|---|---|
| `FUN_005AB760` | C->S `0x0065` | `<BBII>` (10 B) | `FUN_006122C0`; local room kind, direction, entry X/Y |
| `FUN_005AB7B0` | C->S `0x0066` | `<BIIII B>` (22 B) | `FUN_0061A420`, `FUN_0061B510`, `FUN_0061BCF0`; movement/position report |
| `FUN_005AB830` | C->S `0x0067` | `<BII I H>` (15 B) | `FUN_00619900`; stop/arrival/action report |
| `FUN_005AB890` | C->S `0x0069` | one byte | `FUN_00615180`; Plaza chair index after `c_trace`/`tex_name` match |
| `FUN_005AB8D0` | C->S `0x006A` | empty | `FUN_0061B510` actor-state branch; role is not a local-room reward |
| `FUN_005AB900` | C->S `0x0018` | three bytes | `FUN_005B2970`; selector/action state, exact gameplay meaning pending |
| `FUN_005AB950` | C->S `0x006C` | `<I>` (4 B) | `FUN_005CE8E0` E/community toggle and `FUN_005FDAB0` UI event |

The observed Gym frame `08 15 15 02 00 00 85 05 00 00` consequently decodes
as `kind=0x08` (Gym), `direction=0x15`, `x=0x215`, `y=0x585`.  The second
byte `0x15` is **not** a room kind.  Any server room classifier must keep
`0x08` as Gym and treat `0x15` as the direction/orientation field.  This is a
source-level bookkeeping correction for implementations that previously
labelled `0x15` as Gym.

The opposite-direction handlers remain separate contracts.  In particular,
S->C `0x0065` flushes remote actors, S->C `0x0066` consumes 0x1A-byte remote
actor records, and S->C `0x006C` consumes a six-byte remote-actor field update;
none is a direct echo of the C->S forms above.

## 3. Local popup/content actions are not native ACK waits

`FUN_005E3EE0` handles the data-driven popup command groups.  For Gym popup
IDs `0x41`, `0x42`, and `0x43`, it validates the selected object/stat gate and
calls `FUN_0055BDB0` with local action codes (`0x1B`/`0x1C`, `0x0C`--`0x0E`,
and `0x1E`--`0x20`, respectively).  `FUN_0055BDB0` only resets local action
descriptors/animation state and queues local events.  The same shape applies
to the Playroom, Magic, Library, and Cook popup groups.  There is no direct
call to the network sender family in this native popup continuation.

This proves a local content boundary, not that every script callback is
network-free: an indirect script/native callback could still send later.  A
real single-action capture is required before adding a server result.  In
particular, the one observed C->S `0x0065` in the Gym session is the room
membership report emitted by `FUN_006122C0`; it is not a dumbbell reward ACK.

Shop is a separate boundary.  `FUN_0055A650` creates the local character/NPC
models and `FUN_00565CD0` supplies the `bingbing` model set.  The shop builder
contains no `FUN_005A49B0` stat gate, but this static setup does not identify a
purchase request or result packet.  Those must be captured from one real
selection before implementing a response.

## 4. Implementation consequences and open evidence

1. Keep the no-patch local-room path client-driven.  The server should accept
   C->S `0x0065` as room membership and relay only real peer state; it should
   not send a self ACK to make the local WMB load.
2. Correct room bookkeeping to parse `<BBII>` as `(kind,direction,x,y)`; Gym
   is kind `0x08`, not `0x15`.
3. Translate C->S movement/action records into direction-correct remote actor
   packets for peers.  Do not byte-echo `0x0066`/`0x0067`.
4. Treat `0x0069`, `0x006A`, `0x0018`, and `0x006C` as separate actor/UI
   contracts.  Their presence in local-room code is not evidence of a room
   content reward.
5. The remaining evidence needed for full gameplay is dynamic: one clean
   action in each room (Playroom, Gym, Magic, Cook, Library, Shop), with the
   first new C->S sender and any subsequent inbound state correlated to the
   local popup/action code.  Until that evidence, do not synthesize inventory,
   stat, exercise, recipe, magic, or shop purchase replies.

