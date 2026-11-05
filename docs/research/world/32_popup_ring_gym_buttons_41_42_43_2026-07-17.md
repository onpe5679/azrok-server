# Popup-ring Gym buttons 0x41/0x42/0x43 (2026-07-17)

This is a read-only Ghidra analysis of `Azrok_original.exe`. No executable or
process memory was changed.

> **Superseding correction:** an earlier revision of this note claimed that
> there was no native `case 0x42` handler. That was false. The immediate-`CMP`
> scan missed a compiler-generated switch. Caller-oriented decompilation found
> the real Gym popup consumer in `FUN_005E3EE0`, whose `ButtonQueue_Pop` call
> returns to `0x005E3F14` and whose switch explicitly handles `0x41`, `0x42`,
> and `0x43`.

## Registry entries and popup construction

`CPopupRingCommand` initialization is `FUN_005E1090 @ 0x005E1090`. It creates
all popup-ring buttons through `FUN_00518980 @ 0x00518980`.

| Button id | Bitmap family | Content/category key |
|---:|---|---:|
| `0x41` | `BtnPushUp[_0/_1].wis` | `0x73` |
| `0x42` | `BtnDumbbell[_0/_1].wis` | `0x73` |
| `0x43` | `BtnRopeSkipping[_0/_1].wis` | `0x73` |

The native construction path is:

```text
FUN_005E1090
  -> FUN_00518980(button id)
  -> FUN_0051ADD0(..., button id)
  -> CGameButton object +0x58 = button id

CGameButton hit test FUN_0051B1F0 @ 0x0051B1F0
  -> returns object +0x58 with hover/event state in the out parameter

ButtonQueue_Pop @ 0x004E031C
  -> pops a generic three-dword queued UI event
```

`FUN_005E6960 @ 0x005E6960` builds a popup ring for a selected world object.
It enumerates the object's action strings, searches the command registry for
an exact `(content key, CP949 action label)` match, and shows the matching
button. Thus popup construction is data-driven, but execution is not purely
data-driven: `FUN_005E3EE0` later consumes the queued button id through a
native switch.

The associated `CPopupRingCommand` vtable is at `0x006AB958`. Relevant slots:

| Slot target | Role |
|---|---|
| `FUN_005E1010` | deleting destructor |
| `FUN_005E1090` | registry/resource initialization |
| `FUN_005E3E40` | empty callback |
| `FUN_005E3E60` | UI teardown/reset |
| `FUN_005E3E90` | initialized-state check |

## Why the previous scan was not exhaustive

The earlier Ghidra pass scanned `0x00401000..0x006608EA` for direct
`CMP ...,0x41/0x42/0x43` instructions. The direct comparisons it found were
unrelated ASCII, coordinate, and stat-schema logic, so those individual
classifications were valid. The inference that no native handler existed was
not valid: a compiled switch need not have a direct immediate comparison for
each case.

This is the practical lesson from the correction: when a registry id is known,
follow the event consumer and decompile its switch instead of treating an
immediate-pattern scan as exhaustive handler coverage.

## Correct native Gym action boundary

`FUN_005E3EE0` is the native Gym popup consumer. Its
`ButtonQueue_Pop` call returns at `0x005E3F14`; this is also the reviewed caller
filter for Frida button injection.

The Gym cases map selected object IDs to local action codes:

| Popup | Selected object IDs | Local action codes |
|---:|---|---|
| `0x41` | `0xF6`, `0xF7` | `0x1B`, `0x1C` |
| `0x42` | `0xF8`, `0xF9`, `0xFA` | `0x0C`, `0x0D`, `0x0E` |
| `0x43` | `0xFB`, `0xFC`, `0xFD` | `0x1E`, `0x1F`, `0x20` |

Each selected branch calls `FUN_0055BDB0(action_code)`. The Dumbbell path is
therefore the explicit native `case 0x42` path:

```text
popup 0x42
  -> FUN_005E3EE0 (ButtonQueue_Pop return/caller 0x005E3F14)
  -> selected object 0xF8 / 0xF9 / 0xFA
  -> local action 0x0C / 0x0D / 0x0E
  -> FUN_0055BDB0
  -> local exercise/action state
```

This path does not call the Gym room loader and does not wait for a server echo
of C->S `0x0065`. Its later completion/state-save path must be analyzed and
captured separately; a guessed `0x0065` reward ACK is not justified.

## OutMapGym is a separate consumer

The Gym exit UI is a separate switch, not part of the exercise popup.
`OutMapGym` explicitly handles `case 0x5C`; the instruction after its
`ButtonQueue_Pop` call is `0x005DB4D4`. For dynamic input testing, the two
reviewed boundaries must remain distinct:

```text
Dumbbell action: button 0x42, target caller 0x005E3F14
Gym exit:        button 0x5C, target caller 0x005DB4D4
```

Conflating these consumers can make a synthetic event reach the wrong UI
state, just as an unfiltered queue injection can be consumed during startup.

## Room-entry packet correction

Gym room entry is a separate local-loader chain:

```text
FUN_006122C0(local room index 2)
  -> FUN_00530FE0(2) queues local room code 0x66 (Gym)
  -> FUN_005AB760(kind, direction, entry X, entry Y)
  -> C->S 0x0065
```

The observed ten-byte frame is:

```text
08 15 15 02 00 00 85 05 00 00
```

Its source-proven layout is `<BBII>`:

| Field | Value | Meaning |
|---|---:|---|
| kind | `0x08` | Gym |
| direction | `0x15` | entry direction/orientation |
| X | `0x215` | entry X |
| Y | `0x585` | entry Y |

The previous interpretation that treated `0x15` as the Gym kind was wrong.
C->S `0x0065` is the locally completed room-entry report; it is not the
Dumbbell click and is not an exercise-result request.

## Direct verification points

The corrected boundaries can be measured without patching the binary:

1. break at `FUN_0051B1F0` and confirm button id `0x42` on Dumbbell selection;
2. inspect `FUN_005E6960` and confirm the selected object's registry match;
3. break at `FUN_005E3EE0`, or inject only for caller `0x005E3F14`, and
   confirm `case 0x42` plus the `0xF8..0xFA` action mapping;
4. separately break at `FUN_006122C0`/`FUN_005AB760` during Gym entry and
   confirm `<08,15,0x215,0x585>`;
5. for the exit UI, observe `OutMapGym case 0x5C` at caller `0x005DB4D4`.

The useful server-side evidence for exercise restoration begins at the actual
completion/save packet, not at the superseded no-native-handler theory and not
at a direction-confused `0x0065` packet.
