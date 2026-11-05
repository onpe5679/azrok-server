# 386 ??MRG1 A-B-A(B) A1 environment precheck invalidation

Date: 2026-07-25  
Status: **VERIFIED** ??no FPS sample, no candidate verdict.

The first fresh accepted A process was correctly watcher-created and later
reached visible `1024x768`, registered 94/30,550 replay and advancing direct
Present (`42,953`, error-free async ring). Its initial 120-second sampler
readiness wait timed out *before* that late bootstrap completed, so it emitted
no timing row. A zero-settle retry was then rejected before warm-up/timing by
the required 357 HWND gate: two visible overlapping top-level windows were
directly enumerated (a YouTube Chrome window, MCP Bridge Auto, and the
After Effects window; two counted by the overlap predicate).

Edge foreground activation did not change the observed overlap. A subsequent
read-only census also found a second top-level Edge YouTube window in addition
to the watcher-created BoxedWine Edge PID. The attached sampler's isolated
process-tree requirement must reject this state rather than silently exclude a
user-owned browser. No Present duration, FPS, working-set baseline or CSV
valid row was produced. MRG1 replay is neither accepted nor rejected.

Resume only with the watcher-created Edge as the sole relevant Edge process
and no visible overlapping top-level window, then restart at a fresh accepted
A leg; do not reuse this environment for MRG1 B.

## Later read-only recheck

The state did not recover on a later direct audit. CDP still had exactly one
visible page, but the watcher Edge working set had grown from its fresh 709 MiB
to 4,246.38 MiB. Three visible non-cloaked upper z-order overlaps were then
enumerated (Chrome/YouTube, MCP Bridge Auto, and After Effects). This confirms
both the window and working-set gates remain fail-closed; it does not create a
performance row or change the MRG1 result.
