# Toast success witness contract and 100% fixture (2026-07-18)

## Scope

This record narrows the PatHouse foodmaker implementation to the original
client's observed state projection. It is for the closed-client preservation
server only. No client binary patch or synthetic food grant is used.

## 1. Toast success threshold

**VERIFIED (original-client decompilation + data table):**

- `FUN_005A8AA0` maps food ID `1006` (Toast) to cooking stat `40`.
- `CJSProperty::SuccessCookCheck` at `FUN_005A4EE0` calculates
  `rand() % 100 <= currentSkill * 100 / skillMaximum`.
- The current and maximum values are read by `FUN_005A49B0` and
  `FUN_005A4A50` from the property array (`Property+0x5F4`, stride `0x0C`,
  current at `+0`, maximum at `+8`).
- The original `init.csv` Toast row is `30,0,40`; therefore stat40's cap is
  exactly `40`. At `current=40`, the right side is 100 and every possible
  `rand()%100` result (0..99) succeeds.
- The previously verified server `0x0007` snapshot mapping encodes stat40 at
  `snapshot[0x5A:0x5C]`; the exact success fixture contains `28 00` there.

Relevant original addresses: `005A4EE0`, `005A8AA0`, `005A49B0`,
`005A4A50`, success callback `0055F1C0`.

## 2. Food `0x0014` is an action witness, not always a consumption

**VERIFIED (static control flow):** the success callback executes
`D1 -> C2S 0x0014(foodId) -> inventory add(foodId) -> C2S 0x0008`.
The already captured failure branch sends only `C2S 0x0008`, with the
ingredient decrement.

**IMPLEMENTED and regression-tested:** the preservation server now permits a
food `0x0014` whose existing quantity is zero. It records it as a pending
action witness and lets the immediately following client-owned `0x0008`
projection decide the operation:

- food `-1` => `consume`
- food `+1` => `produce` (the successful foodmaker case)
- food `0` => `unchanged`

Medicine remains a direct server-owned decrement and still rejects unowned
items. The server never manufactures a food entry; only the exact 41-byte
`0x0008` snapshot commits it.

## 3. Isolated live fixture

**VERIFIED (canonical writer/journal):**
`tools/prepare_cooking_live_qa.py --toast-success` creates a new namespace
without overwriting an existing one, with food sum 0, ingredient1500=2, and
stat40=40. Its canonical seed and JSONL journal are atomically durable.

The isolated namespace `qa_toast_success_20260718` was seeded as transaction
`tx-00000001`, revision 1, journal status `durable`.

**NOT VERIFIED (remaining live proof):** after restarting the isolated server
with this witness change, perform one natural Toast selection and require
`C2S 0x0014[EE 03] -> C2S 0x0008` with food slot 6 `0->1`, ingredient 0
`2->1`, durable canonical revision advance, and a clean reconnect restoring
the result through `S2C 0x0007`.

## 4. Regression

**VERIFIED:** `PYTHONPATH='.;tools' python -m unittest
tools.test_server_contract_layers -v` completed with **101 tests OK**,
including both the existing food-consume witness and the new empty-slot
production witness.

**VERIFIED:** the complete suite `PYTHONPATH='.;tools' python -m unittest
discover -s tools -p 'test_*.py' -v` completed with **182 tests OK** after the
witness change.
