# 392 -- MRG1 low accepted-control environment census

Date: 2026-07-25  
Status: **VERIFIED** diagnostics and sampler hardening; causal attribution **NOT VERIFIED**.

## Direct A3 census

Read-only CDP and process inspection after A3 confirms that the current low
rate belongs to the accepted control itself, not to the unvisited MRG1
candidate:

- exactly one page and 51 workers; URL is accepted ABI2/current replay, not B;
- page is `visible`, `hidden=false`, and has focus; all three anti-throttling
  flags are present;
- root HWND is `(-3800,20)-(-1300,2083)`, visible/non-minimized/uncloaked;
  CDP reports DPR 1.25, display `3072x1728`, `screenX/Y=-3032,20`, outer
  `2500x2064`, inner `2478x1926`;
- direct telemetry independently reports successive 120-Present windows at
  42.50, 43.19, 45.36, and 43.10 FPS, with async ring full/errors zero;
- renderer to 9201 and bridge 9201 to 9200 connections are established, and
  no build/cache-generation process is present.

The Edge tree is about 4.317 GiB working set, including a roughly 3.80 GiB
renderer. System free physical memory was only about 8.7 GiB of 194.2 GiB
while several user applications also accumulated CPU time. This is an
environment fact and a potential confound, **not** a proven cause of the low
control rate. No user application was closed or altered.

## Static comparison boundary

The current A1/A2/A3 use the same accepted stem/cache, base game URL and
three anti-throttling flags as a retained 55.0276 control. Confirmed covariate
differences are fresh watcher profile/process per current leg versus the
retained profile, 300-second versus 120-second scene settle, and current
`2500x2063` left-display HWND versus the retained `1905x2092` HWND. The raw
359 high-control CSV no longer exists, so its exact display/DPI/working-set/
settle state cannot be recovered. None of these differences establishes
causality.

## Future-sample evidence repair

`Invoke-AzrokAttachedPresentSample.ps1` now records and requires unchanged
pre/post CDP viewport state (visible + focus, DPR, display dimensions,
screen position, outer/inner dimensions and visual scale), in addition to
the 390 Win32 outer-rect gate. It records system free physical memory before
and after each future row. The parser passes. No historical row is rewritten,
and no unmeasured absolute memory threshold is invented.

MRG1 B remains unvisited. A further fresh accepted A is meaningful only after
the control environment changes or a separately justified diagnostic is
available. The then-active 52--55 admission condition was later withdrawn by
the user; 393 preserves the low rows as memory-pressure observations and
requires a new healthy fresh A to establish the next baseline.
