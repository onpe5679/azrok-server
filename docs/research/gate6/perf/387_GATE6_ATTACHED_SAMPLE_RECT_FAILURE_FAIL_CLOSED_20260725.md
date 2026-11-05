# 387 ??Attached Present sampler upper-window rect fail-closed repair

Date: 2026-07-25  
Status: **VERIFIED** ??harness hardening; no FPS result.

`Invoke-AzrokAttachedPresentSample.ps1` previously folded an upper z-order
window's `GetWindowRect` result into `$ok -and overlap`, so a native rect-query
failure could be interpreted as non-overlap. The sampler now throws immediately
for that upper HWND before evaluating visibility/DWM/overlap. This changes an
unknown compositor/window state into an invalid sample without adding a bypass
or changing any successful path.

PowerShell AST parsing passes. A real preflight against the present environment
also correctly rejected before timing with three directly enumerated visible,
unminimized, uncloaked overlap blockers: Chrome YouTube, MCP Bridge Auto and
After Effects. The watcher Edge itself is again a single descendant process
tree; only the known window overlap remains. No FPS row or candidate conclusion
was created.

The independent general browser sampler may receive the same rect-failure
hardening later; it is deliberately not mixed into this in-progress MRG1
measurement card.
