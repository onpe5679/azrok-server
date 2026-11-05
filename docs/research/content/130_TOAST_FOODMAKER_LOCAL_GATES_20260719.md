# Toast foodmaker local gates and isolated fixture correction (2026-07-19)

## Status

This note records the final live attempts after the success fixture in 129.
It does **not** promote a Toast success packet to VERIFIED: the client did not
emit one.  The negative result is useful because each precondition was
observed at its local consumer, so it must not be misclassified as a server
protocol gap.

## 1. Existing-character connection event

**VERIFIED (Ghidra + isolated live):** `FUN_005EA5B0` is the existing-pet
SelectPet queue consumer.

- button `0x06` is the Connect action.  With its exact post-`ButtonQueue_Pop`
  caller (`0x005EA5E1`), the isolated client sent C→S `0x0005[00]` and received
  S→C `0x0007`; the server reported `scene=100`, `phase=2`, and a bound
  canonical key.
- button `0x07` is CreatePet, not Connect.  Its live effect is the character
  creation screen.  The previous use of `0x07` is retained as a harmless
  diagnostic correction, not a connection result.

## 2. Foodmaker and recipe events

**VERIFIED (Ghidra):** PatHouse queue consumer `FUN_005E3EE0` maps:

- `0x2F` (`BtnCook`) to `FUN_005E6960(0x75, ...)`, the foodmaker popup route;
- `0x48` (`BtnCookToast`) to action id `0x3EE` (Toast / item 1006), then the
  local `0xD1` condition and `FUN_0055BDB0(4)` action plan;
- no packet is sent by either button handler itself.

**VERIFIED (live):** an isolated client whose source tutorial completion was
preserved consumed `0x2F` once and emitted the `popupBuild key=0x75` hook
event.  That proves it passed the local foodmaker availability check.

## 3. Fixture correction: prerequisite state is local

**VERIFIED (source-state comparison + live):** a fixture that cleared
`completed_runtime_rows` was refused by the local UI with the initial-tutorial
message, even after stat23 kitchen cleanliness was 80.  The normal source
state contains `g1:r1:k0:a1001:c40`; retaining that completed-row identifier
allows the `0x2F` foodmaker popup route.

`tools/prepare_cooking_live_qa.py` now:

- seeds `stat40=40` for a deterministic Toast success roll;
- seeds stat23 kitchen cleanliness (default 80);
- retains source runtime/completed tutorial state rather than clearing it;
- still writes through the production canonical transaction and durable
  journal, and refuses namespace overwrite.

## 4. What the direct UI-event run did and did not prove

**VERIFIED (live hook):** in namespace
`qa_toast_success_tutorial_20260719`, C2S/S2C login completed and `0x48` was
consumed once by `FUN_005E3EE0`; the client created the local action plan.

**NOT VERIFIED:** no `0x0014`, follow-up `0x0008`, or C2S `0x0007` appeared
within the subsequent 20 seconds, and the canonical revision stayed 1.  The
filtered queue injection therefore does not substitute for the 3D
foodmaker-interaction context that naturally drives the completion callback.
It is not evidence that the preservation server failed to answer a cooking
packet: no such client packet was produced.

## 5. Verified next boundary

Use the same `qa_toast_success_tutorial_20260719` state with one real
foodmaker object interaction (or an x32dbg observation of
`FUN_0055F1C0` after that interaction).  Success is only accepted when the
single run contains, in order:

1. C→S `0x0014[EE 03]`;
2. C→S `0x0008` 41-byte snapshot with food slot 6 `0→1` and ingredient0
   `2→1`;
3. C→S `0x0007` 196-byte state save;
4. canonical revision/journal commit and reconnect S→C `0x0007` restoring the
   same inventory projection.

## Evidence

- `artifacts/dynamic-analysis/TOAST_SUCCESS_CLEAN_OPEN_FOODMAKER.txt`
- `artifacts/dynamic-analysis/TOAST_SUCCESS_TUTORIAL_OPEN.txt`
- `artifacts/dynamic-analysis/TOAST_SUCCESS_TUTORIAL_SINGLE_EVENT.txt`
- `artifacts/dynamic-analysis/TOAST_SUCCESS_TUTORIAL_FOODMAKER_OPEN.bmp`
- `B:\Azrok_Captures\runs\` (isolated structured captures)
- full regression: `182 tests OK`
