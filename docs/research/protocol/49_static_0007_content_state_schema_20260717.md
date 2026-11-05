# Static bootstrap schema behind local-room content (2026-07-17)

This is a read-only Ghidra pass over `Azrok_original.exe` (headless bridge
`127.0.0.1:8193`).  It records what the local-room builders actually consume
from the initial state packets.  It does not prescribe invented gameplay
values and did not modify the executable or a live process.

## `S->C 0x0007` is a complete setup blob

`HandleS2C_0007_LoadSetupBlob @ 0x0059E330` reads the following fields before
normal room code can query them.  The maximum touched offset is `0x1D7`, so a
payload shorter than `0x1D8` is incomplete even if the login screen appears:

| Offset | Size | Consumer / role |
|---:|---:|---|
| `0x00` | 1 | setup status byte |
| `0x01` | 1 | character/species selector |
| `0x02` | 1 | evolution/stage selector |
| `0x03` | 4 | packed date/time or seed input |
| `0x07` | 4 | setup/state dword |
| `0x0B` | `0x46 * 2` | 70 stat words, passed through `Stats_StoreClampedValue` |
| `0x97` | `0x21` | keyed byte list group `0x21` |
| `0xB8` | `0x0F` | keyed byte list group `0x0F` |
| `0xC7` | `0x14` | keyed byte list group `0x14` |
| `0xEA` | `0x26` | keyed byte list group `0x26` |
| `0x110` | 3 | keyed byte list group `3` |
| `0x113` | `0x0A` | keyed byte list group `10` |
| `0x11D` | 8 | keyed byte list group `8` |
| `0x125` | `0x0B` | 11 domain/effect bytes emitted immediately |
| `0x131` | 1 | keyed byte list group `1` |
| `0x134` | `10 * 2` | runtime-row kind/type values |
| `0x148` | `10 * 2` | runtime-row auxiliary values |
| `0x15C` | `10 * 4` | runtime-row values |
| `0x184` | 8 | mode-pair kind bytes |
| `0x18C` | `8 * 4` | mode-pair values |
| `0x1AC` | `4 * 10` | four domain banks, 10 bytes each |
| `0x1D4` | 4 | domain selector vector |

The handler imports the four domain banks, writes all 70 stat words, imports
the keyed groups, emits the 11 `0x125` bytes as local effects, and compacts
the ten runtime rows.  A row kind survives if it is `< 6` or exactly `0xFF`;
all other kinds are dropped and padded with `0xFF`/zero.  This is why all-zero
or all-FF test data can leave room UI labels visible while yielding empty or
locked content: the client is consuming a structured setup table, not merely
waiting for a room ACK.

`Stats_StoreClampedValue` is indexed `0..0x45`, and
`FUN_005A49B0` reads the same stat cache for IDs `0..0x46` (with the special
level/energy handling for ID 9).  The local room builders use these values:

* Playroom: `0x22`, `0x23`, `0x24`, then threshold values `3` and `5`;
* Library: `0x1E`, then threshold values `7` and `5`;
* Gym: `0x1F`, `0x20`, `0x21`, then threshold values `3` and `5`;
* Magic: `0x25`, `0x26`, `0x27`;
* Cook: `0x28..0x2C`, `0x31..0x35`, `0x3A..0x3E`, then thresholds `7`, `5`, `4`.

These IDs are direct static dependencies of the local builders, not proof of
any corresponding server reward packet.  Initial values should be made
coherent with the authoritative state design before trying to unlock every
variant.

## `S->C 0x000A` is a grouped keyed registry

`HandleS2C_000A_StatRegistry @ 0x0059ECA0` consumes 70 little-endian `u16`
values split into seven groups.  The exact offsets and counts are:

| Group | Payload offset | Count |
|---:|---:|---:|
| 0 | `0x00` | `0x16` (22) |
| 1 | `0x2C` | 6 |
| 2 | `0x38` | 5 |
| 3 | `0x42` | `0x20` (32) |
| 4 | `0x82` | 3 |
| 5 | `0x88` | 1 |
| 6 | `0x8A` | 6 |

For each entry the handler looks up a baked key table (`DAT_006DFB80` and
related tables) and calls `StatRegistry_WriteGroupedKeyValue(group,key,val)`.
The key, not the array position alone, is what later content lookups use.
Sending a short payload or values in an incorrect group can therefore leave
the room descriptor present but its unlock/variant registry empty.

## `S->C 0x000B` is only the XP curve

`HandleS2C_000B_XPCurve @ 0x0059EEE0` forwards the payload to
`XPCurve_StoreValues`.  It does not populate the 70 stats or the keyed
registry and is not a local-room content ACK.

## Practical server boundary

The server should preserve the full `0x0007`/`0x000A` shape and only then tune
values to fill empty inventory/status/room labels.  A room WMB load can be
successful with sparse data, but the five-stage builders will select locked
or sentinel descriptors when the stat cache, keyed registry, or runtime-row
tables are empty.  Values for items, quests, rewards, and messages still need
their own direct wire evidence; do not repurpose the room loader or fabricate
an ACK from these setup tables.

