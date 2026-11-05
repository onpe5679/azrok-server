# 452 — INT9A rate-stability gate failure observation

> Status: **VERIFIED measurement-contract observation; cause NOT VERIFIED.**

## Result

The repaired fresh accepted A6 leg reached the same clean, explicit, detached
workload tuple as 450/451.  Before any official FPS interval, the new
read-only 30-second stability preflight measured five windows:

```
164.8145 ; 32.0304 ; 41.3651 ; 37.9274 ; 35.0599 FPS
```

No adjacent pair is within the required 3% band.  The sampler therefore wrote
a `present-rate-stability` rejection and threw before the official CSV row.
A5 likewise rejected before an official row at
`177.4279 ; 46.7518 ; 39.7208`.

## Consequence

The accepted replay cannot currently establish a control baseline even after
the workload fingerprint is clean/detached and after up to five post-detach
30-second probes.  This is not a candidate result, not an INT9A rejection, and
not a browser/service block.  Candidate B remains prohibited.

The time-ordered official controls in 450 plus the A5/A6 preflight sequences
show a non-random, temporally structured rate change that crosses fresh browser
process boundaries and also exists inside a process.  This is a VERIFIED
observation only.  OS file cache, GPU shader/driver cache, server-side cache,
game-state transition, and host scheduling are possible explanations but are
all **INFERRED / NOT VERIFIED**.  No cache purge, priority change, browser
flag change, cache regeneration, or candidate load is authorized from this
observation alone.

## Next diagnostic boundary

The next work must identify a directly measurable host or rendering state that
changes with the rate, or establish an unambiguous long-settle control protocol
without weakening the ±3% A/B decision rule.  It must not consume candidate
legs while the accepted control fails this gate.
