# 416 -- Gate 6 logical-composite32 B1 working-set gate repair (2026-07-26)

## Status

**VERIFIED B1 is not a performance row; VERIFIED sampler baseline-phase repair.
No logical-composite32 adoption/rejection exists.**

Fresh accepted A1 completed the full attached sample with 1,304 Presents in
30.015262 seconds = **43.4446 FPS**.  It was visible/focused, had zero upper
window overlap, stable outer rect/viewport, one isolated Edge tree, CSS
1024x768, and free memory 122,917.59 -> 120,802.73 MiB.  This is a valid
control observation, but it cannot be paired with B1 under the old
working-set reference phase.

The fresh private B1 passed its exact replay identity before timing, but the
sampler rejected it after the timing window without appending a performance
CSV row:

```text
old reference: A1 pre-sample working set  2,669.74 MiB
old later-leg cap (max(1.25x, +512)):      3,338 MiB
B1 post-sample working set:                4,113.32 MiB
rejection: working-set-after
```

This is fail-closed and B1's FPS is deliberately unavailable.  However, the
same valid A1 itself ended at **4,192.50 MiB**, 79.18 MiB *above* B1's rejected
post-sample value.  Therefore the old pre-sample reference compares a cold
fresh process to a loaded/settled process and can reject a candidate whose
post-scene working set is lower than its own control.  It cannot distinguish
page-lifetime accumulation from normal first-scene allocation.

The sampler now requires every later A/B leg to declare
`-PriorValidMsedgeWorkingSetPhase PostSample`; only the first fresh control A
may establish the reference, and its recorded **post-sample** working-set
value is the later-leg comparison value.  The existing 25%/+512MiB cap,
pre/post checks, rejection CSV, isolated tree, free-memory, visibility,
rect/viewport and Present-collapse gates are unchanged.  PowerShell parsing
passes.  This repair does not reopen any historical result.

## Next gate

Take a new watcher-fresh accepted A under the clarified baseline contract,
then use that A's `MsedgeWorkingSetAfterMiB`, free-memory pre value and Present
FPS for the private B1.  Do not use the rejected B1 for A-B-A or candidate
direction.  If the fresh B passes, continue fresh A and (if drift requires)
fresh B.
