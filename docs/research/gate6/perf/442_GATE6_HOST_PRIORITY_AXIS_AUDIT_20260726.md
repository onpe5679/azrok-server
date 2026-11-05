# 442. Host process-priority axis audit

Date: 2026-07-26  
Status: **VERIFIED host configuration/snapshot; causality is NOT VERIFIED**

## Direct host evidence

`docs/research/_salvage/monitoring/boost.ps1` was read directly. Its runtime
target list is exactly:

```powershell
$names = @('ChatGPT', 'chrome')
```

It disables EcoQoS and may set High priority for those processes; it does not
open, alter, or prioritize `msedge`. Its comment still calls those processes
game-hosting renderers, an assumption that predates the current Edge renderer.

A direct `Win32_Process` priority snapshot while the fresh diagnostic Edge
tree was alive found:

| image | count | priority distribution |
|---|---:|---|
| ChatGPT.exe | 12 | High 3, AboveNormal 1, Normal 8 |
| chrome.exe | 9 | AboveNormal 1, Normal 8 |
| msedge.exe | 8 | AboveNormal 1, Normal 6, Idle 1 |

The actual Edge root process was Normal; its tree also included one Idle child.
This independently verifies that current measurement hygiene did not record a
host CPU-priority distribution, despite checking window placement, overlap,
memory, process tree, and Present collapse.

## Decision

No host priority has been changed. The supplied historical 30-second sample
end times do not overlap the monitoring execution itself, and the priority
state persists beyond a monitoring pulse. However, the snapshot alone does
not establish that priority asymmetry caused A3's 27.2212 FPS or B2's 104.7108
because A4 recovered under the same persistent asymmetry. Therefore causal
attribution is **NOT VERIFIED** and 437 remains inconclusive.

Future attached FPS rows must record, before and after the window, a
role-neutral `Win32_Process` priority distribution for the complete Edge tree
and competing ChatGPT/chrome processes. This is a diagnostic record first, not
an uncalibrated rejection threshold. Any user-approved priority change creates
a new measurement epoch and requires new accepted controls before comparison.
