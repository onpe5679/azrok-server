# Scheduled-task request guard and restart-4 end-to-end proof (2026-07-17)

This note records two operational results from the fourth clean restart: a
second independent natural PatHouse-to-Plaza success, and a fail-closed guard
for the shared elevated scheduled-task dispatcher.

## 1. Restart 4 completed the natural route (VERIFIED)

Client PID `138892` entered a stable PatHouse after a clean launcher/server
restart. The control API reported the following progression:

```text
pathouse_stable
-> pathouse_exit_ready
-> plaza_healthy
```

The growth step used the already verified internal button-reader contract,
not a coordinate guess:

```text
ButtonId = 33 (0x21, Sleep)
target caller = 0x005E3F14
param2 = 1
param3 = -1
```

The client naturally displayed the RedRon growth result. The user then clicked
the actual outside door. Capture `captures/packets_20260717_230719.txt` records:

```text
C2S #38 0x0019 [00]
S2C #38 0x000D [00]
C2S/S2C #39..#43 0x0016 heartbeat plus S2C 0x0004[01] x5
C2S #44 0x0064 [01]
S2C #44 0x0064, 27 bytes
C2S/S2C #45 onward 0x0016 heartbeat resumed
```

The authoritative payload was:

```text
0a01000000007b0f0000c3000000000000000202ea070611170b2b
```

The resulting runtime state was:

```text
scene=110
phase=4
dispatch_mode=1
self_actor_id=1
transition.code=plaza_healthy
state-1 dispatch ready=true
heartbeat recent=true
engine error=false
```

Evidence:

- `artifacts/dynamic-analysis/restart4_pathouse_20260717_2310.bmp`
- `artifacts/dynamic-analysis/restart4_after_sleep_button_20260717_2312.bmp`
- `artifacts/dynamic-analysis/restart4_plaza_healthy_20260717_2317.bmp`
- `captures/packets_20260717_230719.txt`

This independently repeats note 63's successful clean retry. No `S2C 0x006E`
or executable code patch was used. Frida was restricted to test-only internal
button-event injection; it did not alter game/protocol logic.

## 2. Visual spawn/camera evidence is excluded (VERIFIED contamination)

The user manipulated an already running client before the final visual check.
One existing client was therefore not at the original spawn point and did not
have the original camera angle.

The restart-4 screenshot is valid evidence that the outdoor Plaza rendered and
the client remained playable, but it is **not** a baseline for any of these:

- the protocol-defined initial Plaza position;
- the default camera position or yaw;
- equality of spawn/camera state across two clients.

Any future spawn or camera conclusion needs a fresh client captured before
manual movement/camera input. Current positional/camera interpretation is
**NOT VERIFIED**.

## 3. Misspelled request marker caused destructive fallback (VERIFIED)

The elevated scheduled task `Azrok-Plaza-Stop` is a shared dispatcher for
one-shot UI, Frida, debugger, alternate-launch, and close-instance requests.
During a secondary-client attempt, the intended UI request was mistakenly
written as:

```text
REQUEST_UI_ACTION.json
```

The recognized name is:

```text
REQUEST_AZROK_UI_ACTION.json
```

Because the old dispatcher did not recognize the misspelled marker, execution
fell through to its historical default stop-all branch and closed the clients
and shared server. This was an automation-request filename error, not a game
or protocol failure.

## 4. Unknown `REQUEST_*` markers now fail closed (VERIFIED)

`tools/stop_azrok_elevated.ps1` now enumerates regular files matching
`artifacts/dynamic-analysis/REQUEST_*` after all recognized one-shot branches
and before the destructive default. If any unknown marker exists, it throws:

```text
Unknown request marker(s): <name>. Refusing default stop-all fallback.
```

Recognized paths include the exact UI name
`REQUEST_AZROK_UI_ACTION.json`. A deliberate scheduled-task invocation with no
request marker still retains the original stop-all behavior.

A live negative test used an unknown marker named
`REQUEST_TYPO_GUARD_TEST`. The scheduled task returned failure (`LastTaskResult
= 1`) while client PID `138892` and the server remained alive. The marker was
then removed. This proves that a future spelling error cannot silently reach
the default destructive branch.

## 5. Operational rule

- Use the existing helper scripts when one exists; they create the exact marker
  names expected by the dispatcher.
- For direct UI requests, the only valid filename is
  `REQUEST_AZROK_UI_ACTION.json`.
- Treat any scheduled-task failure with a remaining unknown `REQUEST_*` marker
  as a protected refusal. Correct or remove the marker before retrying.
- Do not interpret a user-manipulated client's spawn position or camera angle as
  protocol evidence.

## 6. Two-client follow-up

Restart 4 subsequently added a reused-server secondary client and proved
reciprocal Plaza roster rendering plus movement relay. That evidence and the
multi-client dashboard attribution correction are documented in note 67. The
spawn/camera exclusion above remains in force for both screenshots.
