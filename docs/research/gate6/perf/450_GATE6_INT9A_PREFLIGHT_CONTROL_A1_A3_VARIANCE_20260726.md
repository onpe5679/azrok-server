# 450 — INT9A preflight control A1–A3 variance

> Status: **VERIFIED observations; performance conclusion NOT VERIFIED.**

## Scope

This document records the first three fresh accepted-control 30-second samples
that used the 447–449 manual workload-fingerprint preflight contract.  It does
not evaluate the INT9A candidate and does not reopen any earlier replay or
render-integrity conclusion.

## Direct observations

Each leg used the accepted ABI1 replay (`94/30,550/28,944`) on a watcher-provided
fresh Edge process.  Before timing, CDP observed the exact stable tuple and an
explicit call to `azrokDetachWorkloadFingerprint()` restored the original
dispatch function:

```
1:120:21480:14158560:2109626789:0:0
```

The attached sampler independently accepted that canonical tuple, saw one
visible page, CSS `1024x768`, primary-display window `(710,20)-(1800,1590)`, no
top-level overlap, the three anti-throttling flags, complete Edge tree, and
healthy working-set/free-memory gates.  It also recorded the unchanged host
priority snapshot (`EdgeTree=AboveNormal 1; Idle 1; Normal 8`; ChatGPT has High
3) without altering it.

| leg | UTC end | Present / 30s | FPS |
| --- | --- | ---: | ---: |
| A1 | 00:59:17 | 787 | 26.2236 |
| A2 | 01:27:25 | 2,872 | 95.7204 |
| A3 | 01:35:16 | 3,301 | 110.0058 |

All three rows are valid **structural** samples in
`artifacts/performance/int9a_specialized_primary_20260726.csv`.  The A1/A2 and
A2/A3 differences exceed the 3% stability band by a large margin.  Therefore
the accepted control baseline is not established, none of these rows may be
used for an A/B effect, and the candidate B leg is not authorized yet.  The
next action is another fresh accepted A control under the identical preflight
contract.

## Interpretation boundary

The common preflight tuple rules out the particular command-shape mismatch it
measures; it is not semantic scene identity or an explanation for the FPS
spread.  The previously measured host-priority asymmetry remains a VERIFIED
host-state observation but is **NOT VERIFIED** as a cause.  No host priority,
browser flag, cache, build, or asset was changed during these samples.
