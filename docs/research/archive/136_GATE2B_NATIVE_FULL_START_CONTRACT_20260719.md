# 136 — Gate 2b: Native BoxedWine full-start contract

> **SUPERSEDED by 137.** The full-start construction remains historical evidence, but its pre-render clean-exit conclusion was caused by a missing `med.exe` in the disposable runtime mount. See `137_GATE2B_MED_RUNTIME_FIX_D3D_CRASH_20260719.md`.

Date: 2026-07-19  
Status: **VERIFIED** for the execution boundary; downstream D3D/network stages are **NOT REACHED**.

## Purpose

Gate 2b must not treat `Azrok.exe` alone as the restoration startup condition. The known-good Windows path is:

1. preservation server listening on `127.0.0.1:9200`;
2. start `Azrok.exe -NX200` suspended;
3. resume immediately so `acknex.dll` can initialize;
4. wait for engine pointer `0x006E8430`;
5. inject only the three WDL string pointers: server, user, auth.

Bare IP/user/auth command-line arguments are excluded: they trigger the previously rejected `LOCALAUTH.WDL` route.

## Test construction (VERIFIED)

- Native runtime: official BoxedWine 26R1 Windows x64 console executable. The initial run used `TinyCore15Wine6.0.zip`; the official UI then downloaded the matching default `TinyCore15Wine11.0.zip` (159,146,791 bytes) for a version-isolation rerun.
- Guest launcher: `tools/boxedwine_guest_launcher/guest_launcher.c`, PE32 x86. It mirrors the proven Python launch order above, uses `127.0.0.1:9200`, `player`, `localauth`, and does not patch executable code/imports.
- Deployed guest launcher SHA-256: `0B05B0DF5407F591FEF1416E2D0A502219C7D720F756E9345693474AB8535DDA`.
- Host server: `python -u tools/run_server_only.py --port 9200 --control-port 0 --content-profile playable --state-namespace gate2b_boxedwine_20260719`.
- Host TCP self-connect succeeded before the guest run. The game mount was a clean BoxedWine runtime plus `AzrokGuestLauncher.exe`.

## Results

| Gate 2b stage | Result | Direct evidence |
|---|---|---|
| (a) application launch | **PARTIAL / FAIL** | BoxedWine creates its `Gate2b Azrok full-contract` window; guest launcher creates and resumes the Azrok child; `AckUtl.dll`, `acknex.dll`, Wine `d3d9.dll` and `wined3d.dll` load. The child exits with code `0` before engine-variable initialization. |
| (b) D3D device creation | **NOT REACHED** | `Direct3DCreate9=0`, `CreateDevice=0`, `trace:d3d9=0` in the full-contract and relay captures. |
| (c) screen output | **FAIL / NOT REACHED** | A host window is shown, but the child terminates before game rendering begins. No game frame was observed. |
| (d) frames | **FAIL / NOT REACHED** | No `Present`, no D3D device, no render loop evidence. |
| (e) server connection | **NOT REACHED** | The 9200 log has only the deliberate host self-connect; no guest game protocol connection or packet arrived because WDL injection never began. |

## Exact blocker (VERIFIED)

The first complete-contract run reports that the engine variables do not initialize. The instrumented rerun narrows this: the Azrok child exits normally (`GetExitCodeProcess == 0`) before `0x006E8430` becomes usable, so no WDL pointers are written.

The one-time `WINEDEBUG=+relay` capture identifies the exiting guest process as `00b4` (the process that loaded native `D:\\acknex.dll`). Its terminal call is:

```text
00b4:Call KERNEL32.ExitProcess(00000000) ret=101d9508
```

Before that terminal path, the same process loads Wine D3D9/wined3d but has no observed `Direct3DCreate9`, `CreateDevice`, socket connect, or game packet call. `mscoree.dll` lookup immediately before process teardown is observed, but its causal role is **NOT VERIFIED**; it must not be treated as the reason for exit.

### Wine-version isolation (VERIFIED)

The same server, guest launcher, mount, `-NX200`, and WDL-injection wait were rerun with the official BoxedWine 26R1 Wine 11.0 filesystem. Wine first initialized its prefix, then loaded `D:\\AckUtl.dll`, `D:\\acknex.dll`, `d3d9.dll`, and `wined3d.dll`; the child again exited before the engine pointer became usable. The guest launcher reports `Child exited before engine initialization: 0`.

Therefore this failure is **not isolated to the old Wine 6 filesystem**. D3D9 device creation and network injection remain not reached in both images.

## Evidence artifacts

- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine6_full_contract_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine6_full_contract_diagnostic_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine6_full_contract_relay_stdout.log` (10.8 MiB, narrow one-time relay capture)
- `artifacts/boxedwine/20260719_gate2b_native/server_9200_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/guest_launcher_build_x86_diagnostic.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_full_contract_stdout.log`

## Decision impact

This is not evidence that Azrok's D3D9 API is unsupported by native BoxedWine. Rendering is not reached. It is evidence that the full restoration startup contract cannot get past native BoxedWine/Wine's pre-engine clean-exit boundary in this environment. Therefore Gate 2b is a negative result at (a), and no D3D/WebGL backend direction can be selected yet.
