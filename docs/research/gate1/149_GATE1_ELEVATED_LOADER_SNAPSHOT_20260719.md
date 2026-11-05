# 149 Gate 1 elevated loader snapshot (2026-07-19)

## Purpose

`148_GATE1_ARGPROBE_LOAD_FAILURE_20260719.md` established that an unchanged
`d3d9_probe.log` cannot prove whether the expanded proxy DLL loaded.  This
adds the smallest direct observation needed before another renderer run:
Windows' own module snapshot for the already-running elevated client.

## Implementation

**VERIFIED (source review and local helper execution):**

- `tools/snapshot_azrok_modules.py` calls
  `CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)` and
  enumerates `MODULEENTRY32W` records.  It is read-only: it does not attach a
  debugger, suspend the process, read process memory, or modify files.
- `tools/invoke_azrok_module_snapshot.ps1` uses the established
  `Azrok-Plaza-Stop` scheduled-task boundary.  The request pins PID, immutable
  start time, and an output path below `artifacts/`.
- The elevated handler validates that the selected image is exactly this
  workspace's `Azrok.exe`, validates the start time and output path again,
  then invokes only the checked-in snapshot helper.
- The helper was exercised without starting Azrok: a temporary Python process
  loaded `C:\Windows\System32\d3d9.dll`, and the snapshot returned exactly
  one `d3d9.dll` record at that path.  See
  `artifacts/dynamic-analysis/loader_module_snapshot_d3d9_filter_selftest_20260719.json`.

## Live observation

**VERIFIED (PID 166636):** Windows mapped both members of the expected native
proxy chain:

```text
<home>\Documents\<project-dir>\Azrok_Plaza\d3d9.dll
C:\Windows\SysWOW64\d3d9.dll
```

The application-local module is the deployed flushprobe; the system module is
the real D3D9 target loaded by the proxy. The original helper incorrectly set
`d3d9_loaded=false` when more than one same-named module was present. That
uniqueness assumption is now removed: the JSON records `d3d9_count` and treats
one-or-more mappings as loaded.

Evidence: `artifacts/d3d9_probe/20260719_gate1_argflush_pathouse/loader_module_snapshot.json`.

## Reusable procedure

For the next native argprobe attempt, first place the candidate DLL beside
`Azrok.exe`, launch only to first rendered PatHouse, and invoke:

```powershell
tools\invoke_azrok_module_snapshot.ps1 -ProcessId <Azrok PID>
```

The resulting JSON is the decision point:

- a `d3d9.dll` record whose `path` equals the workspace candidate proves
  Windows mapped that exact loader path; a second system record is expected
  for a functioning proxy chain;
- a system/dgVoodoo path or no record disproves the deployment path;
- a snapshot error is a measurement failure, not a proxy-load conclusion.

Only after that observation should the smallest rendering route needed by the
current web-backend question be used for an argument histogram.
