# Gate 1 argument-probe deployment failure (2026-07-19)

> **SUPERSEDED by 149 and 154 for the completed measurement path.** This aborted
> detach-only run remains valid history; the loader path is now directly
> verified and periodic Present checkpoints preserve partial histograms.

## Scope

This is a **measurement failure record**, not a new content-validation run.
The expanded x86 `d3d9_argprobe.dll` was placed beside `Azrok.exe` as
`d3d9.dll`, then one native Windows session reached PatHouse, Plaza, a
protocol-controlled natural OX round, and cooking-academy room entry. The
session was stopped after room-render confirmation; no additional cooking QA
was attempted.

## Result

**VERIFIED:** no new argument-distribution result was produced.

- The only root `d3d9_probe.log` remained the prior Gate 1 file: 7,323 bytes,
  last-write `2026-07-19 01:20:26 KST`.
- The CUA and `WM_CLOSE` close requests were ignored by the client. The
  selected instance was finally stopped to release the loaded DLL for restore,
  so `DLL_PROCESS_DETACH` was **not** a valid expected write point.
- Therefore no call counts or histogram entries from this run may be compared
  with Gate 1 or used to size the browser ABI.
- The original dgVoodoo `d3d9.dll` was restored after the selected client
  exited. Source and restored SHA-256 both equal
  `B7401378B2B8E8C18C88A033E77C3EE99F4C7D2AC8CFCC949D79C1DD7FA99767`.

## Interpretation

**NOT VERIFIED:** this aborted run provides no evidence either way about
whether the expanded DLL loaded. Because it did not finish through a normal
detach path, the unchanged logfile cannot distinguish "not loaded" from a
working probe that never reached `DLL_PROCESS_DETACH`. The prior assertion
that copying the DLL beside the EXE is sufficient for this elevated launch
path is therefore not reusable evidence.

## Next narrow measurement

Before any rerun, use one direct loader observation on a fresh native client
(module list or loader trace) to prove the exact loaded `d3d9.dll` path. Do
not repeat content traversal for this question. After load-path proof, run the
minimum rendering route only: PatHouse -> Plaza -> one OX round, then normal
exit and collect the histogram.

## Boundary

The purpose of Gate 1 is browser-renderer requirements. Content gameplay is
out of scope except for the minimal scene coverage needed to exercise that
renderer.
