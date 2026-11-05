# 152 — Gate 2c scheduler and Wine GUI smoke (2026-07-19)

## Scope

This is the cheapest orthogonal test of the previous Azrok-specific white
screen / 0 MIPS / empty-probe observation. It intentionally contains no
Azrok binary, D3D9 DLL, probe, `WINEDLLOVERRIDES`, server, or game content.

Per user direction, content validation is now bounded to rendering proof only:
PatHouse, Plaza, and at most one representative minigame, using only the one
or two locations needed by the current renderer question. Exhaustive gameplay,
cooking, library, quest, sound, and feature QA are outside the web-port gate.

## Pinned smoke payload

**VERIFIED:** `tools/boxedwine_local/apps/Gate2c_smoke.zip` is 246 bytes,
SHA-256 `17661BF7751DACE2AAC259A944CDD31A15B3DF9EF8C755F9AF81991A9BBEA95F`,
and contains only `run_smoke.bat`.

The batch prints start/end markers and executes a 100,000-iteration integer
loop through `/bin/wine cmd /c run_smoke.bat`. It does not contain or load
`Azrok.exe` or `d3d9.dll`.

## Browser observations

### Command/x86 execution

**VERIFIED live:** the local Emscripten harness printed all markers:

```text
GATE2C_SMOKE_BEGIN
GATE2C_CMD_OK
GATE2C_LOOP_OK=100000
GATE2C_SMOKE_END
```

The browser title reached **BoxedWine 135 MIPS** while the loop ran. After the
batch completed it returned to **0 MIPS**, which is the expected idle state
when no guest thread remains scheduled. Therefore a stable 0 MIPS reading is
not a CPU benchmark by itself.

### Wine GUI path

**VERIFIED live:** the same root/overlay/WASM harness launched
`c:/windows/system32/notepad.exe`. The browser title reached **91 MIPS**, the
console reported `Creating Window: 800x600`, and the canvas visibly rendered
the Wine Notepad window with menu bar and editable client area.

Both runs printed the old-root warning:

```text
wine: cannot find L"C:\\windows\\system32\\wineboot.exe"
err:process:start_wineboot failed to start wineboot, err 2
```

The command markers and Notepad window appeared after the warning, so it is
not fatal to these two smoke paths.

## Conclusion

**VERIFIED:** the Gate 2c Emscripten scheduler, x86 execution, Wine `cmd`, and
Wine GUI/GDI canvas path are operational. The earlier Azrok white screen / 0
MIPS / empty probe remains a valid observation of that Azrok package, but it
cannot be attributed to generic BoxedWine browser bootstrap or a dead guest
scheduler.

The remaining boundary is now Azrok-specific packaging/startup, especially
the bundled native D3D9 probe plus `WINEDLLOVERRIDES=d3d9=n,b`, followed by the
absence of an Emscripten 3D backend. The next 2c run must remove both the probe
DLL and override before interpreting MIPS or D3D behavior.

## Artifacts

- `tools/boxedwine_local/index_smoke.html`
- `tools/boxedwine_local/index_notepad.html`
- `tools/boxedwine_local/run_smoke.bat`
- `tools/boxedwine_local/apps/Gate2c_smoke.zip`

