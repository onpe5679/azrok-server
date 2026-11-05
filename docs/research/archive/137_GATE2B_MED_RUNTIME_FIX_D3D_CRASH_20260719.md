# 137 — Gate 2b: missing runtime file fixed; D3D frames then access violation

Date: 2026-07-19  

> **SUPERSEDED by 138 and 139.** The original `med.exe` packaging observation
> remains valid, but the claimed D3D/render-path crash cause was replaced by
> the verified named-CLI startup race in 138. PatHouse geometry measurement is
> recorded in 139.
Status: **VERIFIED** for the new native BoxedWine boundary. The pre-render clean-exit conclusion in 136 is superseded.

## Scope

This run keeps the real startup contract: the preservation server on `127.0.0.1:9200`, the guest launcher’s suspended-create then immediate-resume order, and only the three WDL string injections after engine pointer `0x006E8430` becomes usable. It is not an `Azrok.exe`-only test.

The user-supplied direct PE-header check is also retained: `Azrok.exe` has image base `0x00400000`, `RELOCS_STRIPPED`, and no `DYNAMICBASE`; therefore the launcher’s absolute engine-pointer address is not an ASLR hypothesis. The child crashes before that pointer can be used.

## First blocker: packaging, not Wine D3D (VERIFIED)

The initial BoxedWine game mount omitted `med.exe`.

- Relay evidence: `CreateFileA("D:\\med.exe", OPEN_EXISTING)` failed with `NtCreateFile=c0000034` / `GetLastError=2`.
- Static Acknex path: `acknex.dll` opens `med.exe`; failure writes `Installation corrupted`, sets the failure state, waits five seconds, then calls `ExitProcess(0)`.
- Both the old 2c ZIP-derived runtime and the initial 2b mount lacked the file.
- The original `med.exe` and the installation-image extraction are identical: 1,036,288 bytes, SHA-256 `2F4E73BBB7DEB5903E47568827935B7B7C7DE39B02366088BDBC5ED0F66ACFEF`.

The original was copied only into the disposable 2b mount `artifacts/boxedwine/20260719_gate2b_native/Azrok_runtime/med.exe`. No game executable or import was patched.

## Cheap slowness hypothesis (VERIFIED — rejected)

The guest launcher’s engine wait was increased from 30 seconds to 300 seconds (`600 × 500 ms`) and rebuilt as PE32 x86. The first rerun terminated in approximately one second with:

```text
[ERROR] Child exited before engine initialization: 0
```

Therefore the former condition was a clean process termination, not a slow x86-emulation initialization. The final 300-second wait code reports the last engine-pointer/read state when a child remains alive; it did not need to reach that timeout here.

## After `med.exe`: five-stage Gate 2b result (VERIFIED unless marked)

| Stage | Result | Direct evidence |
|---|---|---|
| (a) launch | **PASS** | Guest launcher created and resumed child PID 224; `Azrok.exe`, `AckUtl.dll`, and `acknex.dll` initialized. |
| (b) D3D device | **PASS** | `Direct3DCreate9 Created d3d9 object`; `d3d9_CreateDevice Created device`; `wined3d_device_create Created device`. |
| (c) visible screen | **NOT VERIFIED** | BoxedWine showed its window, but its lifetime was shorter than the next safe screen capture. The renderer executed onscreen Present; visible non-blank game pixels were not captured, so this is not called a visual pass. |
| (d) frames | **PASS (5)** | Five `swapchain_gl_present Presenting DC` / `SwapBuffers called, Starting new frame` pairs occurred. |
| (e) preservation-server connection | **NOT REACHED** | The 9200 log has only the deliberate host self-connect. The launcher reports child exit before engine initialization, so WDL server/user/auth injection never occurs. |

The child subsequently fails with `Unhandled exception code c0000005 flags 0 addr (nil)` and launcher exit code `3221225477` before `0x006E8430` is usable. This is now the active Gate 2b blocker: **Wine 11 / BoxedWine’s rendering path has initialized and presented five frames, then Azrok hits an access violation.** It is not evidence of a missing D3D9 surface.

## Exception instruction (VERIFIED) and caller (NOT VERIFIED)

`WINEDEBUG=+seh` records the first fatal game-thread exception as a read access violation at `EIP=0x00654453`, with `ECX=0`:

```text
0024:trace:seh:dispatch_exception code=c0000005
0024:trace:seh:dispatch_exception eip=00654453 ... ecx=00000000
```

Ghidra maps that instruction to `Azrok.exe!FUN_006543c0`, the CRT-style `strcat` implementation. Its `0x006544a8` path loads the second argument into `ECX`; `0x00654453` then reads `[ECX]`. Therefore the immediate fault is **a null source string passed to `strcat`**, not a null destination and not an address relocation issue.

WineDbg is present at `/opt/wine/bin/winedbg` (the earlier `/bin/winedbg` failure was a path error). It can start the child under debugger, but this BoxedWine console path accepts the initial continue and then returns only `Process ... terminated` without emitting the queued `bt` result. Its installed Wine 11 build rejects both `--backtrace-all` and `--minidump`; therefore the ordinary noninteractive dump route is absent too. The direct caller that supplied the null source is consequently **NOT VERIFIED**. The next debugger work must obtain a stack/caller without turning this into a renderer implementation task.

## Wine channel and override results (VERIFIED)

- `WINEDEBUG=+loaddll,+module` is present in this BoxedWine Wine build. It loads native `D:\\acknex.dll` and `D:\\AckUtl.dll`.
- That trace also shows Wine’s hardcoded builtin preference for `d3d9.dll`, even though `D:\\d3d9.dll` is found. `d3d9_probe.log` is therefore absent in this environment.
- A subsequent run passed `WINEDLLOVERRIDES=d3d9=n,b` and `WINEDEBUG=+d3d9,+d3d`. The narrow trace still directly confirms Wine D3D9/WineD3D object, device, draw, and Present execution. The custom probe did not become the loaded implementation, so Gate 1’s 56-method surface measurement remains the authoritative native-Windows measurement, not a 2b rerun result.

## 2b vs 2c contrast (VERIFIED)

The stopped 2c browser run remains exactly: white client area, `0 MIPS`, empty probe log. By contrast, native 2b now reaches Acknex initialization, D3D device creation, draw calls, and five present frames. This narrows the earlier 2c failure toward the WASM/packaging/browser layer; it does not prove 2c will work after merely copying `med.exe`.

## Evidence artifacts

- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_300s_030639_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_medfix_030731_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_medfix_module_030847_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_medfix_probe_d3d_030940_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_medfix_probe_d3d_plain.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_medfix_seh_031443_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_medfix_winedbg_btall_032209_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_medfix_minidump_032343_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/server_9200_wine11_300s_030617_stdout.log`
- `tools/boxedwine_guest_launcher/guest_launcher.c`

## Decision impact

There is now direct evidence that native BoxedWine can execute the original client’s D3D9 device and present loop. The next isolation should target the `c0000005` context in this specific native Wine/BoxedWine rendering run (for example, a narrow debugger/backtrace), not implement a WebGL backend or infer a D3D9 API gap. Gate 2c remains stopped until that result is considered with the user.
