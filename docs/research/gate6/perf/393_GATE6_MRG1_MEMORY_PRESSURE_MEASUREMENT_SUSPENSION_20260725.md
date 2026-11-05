# 393 -- MRG1 memory-pressure measurement suspension

> **Operational suspension SUPERSEDED by 394.** The pressure evidence and
> dual free-memory gate remain valid; the user explicitly reauthorized
> DISPLAY6 relative A/B measurement before After Effects exits.

Date: 2026-07-25  
Status: **VERIFIED** measurement eligibility correction and harness repair;
memory-pressure causality is **INFERRED**.

## Measurement disposition

The user directly measured the current machine at 19,096 MiB free of
194,192 MiB (90% used): After Effects alone held 102,737 MiB and 76 Comet
processes held 21,062 MiB. This corroborates the independently observed
roughly 8.7 GiB free-memory snapshot during the A3 dynamic census.

The historical user-measured comparison state had 113,699 MiB free and
accepted A values 54.5970 and 54.3583. The current pressure state contains
A1/A2/A3 values 44.2917/36.8466/41.9950 with much wider variation. The timing
and direction make system-memory pressure the leading explanation, but this
is an **INFERRED** correlation, not a proven causal mechanism and not a
left-display/GPU conclusion.

A1--A3 remain preserved as directly collected observations. They are now
explicitly **not eligible for any performance or candidate decision** because
the pressure condition was discovered after collection. MRG1 B was never
visited. The initiated A4 120-second-settle diagnostic was terminated on the
user's immediate instruction before it produced a timing row; it has no FPS
value and is not a sample.

## Relative free-memory gate

The attached sampler now treats system free physical memory like the existing
per-leg Edge working-set contract:

- only a fresh Control A may establish a free-memory baseline;
- later A/B legs require that baseline and reject before or after timing if
  free physical memory drops below 75% of it;
- rejected rows are durably written to a separate
  `.system-memory-rejections.csv`; accepted rows record prior/free/floor
  evidence;
- candidate B cannot establish or omit the memory baseline.

The 75% ratio is an explicit relative drift guard, not a claim that a fixed
absolute free-memory amount is sufficient. PowerShell parser validation and a
candidate-role fail-closed regression pass. No build, cache generation,
browser restart, or FPS sample will run until the user confirms After Effects
has exited and requests a new fresh A.

## Exact future invocation contract

The older 373 working-set description remains historically correct, but every
new runner invocation now selects **one mode for each independent axis**:

```powershell
# First healthy watcher-fresh Control A
Invoke-AzrokAttachedPresentSample.ps1 ... -LegRole ControlA `
  -EstablishWorkingSetBaseline -EstablishSystemMemoryBaseline ...

# Each later fresh A or B leg, using the last valid A values
Invoke-AzrokAttachedPresentSample.ps1 ... `
  -PriorValidMsedgeWorkingSetMiB <A-MiB> `
  -PriorValidSystemFreePhysicalMiB <A-free-MiB> ...
```

The runner has no committed scripted callers, so this documentation closes the
only known omission risk in human-operated A/B/A(B) use. Read-only suspension
verification still found AfterFX at 127,728.96 MiB working set and only
13,700.69 MiB system free; no sampler/build process is running, all five
service/CDP ports listen, and the sole page remains accepted A4. These are
pressure-state facts, not a new FPS observation.
