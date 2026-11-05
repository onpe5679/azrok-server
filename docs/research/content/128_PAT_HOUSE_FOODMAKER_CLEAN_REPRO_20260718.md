# PatHouse Foodmaker clean reproduction and branch correction (2026-07-18)

> This record corrects only the `mode 6 = cooking` claim in archived 77. Its
> item/stat catalogue evidence remains useful, but the UI-mode attribution is
> superseded by this record; the prior record is retained at
> `docs/research/archive/77_cooking_recipe_system_20260718.md`.

## Scope

This is an interoperability evidence record for the local, officially closed
game client. No client binary patch or synthetic inventory/food response was
used in the clean reproduction.

## 1. Clean live observation: actual foodmaker Toast selection

**VERIFIED (dynamic, clean server/client session)**

- Run: `B:\Azrok_Captures\runs\20260718T230819_111132_aae197d5`
- Isolated namespace: `qa_cooking_clean_20260718`; canonical seed was food
  sum `0`, ingredient `[2,0,0]`.
- The user operated the actual PatHouse oven/foodmaker UI and selected Toast.
  No Frida process or x32dbg process was running. The process-module check
  could not cross the client privilege boundary, so it is not proof of no
  injected DLL; it is only a clean-process baseline.
- The client emitted exactly one changed `C->S 0x0008` 41-byte inventory
  snapshot at capture sequence `25`, packet number `12`, time
  `2026-07-18T14:09:27.355Z`: ingredient `[2,0,0] -> [1,0,0]`. The directly
  preceding baseline was capture sequence `20`, packet number `9`, at
  `14:09:09.523Z`. Food remained all zero. There was no `C->S 0x0014`,
  `0x0012`, `0x0017`, `0x0007`, food-add snapshot, or immediate S->C response
  in that action window.
- The server atomically persisted only `inventory.ingredient` as canonical
  revision `3 -> 4`, with durable journal receipt `tx-00000004`. This is the
  correct server behavior for the client-owned exact snapshot received; the
  server must not invent a Toast item that the client did not project.
- More than three subsequent `0x0016` heartbeat request/response pairs were
  captured, with the next pair at `14:09:36.122Z/.126Z`. The client remained
  responsive through PatHouse and a later natural Plaza transition until at
  least `14:23:36Z`. Therefore the earlier crash contaminated by a loaded
  `frida-agent.dll` is not reproducible as an inherent foodmaker crash.

**VERIFIED (completion static path; dynamic convergence):** this exact
ingredient-only projection is the original local **cooking failure** branch,
not a server omission. Original ILK names `FUN_0055F1C0` as
`CPlayerAni::SuccessFail_Food()` and `FUN_005A4EE0` as
`CJSProperty::SuccessCookCheck(int foodId)` (Naver peer `0x004AB560`).
The latter maps the food ID to its cooking-skill stat through `FUN_005A8AA0`
and returns a
`rand() % 100 <= currentSkill * 100 / skillMaximum` result. On false,
`FUN_0055F1C0` invokes `CJSInventory::DelRefrigerator(false, ingredientId)`
(`FUN_0059B570` / Naver `0x004A1240`) which removes only the ingredient and
saves the refrigerator (`FUN_0059B6D0`, `0x0008`), with no `0x0014` and no
food add. A zero skill maximum is an always-fail condition. This exactly
matches capture sequence 25 with structured-capture drop count zero.

On true, `FUN_0055F1C0` instead calls
`FUN_00596690(0, 0xD1, selectedFoodId)`: a successful ingredient delete is
followed by food `0x0014`, food add, and refrigerator `0x0008` save. The
success wire is already supported by the server's existing `0014` witness plus
authoritative `0008` snapshot contract, but a clean live success roll remains
**NOT VERIFIED**.

## 2. Static correction: mode 6 is not the foodmaker recipe success path

**VERIFIED (Plaza original decompilation)**

`FUN_005D27C0` (`0x005D27C0`) assigns the selected ID from its local slot
array. Its mode branches are distinct:

- mode `3` calls `FUN_0055CFA0` after the feed UI flag check;
- mode `5` checks action `0xD3`;
- mode `6` calls `FUN_00596690(0, 0xD5, selectedId)`, then
  `FUN_0059B7F0(selectedId)`, and sets a local flag.

`FUN_0059B7F0` calls `FUN_0059BE80` and invokes its container vtable only when
the selected item was successfully removed. It has no food-add call.
`FUN_00596690`'s `0xD5` switch contains disease-medicine IDs `4000..4005`.
Consequently the former attribution of `FUN_005D27C0` mode `6` as the
foodmaker cooking implementation is false. It cannot explain a Toast recipe
output and must not be used to infer a food-add server packet.

The previously noted `0xD1` action branch contains refrigerator/container
operations (`FUN_005A8A20`, `FUN_0059C270`, `FUN_0059C120`,
`FUN_0059BE80`, `FUN_0059BD70`, `FUN_0059B6D0`), but it is a separate branch
from mode 6 and does not establish the actual oven UI's selection-to-output
sequence.

## 3. Actual Toast button is an action launch, not a direct output grant

**VERIFIED (Ghidra, `FUN_005E1090` / `0x005E1090`):**

- `Data\\button\\BtnCookToast*.wis` is registered as button event `0x48`.
- Event `0x48` first stores action `0x3EE` (decimal `1006`, Toast) through
  `FUN_00562240`, then checks `FUN_005A14D0(0xD1)`.
- On the passing branch it records the same action through `FUN_0055CFA0` and
  calls `FUN_0055BDB0(4)`, which constructs local action records. It does not
  call the inventory snapshot sender in this button branch.

Therefore selecting Toast is only the entry to a local cooking action. The
observed later ingredient-only `0x0008` snapshot is the completion callback's
explicit failure path, not a server-side response or the button handler
itself. The success-roll live capture remains **NOT VERIFIED**.

`CPopupMyBag::View_Etc()` is the actual mode-6 path (medicine use), and
`FUN_005D0AA0` is `CPopupMyBag::View_Material()`, not a recipe page. MyBag is
therefore not the cooking trigger.

## 4. Prior contaminated crash is retained as evidence, not a conclusion

**VERIFIED (dynamic timeline):** The earlier actual-foodmaker attempt ended
with `0xC0000005`; the final normal packet preceded the fault, and no new
`0x0014`, `0x0008`, or `0x0007` occurred at the fault boundary. WER recorded
`frida-agent.dll` in the crashed process. Thus neither a server response nor
the foodmaker action itself is established as the cause. The clean run above
specifically refutes the broad claim that using the oven always crashes.

## 5. Wire framing correction

**VERIFIED (original packet writer plus capture):** a frame is
`[u16 payloadLen][u16 opcode][payload]`. For `C->S 0x0012` with five-byte
payload `[40:u32, 2:u8]`, the exact frame begins
`05 00 12 00 28 00 00 00 02`: header length is `5`, total frame length is `9`.
The older `09 00` example confused total frame length with the wire header.

## 6. Next direct checks

1. Use a non-invasive x32dbg observer when an executable is installed on B:
   or C: (the resolver fails closed; D: is prohibited) to observe the actual
   successful-roll `FUN_00596690` / `FUN_0059BD70` add path.
2. In a fresh fixture, record the whole user-visible sequence after selecting
   Toast until a success roll: resulting food slot, `0x0014`, `0x0008`
   projection, stat40 delta, and reconnect state.
3. Continue to avoid synthetic food or an ACK: failure is client-local
   ingredient deletion; success is already represented by client-emitted
   `0x0014` plus its snapshot.
