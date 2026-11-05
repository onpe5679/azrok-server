# 385 ??MRG1 generation-2 pinned replay render

Date: 2026-07-25  
Status: **VERIFIED** ??replay render integrity only; not a performance result.

## Fresh replay proof

A watcher-fresh isolated browser opened only the MRG1 generation-2 replay URL
and was started by real pointer gesture. Before guest launch, the loader
directly reported visible/focused CSS/backing `1024x768`, guard ABI `1`,
`jitReplay=registered`, `jitReplayPair=legacy-v2`, 165 groups, 52,487 blocks,
zero patches and no pending group staging. The optional dependency trace
reached zero.

The page then completed its delayed guest/bridge bootstrap. Direct CDP
observation found `D3D9WebDebug.presents=236` and async ring
`callbacks=236`, `errors=0`, no gaps/reorders. Textarea telemetry independently
records the 120-frame Present window and submitted/reaped ring work with no
errors. This is actual replayed PatHouse render, not merely staged cache
identity or `Showing Window` liveness.

## Boundary

No 30-second capture was executed. Generation-2 MRG1 may now enter the
required per-leg fresh-process accepted-vs-MRG1 A-B-A(B) comparison. Each leg
must satisfy the 357 window/argv/working-set gate and wait through the
documented bootstrap before timing; no build or cache transform may run during
the samples.
