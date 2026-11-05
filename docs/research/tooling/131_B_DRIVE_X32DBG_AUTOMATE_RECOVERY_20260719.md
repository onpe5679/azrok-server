# B: x32dbg Automate recovery and Toast observer boundary (2026-07-19)

## Scope

This note records a tooling recovery only. It does not change the game binary,
send synthetic network packets, or alter the primary play session. The target
is the disposable Toast QA client on port 9218.

## VERIFIED

- The old desktop shortcuts target `D:\x64dbg\...`; D: was not read or used.
- A clean official x64dbg snapshot was restored under
  `B:\x64dbg\release\x32\x32dbg.exe`. The Python resolver and approved
  elevated launcher now recognize that unpacked `release` layout.
- x64dbg Automate requires its plugin separately from the debugger. Installing
  the 32-bit `x64dbg-automate.dp32` plus `libzmq-mt-4_3_5.dll` in
  `B:\x64dbg\release\x32\plugins` changed the failure from missing session
  registration to an explicit compatibility check.
- The current plugin reports compatibility tag `ghost_fungus`. The pre-existing
  global package reported `lilac_bonnet`; the elevated trace launcher therefore
  gives its child process `B:\Azrok_Automate_Runtime`, containing the matching
  client. The locked global MCP executable was left untouched.
- With the matching pair, the `cook` observer attached to the isolated client,
  cleared stale breakpoints, armed exactly 10 cold cooking checkpoints, and
  resumed it. The log then recorded normal C2S `0x0016` heartbeats through the
  generic sender.
- Closing a live interactive x32dbg session caused its attached disposable QA
  client to exit. The primary user client was not affected.

## NOT VERIFIED / boundary

- The natural Toast success callback was not captured in this observer run.
  GPU TLS breakpoints from `nvgpucomp32.dll` preceded Automate ZMQ failure
  `Again(Resource temporarily unavailable)`, after which the disposable client
  exited.
- Do not attach Frida input and x32dbg to the same client in the next attempt.
  Use structured server capture during real oven/table input, then a separate
  debugger-only replay if the packet chain remains incomplete.

## Verification

```text
python -m unittest tools.test_x32dbg_path -v  -> 2 tests OK
python tools/x32dbg_plaza_interaction_trace.py --help -> cook profile listed
PowerShell parser for tools/stop_azrok_elevated.ps1 -> syntax-ok
```

## Result

The non-D: dynamic-analysis path is restored and an actual attachment was
observed. It is usable only with the single-observer restriction above; this
does not alter the Toast content conclusion in 128/130.
