# Queue event 0x042D is local click sound, not a door transition (2026-07-17)

This note correlates the clean PatHouse x32dbg hit at `0x0050FE80` with the
read-only Ghidra control flow. No binary or process-memory patch was applied.

## Captured return address

The captured first return address `0x005305F4` is inside
`FUN_005305D0 @ 0x005305D0`:

```c
void FUN_005305D0(u32 event_id, u32 mode)
{
    ButtonQueue_Push(event_id, mode, 0xFFFFFFFF);
}
```

At assembly address `0x005305E9`, the wrapper selects the `CGame` queue at
`this + 0x307A7`; `0x005305EF` calls the thunk leading to `0x0050FE80`; and
`0x005305F4` is the first instruction after that call. Consequently this
return address identifies the generic queue wrapper, not the higher-level
world object that produced the click.

## Exact 0x042D meaning

The consumer is `FUN_005363A0 @ 0x005363A0`. It pops the same
`CGame + 0x307A7` three-dword queue. When the second field is `1`, its switch
contains:

```text
case 0x042D:
    FUN_00515160("click.ogg", local_position, 100);
```

When the second field is `0`, the consumer follows the generic sound-stop
path instead. Thus the observed event is a local click/UI sound command. It is
not a network opcode, room id, door id, or content result.

The same switch provides useful negative controls:

| Queue event | Local sound/role |
|---:|---|
| `0x042D` | `click.ogg` |
| `0x048E` | `door_A.ogg` |
| `0x0491` | `outmap_enter.ogg` |
| `0x0492` | `outmap_on.ogg` |
| `0x0493` | `outmap_popup.ogg` |
| `0x0494` | `NPC_On_A.ogg` |
| `0x0495` | `NPC_Off_A.ogg` |

Therefore repeated `0x042D` hits after floor/object clicks prove only that
the generic local click feedback ran. They do not prove that a door hit-test,
NPC interaction, popup command selection, or room transition ran.

## All native 0x042D producers

An instruction scan found exactly three immediate `PUSH 0x42D` sites:

1. `FUN_00542B90 @ 0x00542B90` calls
   `FUN_005305D0(0x42D,1)`, then performs local current-room/UI follow-up.
2. `FUN_005E6960 @ 0x005E6960` emits `0x42D,1` when building the
   data-driven popup ring, before matching `(content key, action label)` and
   showing its action buttons.
3. `FUN_005E7130 @ 0x005E7130` is a small helper that emits
   `FUN_005305D0(0x42D,1)`.

Because all three converge on `FUN_005305D0`, the captured inner return
address alone cannot distinguish them.

## Next local action boundaries

For an actual content-object click, the expected continuation is:

```text
FUN_005E6960(key, screen_x, screen_y)
  -> local 0x042D click sound
  -> match `(key, CP949 action label)`
  -> show popup CGameButton(s)
  -> FUN_0051B1F0 returns selected popup button id
  -> script/content continuation
```

For an actual local-room transition, the useful proof remains:

```text
FUN_006122C0(local room index)
  -> FUN_00530FE0(index)
  -> local WMB load
  -> FUN_005AB760
  -> C->S 0x0065 <room kind, direction, X, Y>
```

The sound event `0x048E` may accompany a real door but is still only local
presentation. `FUN_006122C0`/`FUN_005AB760` are the decisive transition
breakpoints.

## Clean debugger discriminator

Keep `0x0050FE80` only as a broad event logger, and add breakpoints at:

```text
0x00542B90  generic current-room/UI click producer
0x005E6960  popup-ring content producer
0x005E7130  small generic click helper
0x005363A0  event consumer; confirm case 0x42D -> click.ogg
0x0051B1F0  popup button id returned
0x006122C0  real room transition continuation
0x005AB760  C->S 0x0065 sender
```

Alternatively, capture the caller-of-`FUN_005305D0` stack return in addition
to the inner `0x005305F4` return. That outer return identifies which of the
three producers generated the click.

For the exact `FUN_005305D0` prologue shown in this binary, at entry to the
underlying `0x0050FE80` queue routine the useful stack fields are:

```text
[ESP+0x00] = 0x005305F4 (inner wrapper return)
[ESP+0x04] = event id (0x042D in this capture)
[ESP+0x08] = mode (normally 1 for play)
[ESP+0x0C] = 0xFFFFFFFF
[ESP+0x64] = caller-of-FUN_005305D0 return address
```

Logging `[ESP+0x64]` on the next hit directly separates the
`FUN_00542B90`, `FUN_005E6960`, and `FUN_005E7130` paths without changing the
program.
