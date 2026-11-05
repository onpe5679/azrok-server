# Local-room static continuations and server boundaries (2026-07-17)

This note extends the runtime matrix with the native continuation functions
for Playroom, Library, Gym, Magic, Cook, and Shop. Analysis was read-only;
neither the executable nor process memory was patched.

## Shared loader and initialization chain

```text
popup/content selection
  -> FUN_006122C0(local room index)
  -> FUN_00530FE0(local room index)
  -> GameManager_DispatchRoomCode @ 0x0050A0F0
  -> level_load(room WMB)
  -> GameManager_ExecuteRoomInit @ 0x0050B400
  -> room-specific five-stage initializer
  -> phase global +0x31792 = 2
```

The client performs this chain locally. `C->S 0x0065` is emitted after local
selection/load staging and is a room-membership report, not a content ACK.

| Room | Local index | WMB | Post-load code | Five-stage init | Initial local queue/event |
|---|---:|---|---:|---|---:|
| Playroom | `0` | `playroom.wmb` | `0x65` | `FUN_005318C0` | `0x41B` via `FUN_00530890` |
| Library | `1` | `library_1.wmb` | `0x6A` | `FUN_00532470` | `0x420` via `FUN_00530D70` |
| Gym | `2` | `gym.wmb` | `0x66` | `FUN_00531B10` | `0x41C` via `FUN_005309B0` |
| Magic | `3` | `magic.wmb` | `0x67` | `FUN_00531D60` | `0x41D` via `FUN_00530AA0` |
| Cook | `4` | `cook.wmb` | `0x68` | `FUN_00531FB0` | `0x41E` via `FUN_00530B90` |
| Shop | `5` | `shop.wmb` | `0x69` | `FUN_00532200` | `0x41F` via `FUN_00530C80` |

Each initializer has the same five-stage shape: base room state, entity/world
creation, camera/vector setup, shared scene UI, then the room-specific content
descriptor builder. The final builders are the most useful breakpoints for
proving that a room is initialized past its loading screen.

## Popup command map by content key

`CPopupRingCommand` initialization `FUN_005E1090` defines 58 data-driven
commands. `FUN_005E6960` matches `(content key, CP949 action label)`; there is
no native per-button switch.

| Content area | Key | Popup ids and labels |
|---|---:|---|
| Playroom | `0x71` | `0x31` 저글링, `0x32` 요요, `0x33` 덤블링, `0x34` 딸랑이 |
| Magic | `0x72` | `0x3E` 매직클론, `0x3F` 퍼니쉴드, `0x40` 에어훅 |
| Gym | `0x73` | `0x41` 팔굽혀펴기, `0x42` 아령, `0x43` 줄넘기 |
| Library | `0x74` | `0x44` 독서 |
| Library level | `0x75` | `0x45` 초급, `0x46` 중급, `0x47` 고급 |
| Cook set A | `0x76` | `0x48` 토스트, `0x49` 베이컨구이, `0x4A` 삶은계란, `0x4B` 샌드위치, `0x4C` 국수 |
| Cook set B | `0x77` | `0x4D` 오믈렛, `0x4E` 크로아상, `0x4F` 핫케익, `0x50` 스파게티, `0x51` 볶음밥 |
| Cook set C | `0x78` | `0x52` 소시지그릴, `0x53` 스프, `0x54` 샐러드, `0x55` 비빔밥, `0x56` 김밥 |

Shop has no entry in these `0x71..0x78` popup groups. It uses its dedicated
room objects/UI after `FUN_00532200`; treating it as another popup-ring room
would miss its inventory/selection boundary.

## Room-specific content builders and stat gates

All six builders populate local 0x10C-byte content descriptors through
`FUN_00547BF0`. These are local world/action records, not packets.

| Room | Content builder | Stat ids read through `FUN_005A49B0` | Static effect |
|---|---|---|---|
| Playroom | `FUN_00548000` | `0x22,0x23,0x24`, then `3,5` thresholds | chooses base/unlocked play object variants |
| Library | `FUN_0054AC20` | `0x1E`, then `7,5` thresholds | chooses reading/level variants |
| Gym | `FUN_00548B10` | `0x1F,0x20,0x21`, then `3,5` thresholds | chooses exercise object variants |
| Magic | `FUN_00549650` | `0x25,0x26,0x27` | chooses magic object variants |
| Cook | `FUN_00549EF0` | `0x28..0x2C`, `0x31..0x35`, `0x3A..0x3E`, then `7,5,4` | chooses recipes and progression variants |
| Shop | `FUN_00547C70` | none in the builder | creates sparse shop descriptors; dedicated shop/NPC setup applies |

The builders' room selector fields are also distinct: Playroom `1`, Gym `2`,
Magic `3`, Cook `4`, Shop `5`, Library `6`. This matches the local room index
family and is a useful memory/breakpoint discriminator.

Important consequence: initial playable object availability is determined
from local stat state before any room-specific server response. A malformed or
stale initial stat bag can select the wrong variants even when the WMB loaded
successfully.

## Server boundaries: proven versus still unknown

### Proven server responsibilities

1. **Initial persistent state:** `S->C 0x0007` imports the stat values later
   queried by `FUN_005A49B0`. The server must preserve the client schema/wire
   order and avoid replaying a second bootstrap bundle during room init.
2. **Room membership:** accept C->S `0x0065 <BBII>`, record wire room kind and
   entry pose, remove the client from the prior room, and rebuild only real
   non-self rosters. Empty S->C `0x0065` is a roster flush, not a self ACK.
3. **Movement/action presence:** accept C->S `0x0066` and `0x0067`, update
   authoritative actor state, and translate for peers. Never byte-echo them as
   opposite-direction packets.
4. **Shop/equipment persistence:** the already recovered C->S `0x000C`
   11-byte changed-slot snapshot belongs to selection/equipment state. Accept
   and persist it; do not echo it as the different 7-byte S->C `0x000C` form.

### Not yet proven and must be captured

- No static native path proves that popup ids `0x31..0x56` require an immediate
  server ACK. Their ID dispatch crosses the generic popup/script boundary.
- The exact completion packet for experience gain, recipe consumption, magic
  reward, or exercise reward has not been correlated to a real action. Do not
  invent a reply from the stat ids used by the content builders.
- The exact Shop purchase request/result pair is not established by the room
  builder. Its dedicated UI must be traced from a real selection through the
  first C->S sender and the corresponding inbound result handler.

## Concrete validation breakpoints

For every room, first break on its five-stage initializer and final content
builder from the tables above. Then use these shared boundaries:

```text
0x005E6960  popup `(key,label)` match
0x0051B1F0  CGameButton id returned from object+0x58
0x006122C0  local room/script continuation
0x005AB760  C->S 0x0065 sender
0x005A49B0  stat lookup used to choose local content variants
0x00547BF0  local content descriptor insertion
```

For Shop additionally break at `FUN_00532200`, `FUN_00530C80`,
`FUN_0055A650`, and `FUN_00547C70`. `FUN_0055A650` performs the Shop-specific
world/NPC setup and calls `FUN_00565CD0`, which creates the local `bingbing`
model set; this is still local scene setup, not proof of a purchase protocol.

The decisive capture procedure is: clear the packet tail, perform exactly one
visible action, and correlate the first new C->S packet with the selected
popup key/id and the relevant room builder/stat lookup. Only then should a
server result packet be implemented.
