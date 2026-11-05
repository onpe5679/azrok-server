# 388 ??Fresh-browser watcher window-placement contract

Date: 2026-07-25  
Status: **VERIFIED** ??measurement environment repair; no FPS result.

The user moved the prior measurement Edge to the non-overlapping left monitor,
but a subsequent `RESTART_REQUEST` necessarily killed that prior process. The
running watcher then created its fresh replacement at the default primary
monitor location, where it overlapped user windows. Direct Win32 inspection
confirmed the new watcher Edge HWND on the primary monitor; attempting to move
that HWND from this process failed with Win32 access denied (5). No timing was
started from this state.

The watcher source now accepts an optional paired `-WindowLeft` and
`-WindowTop` parameter and appends the standard Edge
`--window-position=X,Y` argument only when both are supplied. A one-sided
coordinate is fail-closed. Parser validation passes. This edit does **not**
affect the already-running watcher process; it must be human-relaunched with,
for the verified left monitor placement, `-WindowLeft -2211 -WindowTop 241`.

After that human-owned watcher restart, each `RESTART_REQUEST` can provide a
fresh Edge directly on the isolated monitor, preserving the per-leg fresh
process rule without closing/minimizing unrelated user windows. MRG1 A-B-A(B)
remains unmeasured.
