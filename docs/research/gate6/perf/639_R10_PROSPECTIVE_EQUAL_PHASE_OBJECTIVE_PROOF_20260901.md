# 639 — r10 prospective equal-phase objective proof

Date: 2026-09-01 KST

## Conclusion

- **VERIFIED OBJECTIVE ACHIEVED:** r10 reduced actual PatHouse frame time by
  substantially more than 10% under a prospective, equal-phase, fresh-process
  A1/B1/A2/B2 experiment. The fixed 600-Present superwindow result was median
  **18.5468%**, mean **19.8282%**, flat bootstrap 95% interval
  **[15.5776%, 24.0639%]**, and hierarchical bootstrap 95% interval
  **[14.8564%, 24.7683%]**.
- **VERIFIED REPLICATION:** both paired legs independently exceeded 10%:
  A1/B1 **22.4239%**, A2/B2 **17.2796%**. This is not a single lucky pair or a
  120-Present transient.
- **VERIFIED CANDIDATE STABILITY:** r10 candidate drift was **0.1135%** across
  600-Present arms and **2.4131%** across base-window arms. B1 recorded FACE
  lookup hits **3686/3689** and B2 **3708/3711** with active-HLE mode.
- **VERIFIED EQUAL PHASE / INTEGRITY:** all four legs used fresh
  server/browser/storage. Measurement began at `25023–25081 ms` after exact
  server C2S `0x0005` PatHouse acceptance; median A/B start skew was only
  **0.0045 s**. Each leg supplied `30/30` exact 120-Present windows with
  sequence gaps, truncations, overflows, validation errors, and no-JIT blocks
  all zero. Max warmup was `8716–8956 <=10000`; max pending was
  `67–68 <=100`.
- **VERIFIED BASE-WINDOW CROSS-CHECK:** all 120 base windows independently gave
  median **19.7703%**, trimmed mean **19.7673%**, bootstrap 95% interval
  **[17.7701%, 21.7534%]**, and paired effects **20.7270% / 18.1450%**.
- **PRODUCTION PROMOTION POLICY STILL FALSE:** admission-v1 also requires both
  arms' cross-leg drift `<=5%`. Control drift was **6.6488%** at superwindow
  level and **5.6112%** at base-window level, so
  `acceptedFrameTime10=false` remains correct. Candidate drift passed. This is
  a control-repeatability/promotion-policy failure, not a failure of the
  candidate effect, candidate stability, or the user's objective-level >10%
  requirement.
- **Production/default changed:** no. r10 remains an explicit canary; this
  document does not waive the production-promotion policy.

## Frozen prospective contract

The contract was fixed before any candidate/effect result:

```text
PatHouse scene age >= 25000 ms (requested minimum >=15000 ms)
Present delta >= 600
start lateness <= 3000 ms
warmup_blocks <= 10000 per accepted base window
pending_blocks <= 100 per accepted base window
nojit_blocks == 0
30 accepted 120-Present windows per leg
5 consecutive base windows per 600-Present superwindow
6 superwindows per leg
```

The pending bound was frozen after observing only the A1 setup maximum `68`
(less than 0.011% of roughly 600k JIT blocks), before B1 or any A/B effect was
available, and was not changed afterward.

## Authoritative evidence

- Experiment/report:
  `artifacts/performance/face_r8_vs_r10_phasegated30_attempt4_fresh_ab_20260901.json`
- Four validated legs and pre-validation raw copies:
  `artifacts/performance/face_r8_vs_r10_phasegated30_attempt4_fresh_ab_20260901.json.legs/`
- Fixed superwindow and bootstrap analysis:
  `artifacts/performance/face_r8_vs_r10_phasegated30_attempt4_superwindow_analysis_20260901.json`
- Legacy phase-confound attribution:
  `artifacts/performance/face_r8_vs_r10_variance_attribution_20260901.json`
- Rejected pre-evidence attempts:
  `artifacts/performance/face_r8_vs_r10_phasegated30_attempt{1,2,3}_NOT_ACCEPTED_20260901.json`

## Interpretation boundary

#634's legacy effect could not identify r10 because control and candidate began
11.3445 seconds apart. #636 corrected that benchmark and retained the strict
admission policy. This document resolves the narrower but central objective:
the implemented r10 candidate itself produces a reproducible, prospective,
actual-PatHouse frame-time improvement whose central estimates, both paired
replications, and both bootstrap lower bounds all exceed 10%.
