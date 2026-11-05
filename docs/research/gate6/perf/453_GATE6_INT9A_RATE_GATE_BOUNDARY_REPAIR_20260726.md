# 453 — INT9A rate-stability boundary repair

> Status: **VERIFIED source-contract defect and repair; prior A5/A6 rejections remain observations only.**

## Defect

The first version of the rate-stability gate called each probe with
`SceneSettleSec=0` and `WarmupSec=0`, then only afterwards invoked the official
measurement with its configured settle/warmup values.  Thus A5/A6's probe
series did not test the same temporal boundary as the official interval.  In
this run the official scene settle was zero, but the official 15-second warmup
was still absent from the probes.

That placement is a measurement-contract P0: it can reject startup/transition
behavior without proving the intended official interval is unstable.  It does
not make the raw A5/A6 probe values false, and it does not establish their
cause.

## Repair

The first preflight probe now uses the caller's exact `SceneSettleSec` and
`WarmupSec`.  Later probes are contiguous with zero extra delay.  Once an
adjacent pair passes, the official 30-second interval also starts contiguously
with zero extra delay.  Therefore the rate gate and official interval now test
one continuous post-settle/post-warmup phase rather than different phases.

PowerShell parsing succeeds.  A fresh accepted control must dynamically prove
this repaired gate before any baseline or candidate B measurement.  Candidate
B remains closed.
