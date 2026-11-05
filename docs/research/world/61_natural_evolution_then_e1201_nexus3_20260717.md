# Natural evolution succeeds, then E1201 `Nexus too small! (3)`

> **SUPERSEDED by 62 for the operational conclusion and next discriminator.**
> The Nexus-40 failure remains valid historical A/B evidence; native `-NX200`
> subsequently completed the same natural evolution and natural Plaza exit.

Date: 2026-07-17

This is the first packet-faithful, client-owned evolution run.  It also
corrects the timing conclusion in note 60.  The executable and Acknex binary
were unmodified and the runtime nexus setting remained 40.

## 1. Starting contract

The server delivered the shipped 472-byte `S2C 0x0007` with:

- selector byte `payload[2] = 0`;
- EXP 33000 and the recovered shipped stat profile;
- stat 55/56 authority values 1/2;
- runtime row 0 `kind=3, aux=0`;
- all remaining runtime rows left at the `0xFFFF` sentinel.

The client reached PatHouse `scene=100 / phase=2`, remained responsive, and
continued heartbeats at native `Nexus=40`.

## 2. Real input path and menu evidence

Late Frida attachment originally missed the DirectInput device creation.  The
test harness now observes the existing device poll at `FUN_00508FA0` and, only
while a synthetic test click is active, supplies raw left-button bit `0x80` at
the function's caller output `+4`.  No game state or protocol field is written.

A world click on the live BlueRon returned action 100 and built the real radial
menu.  Runtime button placement exposed:

| Button | ID | live top-left |
|---|---:|---:|
| 식사 | 44 | `(527,249)` |
| 용변 | 37 | `(459,249)` |
| 목욕 | 41 | `(407,292)` |
| 수면 | 33 | `(395,359)` |

`식사` opened the genuine 15-slot cooking inventory (`IDs 393..407`), which
was empty because the current server profile contains no food items.  `수면`
was accepted as button ID 33 without inventing an item or server ACK.

Primary artifacts:

- `artifacts/dynamic-analysis/FRIDA_ELEVATED_20260717_202608_299.txt`
- `artifacts/dynamic-analysis/evolution_menu_live_20260717_2027.bmp`
- `artifacts/dynamic-analysis/FRIDA_ELEVATED_20260717_203109_608.txt`
- `artifacts/dynamic-analysis/evolution_food_grid_live_20260717_2032.bmp`
- `artifacts/dynamic-analysis/FRIDA_ELEVATED_20260717_203331_734.txt`

## 3. Natural client-owned evolution (verified)

After the sleep action the client ran its own evolution presentation:

- the visible species changed from BlueRon to RedRon;
- the quest panel populated `크고 싶어요!` and `햄버거가 먹고 싶어요`;
- a later 196-byte natural `C2S 0x0007` changed its evolution field at `+0x05`
  from 0 to 1;
- the same snapshot retained EXP 33000 and stat 55/56 values 1/2;
- the server atomically persisted the exact evolution value 1.

The visible evolved state is captured in:

- `artifacts/dynamic-analysis/sleep_after_click_20260717_2038.bmp`
- `captures/packets_20260717_201615.txt`, packet `C2S #115`
- `server_state/417a726f6b31_c2s0007.bin`

This proves the recovered `kind=3, aux=0` runtime row and original care action
are sufficient to enter the natural BlueRon-to-RedRon transition.  It does not
prove the resulting model/resource work fits the current nexus allocation.

## 4. Failure boundary: separate E1201 dialog

Immediately after the visible evolution, Acknex opened a separate top-level
dialog:

```text
Error E1201
Nexus too small! (3)
```

The user-observed dialog image is preserved as
`artifacts/dynamic-analysis/E1201_NEXUS3_NATURAL_EVOLUTION_20260717.png`.

The underlying render window remained visible and `Responding=true`, so a
capture of only the AZROK render HWND falsely looked like a successful stable
state.  The packet capture stopped at 20:33:52 after the evolved state save.
No natural `C2S 0x0019` was reached **in this failed Nexus-40 run**.

This directly falsifies note 60 section 3's statement that the error was only
caused by setting the selector before stat import.  It also adds an important
distinction from note 57's earlier reported `(40)` body: this natural promotion
displayed `(3)` in the user's directly observed error dialog.

## 5. Safe baseline and resolved discriminator

The failed client was closed.  A clean restart returned to:

```text
scene=100 / phase=2 / Nexus=40 / Responding=true
saved_state_loaded=true
```

The saved snapshot contains evolution 1, but the server deliberately does not
copy that field into the initial `S2C 0x0007`; doing so is the already-proven
unsafe bootstrap path.  Reconnect evolution restoration remains unresolved.

The `(3)` detail has now been statically decoded: it is the failed allocation
size rounded up to KiB, not the configured nexus value.  Acknex has bottom-up
and top-down allocators.  Its live arena counters are `bottom=0x102FE9B0`,
`total=0x102FE9BC`, and `top=0x102FE9C0`; free space is
`total - bottom - top`.  The base pointer is at `0x102FE9C8`.

Note 62 resolves the allocator and configuration discriminator. The two failure
branches are bottom-up `ACKNEX.DLL+0x3F25C` and top-down `+0x3F3D2`; the detail
is request KiB. Acknex's native parser accepts `-NX200`, and the same natural
flow completed at Nexus 200 with both failure counters and E1201 report at zero.
The exact 2008 service argument and minimum sufficient arena remain unverified.
