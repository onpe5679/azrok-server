# Toast cooking track closure: evidence, boundaries, and clean baseline (2026-07-19)

## Scope and disposition

The unattended cooking QA session is closed. This separates verified
client/handler facts from samples that have not yet been observed. No client
binary patch and no synthetic server food grant were used.

## VERIFIED: local conditions and UI route

### Toast skill (stat40)

- `FUN_005A8AA0` maps Toast/item `1006` to stat `40`.
- `FUN_005A4EE0` performs the local cooking roll:
  `rand()%100 <= currentSkill*100/skillMaximum`.
- The original Toast data has maximum 40. At `stat40=40`, every 0..99 roll
  succeeds. This is a local success gate, not a server packet decision.
- The state snapshot field is `+0x5A` (u16); the QA fixture wrote `40` there.

### Kitchen cleanliness (stat23)

- Stat23 is the local kitchen-cleanliness prerequisite. A cleanliness-zero
  fixture is refused by the client before foodmaker interaction; the QA seed
  used `stat23=80`.
- Cleanliness alone is not sufficient: clearing source completed tutorial row
  `g1:r1:k0:a1001:c40` produced a local initial-tutorial refusal. Retaining it
  allowed the foodmaker route. This is local UI state, not a server reply gap.

### PatHouse queue events

- `FUN_005E3EE0` maps `0x2F` to foodmaker popup path
  `FUN_005E6960(0x75, ...)`.
- The same consumer maps `0x48` to Toast action `0x3EE`/item 1006, runs the
  local D1 condition, and starts `FUN_0055BDB0(4)`.
- Neither button handler itself sends a packet. A live isolated run reached
  `popupBuild key=0x75` for `0x2F`.

## VERIFIED: failure vs success protocol branches

| Client roll | Original local behavior | Server consequence |
|---|---|---|
| false | Deletes one ingredient and sends only C2S `0x0008` | Persist the exact 41-byte inventory projection; do not create food. |
| true | D1 → C2S `0x0014[EE 03]` → local food add → C2S `0x0008` | Treat `0x0014` as a pending witness; the following client snapshot commits the food increment. |

The server covers the empty-food-slot success witness but never invents food:
the exact `0x0008` snapshot remains authoritative for inventory.

## NOT VERIFIED: samples still required

- A human-operated natural Toast success sample has not yet produced full
  `0014 → 0008 → 0007` in a clean isolated run. Filtered queue injection
  reaches the action plan but cannot replace the 3D completion callback.
- Natural live samples for runtime-row kinds **1, 2, and 5** are not captured.
  This is **sample insufficiency**, not a claim that the branches are
  unrecoverable or unsupported by the server contract.
- The next cooking run must be human-operated with structured server capture
  only. Do not combine x32dbg, Frida, or automatic click instrumentation.

## QA teardown and baseline

- The isolated QA client, port-9218 server, x32dbg, Frida request markers, and
  UI automation requests were removed. The primary game client was left alive.
- Full regression after tooling changes:

```text
python -m unittest discover -s tools -p 'test_*.py' -v
Ran 182 tests in 3.064s
OK
```

## Related records

- `128_PAT_HOUSE_FOODMAKER_CLEAN_REPRO_20260718`
- `129_TOAST_SUCCESS_WITNESS_AND_FIXTURE_20260718`
- `130_TOAST_FOODMAKER_LOCAL_GATES_20260719`
- `131_B_DRIVE_X32DBG_AUTOMATE_RECOVERY_20260719`
