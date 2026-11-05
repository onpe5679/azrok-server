# Gate 2c localhost result and Gate 2a host block (2026-07-19)

> **PARTIALLY SUPERSEDED by 152 and 157.** The old instrumented Azrok package did show a white client,
> 0 MIPS, and an empty probe body as recorded below. A later probe-free command
> smoke reached 135 MIPS and completed, and Notepad visibly rendered at 91 MIPS
> in the same browser harness. Therefore the generic-dead-scheduler inference
> is withdrawn. A later clean named-CLI Azrok package itself ran at 87–122 MIPS
> bursts, so the surviving failure boundary is after startup and before verified browser D3D output.

## Scope

This record preserves the requested five-stage feasibility ladder after Gate
1. Gate 2c used the official BoxedWine web build mirrored on loopback. Gate
2a then attempted both a Windows Wine command and the existing Ubuntu WSL2
desktop-Wine route with the requested debug environment.

## Gate 2c: BoxedWine browser on localhost

### Pinned inputs

**VERIFIED:** the public page was replaced by a local-only harness bound to
`127.0.0.1:8765`. The server returned correct `206 Partial Content` responses
for the on-demand Wine root and `application/wasm` for the emulator. It was
stopped after the record was captured.

- Official BoxedWine web files were mirrored under `tools/boxedwine_local/`.
- Wine root: `fullWine1.7.55-v8.zip`, 50,012,741 bytes.
- Minimal online overlay: `wine1.7.55-v8-min-online.zip`, 9,759,641 bytes.
- Clean Azrok payload:
  `artifacts/boxedwine/20260719_gate2c/Azrok_BoxedWine_runtime.zip`,
  SHA-256
  `791F4964D9569024E786494D9AC13EE4F139D9363C36A2D53C4E26185EB69C93`.
- The derivative Gate 2c ZIP added only `run_azrok.bat` and the supplied D3D9
  probe; the original `Azrok.exe` was not modified.
- Preserved HTTP evidence:
  `artifacts/boxedwine/20260719_gate2c/localhost_gate2c.log`.

### Five-stage disposition

| Stage | Result | Direct observation |
|---|---|---|
| (a) launch | **PASS to Wine/Azrok window creation** | BoxedWine launched `/bin/wine cmd /c run_azrok.bat`; Wine created an 800x600 window. |
| (b) D3D device | **NOT VERIFIED** | The D3D9 probe section was printed after Alt+F4, but its body was empty. No `CreateDevice` evidence was produced. |
| (c) screen output | **FAIL** | The shared browser canvas showed a stable white 800x600 client area, never an Azrok frame. |
| (d) frame | **FAIL** | The observed performance remained **0 MIPS** and the white client area did not change over more than 25 seconds. |
| (e) server connection | **NOT REACHED / structurally blocked** | No rendered client or login path was reached; this web build also has no usable native socket path and the Windows WDL launcher is not available inside BoxedWine. |

**VERIFIED (live shared session):** preserve the three symptoms together:

1. white 800x600 client area;
2. 0 MIPS / no frame change;
3. empty D3D9 probe log body.

The console also reported `wineboot.exe` lookup failure, missing
`winepulse.drv`/`winealsa.drv` host libraries, and the `winmm` mixer-control
fixme. Those messages are evidence of this old BoxedWine Wine environment,
but they do not by themselves prove which call prevented D3D device creation.

An initial local-host attempt failed with an XHR request to the public-build
absolute path `/boxedwine/fs/...`. The local server added a path alias and all
subsequent root requests returned HTTP 206. The final white-screen result was
therefore observed after the XHR fault had been removed.

Per user direction, Gate 2c stopped at this state. No further override or
probe experiment is folded into this result.

### Later isolation result

See `152_GATE2C_SCHEDULER_AND_WINE_GUI_SMOKE_20260719.md`. **VERIFIED:** a ZIP
containing only a batch file completed a 100,000-iteration guest loop and
reached 135 MIPS; the same harness visibly rendered Wine Notepad at 91 MIPS.
The three symptoms above remain historical observations of the Azrok payload,
but no longer establish a generic BoxedWine/WASM scheduler or Wine GUI failure.

## Gate 2a: desktop Wine

### Requested diagnostic command

The attempted environment was:

```text
WINEDEBUG=+d3d9,+loaddll,+relay
WINEDLLOVERRIDES=d3d9=b,n
wine Azrok.exe -NX200
```

### Host feasibility result

**VERIFIED:** no `wine`, `wine32`, `wine64`, or `wineserver` executable exists
on the Windows host or its PATH. The Windows attempt therefore stopped at
command resolution: `wine` was not recognized.

**VERIFIED:** the registered Ubuntu distribution is WSL2 and cannot currently
start. The same environment and command through
`wsl.exe -d Ubuntu -- env ... wine ...` stopped before the Linux shell with:

```text
Wsl/Service/CreateInstance/CreateVm/HCS/HCS_E_HYPERV_NOT_INSTALLED
```

Firmware virtualization, VM-monitor extensions, and SLAT report enabled, but
`HypervisorPresent=False`. `vmcompute` and `WslService` are running. Reading
BCD and Windows optional-feature state requires elevation and was denied in
this session, so the exact host configuration knob is **NOT VERIFIED**.

### Five-stage disposition

| Stage | Result | Direct observation |
|---|---|---|
| (a) launch | **BLOCKED before app launch** | Windows Wine is absent; Ubuntu WSL2 fails VM creation before its shell. |
| (b) D3D device | **NOT REACHED** | No Wine process existed, so `+d3d9` emitted nothing. |
| (c) screen output | **NOT REACHED** | No Wine desktop or Azrok window was created. |
| (d) frame | **NOT REACHED** | No renderer process existed. |
| (e) server connection | **NOT REACHED** | The app never launched; WDL injection compatibility was not testable. |

Because the Wine loader itself never existed, `+relay` could not be narrowed
to call families and `WINEDLLOVERRIDES` was never consumed. This is a host
availability result, not evidence that Azrok is incompatible with desktop
Wine.

## Reassessment after Gate 2a

Gate 2a supplied no app-versus-Wine evidence, so it cannot explain or overturn
the Gate 2c white-screen result. Returning to Gate 2c now would only repeat the
same unknown. The next useful isolation point is Gate 2b, native BoxedWine,
where the emulator/Wine/GL stack can be tested without WASM/WebGL.
