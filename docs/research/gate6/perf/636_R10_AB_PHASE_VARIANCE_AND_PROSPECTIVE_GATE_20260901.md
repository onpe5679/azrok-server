# 636 — r10 A/B phase variance attribution and prospective equal-phase result

> **OBJECTIVE-LEVEL RESULT RESOLVED by 639.** The strict production admission
> rejection below remains true; #639 separately proves the requested >10%
> performance objective from this prospective evidence.

Date: 2026-09-01 KST

## Conclusion

- **VERIFIED:** #634 run1/run2 did not measure the same PatHouse phase. The four
  r8 control collectors began a median **0.3135 s** after the server/Present
  acceptance gate; the four r10 collectors began **11.658 s** after it. The
  median skew was **11.3445 s**.
- **VERIFIED:** r8 first accepted windows still contained `145872–192749` JIT
  warmup blocks (and two second windows contained `28251/52609`). r10 waited
  for FACE warmup completion before measurement and its accepted windows were
  already steady. Thus condition, HLE activation, WIS removal, and measurement
  phase are confounded in the legacy runs.
- **QUALIFIES 634:** pooled **14.7294%** remains a candidate signal but is not an
  identified pure r10 effect. A post-hoc common-age sensitivity slice
  (`15–23 s`, warmup blocks `<=10000`) retained median **13.5646%** reduction,
  but its flat bootstrap 95% interval was **[7.5397%, 20.0098%]**. It cannot
  admit the candidate because the slice was defined after observing the data.
- **VERIFIED IMPLEMENTED/TESTED:** the fresh A/B collector now supports an
  identical fail-closed phase contract for both arms: PatHouse acceptance age
  `>=25000 ms` (requested minimum `>=15000 ms`), Present delta `>=600`,
  start lateness `<=3000 ms`, every
  accepted 120-Present window `warmup_blocks<=10000`, `pending_blocks<=100`,
  and `nojit_blocks=0`. The pending upper bound was frozen after A1 setup but
  before any candidate/effect result: A1 maximum 68 was below 0.011% of its
  roughly 600k JIT blocks. This threshold must not change after prospective
  comparison begins. The collector supports 30 accepted base windows per leg
  for six non-overlapping 600-Present superwindows.
- **VERIFIED PROSPECTIVE EFFECT / STRICT REJECT:** A1/B1/A2/B2 each supplied 30
  accepted 120-Present windows. The fixed five-window aggregation produced six
  600-Present superwindows per leg. Median frame-time reduction was
  **18.5468%**, mean reduction **19.8282%**, and flat bootstrap 95% interval
  **[15.5776%, 24.0639%]**. Adjacent A1/B1 and A2/B2 reductions were
  **22.4239% / 17.2796%**.
- **VERIFIED STRICT REJECTION:** control-arm superwindow drift was **6.6488%**,
  above the frozen `<=5%` gate; candidate drift was **0.1135%**. Base-window
  results independently showed median **19.7703%**, CI
  **[17.7701%, 21.7534%]**, and adjacent **20.7270% / 18.1450%**, but control
  drift was likewise **5.6112%**. `acceptedFrameTime10=false` remains correct.
- **VERIFIED CONTRACT:** all legs began at `25023–25081 ms` after PatHouse
  acceptance (median A/B skew **0.0045 s**), with Present delta `783–968`.
  Every leg had `30/30` windows, loss/errors zero, max warmup `8716–8956`, max
  pending `67–68`, and no-JIT zero. B1 FACE hit `3686/3689`, B2 `3708/3711`;
  both controls correctly had zero lookup activity.
- **VERIFIED REJECTED ATTEMPTS:** profiler contamination, original 15 s gate
  lateness, and the `remainingGauge` validation bug were each rejected before
  admission and recorded as NOT ACCEPTED. Raw-leg preservation was added
  before final validation; A1 raw was revalidated under the effect-blind frozen
  pending `<=100` contract before B1 began.
- **Production/default changed:** no.

## Direct evidence

Legacy window-level analysis:

- `artifacts/performance/face_r8_vs_r10_variance_attribution_20260901.json`
- source legs under
  `face_r8_vs_r10_safe_fresh_ab_20260901.json.legs/` and
  `face_r8_vs_r10_safe_fresh_ab_r2_20260901.json.legs/`

Contaminated attempt marker:

- `artifacts/performance/face_r8_vs_r10_phasegated30_attempt1_NOT_ACCEPTED_20260901.json`
- `artifacts/performance/face_r8_vs_r10_phasegated30_attempt2_NOT_ACCEPTED_20260901.json`
- `artifacts/performance/face_r8_vs_r10_phasegated30_attempt3_NOT_ACCEPTED_20260901.json`

Prospective result:

- `artifacts/performance/face_r8_vs_r10_phasegated30_attempt4_fresh_ab_20260901.json`
- `artifacts/performance/face_r8_vs_r10_phasegated30_attempt4_fresh_ab_20260901.json.legs/{A1,B1,A2,B2}.json`
- `artifacts/performance/face_r8_vs_r10_phasegated30_attempt4_superwindow_analysis_20260901.json`

Implemented prospective gate:

- `tools/browser_diagnostics/Collect-AzrokFaceOwnerReadwaitCombined.mjs`
- `tools/browser_diagnostics/Collect-AzrokWaitSharedSnapshot.mjs`
- `tools/browser_diagnostics/Invoke-AzrokFreshABArm.ps1`
- `tools/browser_diagnostics/Run-AzrokFreshAB.mjs`
- `tools/browser_diagnostics/fresh-ab-r8-control.example.json`
- `tools/browser_diagnostics/fresh-ab-r10-safe-candidate.json`
- `tools/browser_diagnostics/analyze_r10_fresh_ab_variance.py`

## Verification

The following passed after the gate changes:

```text
node tools/browser_diagnostics/test-azrok-face-owner-readwait-combined.mjs
node tools/browser_diagnostics/test-azrok-fresh-ab-runner.mjs
node tools/browser_diagnostics/Collect-AzrokWaitSharedSnapshot.mjs --self-test
python -m py_compile tools/browser_diagnostics/analyze_r10_fresh_ab_variance.py
PowerShell parse of Invoke-AzrokFreshABArm.ps1
JSON parse of both prospective arm configs
```

## Prospective admission rule

The fresh run satisfies all phase/stability contracts, but the frozen arm-drift
gate rejects it. Thirty base windows are grouped in fixed order as six
600-Present superwindows per leg. The strong central effect and CI are evidence
that r10 is promising, not authorization to waive drift or change production.
Legacy runs without `measurementPhaseGate` never satisfy this contract.
