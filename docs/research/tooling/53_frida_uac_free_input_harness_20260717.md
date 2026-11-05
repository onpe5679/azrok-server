# UAC-free Frida input harness (2026-07-17)

This note records the validated way to attach the 32-bit Frida input harness to
the elevated Azrok client without asking the interactive user to approve a UAC
dialog on every attach. The executable and its on-disk data are not modified.

## Why the prompt appeared

`Azrok.exe` is launched at high integrity. Starting
`tools/azrok_frida_input.py` from an ordinary terminal therefore makes Frida's
`frida-helper-x86` request elevation before it can attach to the 32-bit target.
Cancelling that dialog can also leave a waiting `frida-helper-x86` process.

The project already has the registered `Azrok-Plaza-Stop` scheduled task,
configured to run with highest privileges. Its checked-in worker
`tools/stop_azrok_elevated.ps1` now has a narrow, one-shot Frida request branch.
Starting the already-approved task with `schtasks /Run` does not require a new
interactive UAC approval.

## Request boundary

The ordinary-integrity caller writes:

```text
artifacts/dynamic-analysis/REQUEST_FRIDA_INPUT.json
```

The elevated task consumes and deletes that request before returning. It does
not accept an arbitrary program, script path, command line, or shell fragment.
It validates all of the following again at high integrity:

- the PID exists and its image path is this workspace's `Azrok.exe`;
- the result file stays below `artifacts/`;
- the action is only `observe` or `push_button`;
- observation duration is in `(0, 30]` seconds;
- a button id fits `u16`, repeat is `1..300`, and settle time is
  `0..10000` milliseconds;
- a nonzero target caller lies inside the Azrok image and matches a reviewed
  button/caller pair.

Before attaching, the task removes a stale `frida-helper-x86` left by a
cancelled low-integrity attach. It deliberately does not stop x64 Frida
helpers or unrelated Python processes.

`tools/invoke_azrok_frida_elevated.ps1` is the normal front end. It creates a
unique result path, writes the one-shot JSON request, runs
`Azrok-Plaza-Stop`, waits for consumption, and prints the result. Examples:

```powershell
# Read-only hook observation
powershell -ExecutionPolicy Bypass -File tools\invoke_azrok_frida_elevated.ps1 `
  -ProcessId 116968 -Observe -Seconds 0.5

# Filtered SelectPet Connect event; caller is after ButtonQueue_Pop in
# FUN_005EA5B0.
powershell -ExecutionPolicy Bypass -File tools\invoke_azrok_frida_elevated.ps1 `
  -ProcessId 116968 -PushButton -ButtonId 6 -Repeat 80 `
  -TargetCaller 0x5ea5e1 -SettleMs 2500 -Trace
```

Do not use `target_caller=0` for unattended input. A caller filter prevents a
different queue consumer from taking the synthetic event; an earlier
unfiltered test was consumed during startup and reached the unrelated W1301
file-open failure path.

## Live validation

The first scheduled-task observation attached to live Azrok PID `116968` and
wrote:

```text
artifacts/dynamic-analysis/FRIDA_ELEVATED_20260717_151151_559.txt
frida_action=observe
target_pid=116968
exit_code=0
{"type":"loaded","payload":{"pointerSize":4,"arch":"ia32"}}
attached_pid=116968
observe_seconds=0.5
```

The hook then returned real `GetCursorPos` and `PeekMessage` observation
counters. The request file was consumed, the target stayed alive, and no
`frida-helper-x86` process remained after detach. This is runtime proof of an
elevated `ia32` attach, not merely successful task dispatch.

## Relationship to the patch-zero rule

The restoration baseline remains **zero client binary patches**. This harness
is test automation: it temporarily instruments a running test process to
observe input or enqueue a reviewed UI event that a human could select. It is
not shipped to players, does not edit `Azrok.exe`, and must not be used to
change game state, bypass a protocol condition, or manufacture a gameplay
success.

Consequently, results obtained through the harness must still be verified at
the actual boundary under test: visible UI state, captured C->S/S->C traffic,
client memory watches, or a subsequent human-play reproduction. Frida making
a button handler run is input automation evidence; it is not by itself server
protocol evidence.
