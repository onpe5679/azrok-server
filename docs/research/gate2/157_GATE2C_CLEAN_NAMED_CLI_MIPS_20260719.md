# 157 Gate 2c clean named-CLI Azrok execution

Date: 2026-07-19

## Scope

This is a scheduler/startup measurement only. It does not claim browser 3D
rendering and deliberately does not traverse game content.

## Clean package

**VERIFIED:** `Azrok_BoxedWine_cleancli.zip` contains the clean Azrok runtime
plus one launch batch. It contains no replacement `d3d9.dll`, no D3D9 probe,
and no `WINEDLLOVERRIDES` line.

```bat
Azrok.exe -NX 200 -NWND -PL player -DIR localauth -IP 127.0.0.1:9200
```

- size: 156,622,454 bytes
- SHA-256: `0EC49810A5179CD1EA0F74E44BCDA867B5D3A81192F399C89B3B241A1AF0B6C0`

## Browser measurement

**VERIFIED in the local in-app browser:** BoxedWine launched
`/bin/wine cmd /c run_azrok_clean.bat`, created an 800x600 Wine window, and
reported the following one-second title samples:

```text
t=2   101 MIPS
t=3    87 MIPS
t=4   120 MIPS
t=5   122 MIPS
t=6   120 MIPS
t=7   119 MIPS
t=8   118 MIPS
t=9    38 MIPS
t=10    0 MIPS
t=11    0 MIPS
t=12  120 MIPS
t=13  114 MIPS
t=14    0 MIPS
t=15    0 MIPS
```

The client area remained white. The console directly reported absent
`winepulse.drv`/`winealsa.drv` host libraries and an unsuccessful Wineboot
attempt, but the guest resumed work after the first zero-MIPS interval.

## Gate 2c verdict update

| stage | result |
|---|---|
| (a) launch | **PASS** — named CLI and 800x600 window reached |
| (b) D3D device creation | **NOT VERIFIED** |
| (c) visible game rendering | **FAIL** — white client area |
| (d) execution/frame evidence | **CPU execution PASS; rendering frame NOT VERIFIED** — sustained 87–122 MIPS bursts, then intermittent idle |
| (e) server connection | **NOT VERIFIED** |

**VERIFIED conclusion:** the old persistent `0 MIPS` observation is not an
Azrok CPU-emulation impossibility. A clean named-CLI Azrok launch executes for
multiple seconds at roughly the same order as the 152 generic smoke and later
resumes after an idle interval. The remaining failure boundary is after guest
startup and before verified browser D3D output.

**INFERRED, not isolated:** removing the old probe/override package removed at
least one confounder. This run does not assign causality to the probe alone
because the package and launch path changed together.

## Next gate

Stop content QA here. The next highest-value proof is the host bridge:
guest `d3d9.dll` command -> BoxedWine trap -> host callback -> JavaScript,
followed by a WebGL2 clear/triangle. PatHouse/Plaza/one minigame remain only
later rendering smoke scenes.
