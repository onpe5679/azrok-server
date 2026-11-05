# 451 — INT9A manual-preflight rate-stability gate

> Status: **VERIFIED diagnostic observation and source gate; performance result NOT VERIFIED.**

## Trigger

Fresh accepted A4 passed every existing structural gate and the same explicit
clean/detached workload tuple as 450, yet its official 30-second interval was
`3,647 / 30.005680s = 121.5437 FPS`.  That is again outside A3's 110.0058 FPS
by more than 3%, so the candidate remains unmeasured.

Immediately after that interval, read-only CDP Present deltas on the *same*
already-detached A4 process were:

| diagnostic window | Present FPS |
| --- | ---: |
| 1 | 41.8415 |
| 2 | 38.3207 |
| 3 | 38.0131 |

This directly proves that the prior 15-second warmup plus a matching command
shape did not ensure a stable Present rate.  It does not prove why the rate
changed, nor does it invalidate the structural contract.

## Fail-closed repair

`Invoke-AzrokAttachedPresentSample.ps1` now runs read-only post-detach
rate-stability probes before every official 30-second interval.  The default
requires two adjacent 30-second probes within 3%; it permits at most five
probes so the directly observed multi-window transition can settle.  A failure writes a
`present-rate-stability` rejection row and throws before the official FPS row.
The output records all probe rates and the accepted adjacent pair.

The first fresh execution of this gate (A5) fail-closed before any official
FPS sample: its three originally allowed probes were `177.4279/46.7518/39.7208`
FPS.  Thus the initial cap of three was itself insufficient for this observed
transition; the cap was raised to five without relaxing the 3% adjacent-pair
criterion.  The rejection is retained in the performance-rejections CSV.

Static PowerShell parsing succeeds.  The next fresh accepted control must use
this gate and establish a new Present baseline only after it passes.  No
candidate B measurement is authorized until a second fresh accepted control
reproduces that baseline within the same 3% band.
