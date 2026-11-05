# 394 -- MRG1 DISPLAY6 relative-comparison reopen

> **Execution deferred by 395.** The DISPLAY6 relative-comparison policy and
> sampler gates remain valid, but user-directed resource hold forbids browser
> and FPS activity until AE exits and the watcher/browser are restored.

Date: 2026-07-25  
Status: **VERIFIED** user-authorized measurement policy change; display/GPU
cause is **INFERRED**.

## Policy correction

The user withdraws the 52--55 FPS admission range. That range was observed
with Edge on the primary display and is not a valid absolute admission gate
for the isolated DISPLAY6 measurement placement. A1 `44.2917` is preserved as
the provisional DISPLAY6 accepted control, rather than discarded.

The current comparison environment is DISPLAY6 at desktop coordinates
`(-3840,0)`, with `3072x1728` browser-reported display dimensions and the
watcher placement `(-3800,20)-(-1300,2083)`. The user reports multiple GPU
adapters and monitors attached across adapters. A lower WebGL rate and the
longer readiness on DISPLAY6 are therefore plausibly caused by a different
rendering GPU path, but this is **INFERRED**: the WebGL renderer string is not
queried because making a new GL context during a performance leg would taint
the result.

The DISPLAY6 results are valid only for same-placement relative candidate
comparison. They cannot establish progress against the absolute 60/65 FPS
goal; that requires a separate primary-display measurement after candidate
disposition.

## Reopened sequence

Take fresh accepted A2, then:

1. If A1/A2 differ by at most 3%, fix their median as the DISPLAY6 accepted
   baseline. Otherwise take one more fresh accepted A before B.
2. Reject any leg below 50% of the fixed DISPLAY6 baseline as an environmental
   collapse and diagnose it before proceeding.
3. With a stable baseline, run fresh-process MRG1 B -> accepted A -> MRG1 B,
   compare adjacent A/B boundaries with the established +/-3% decision rule.

Every leg keeps 390 rect stability, viewport stability, isolated Edge tree,
anti-throttling/visibility, working-set and relative free-memory gates. The
prior A1 has no new free-memory baseline record, so fresh A2 establishes the
dual runner baselines while A1 remains the provisional FPS comparator.

## Present-collapse gate

The sampler now independently requires exactly one present-FPS mode: a fresh
Control A may establish a baseline, or a leg supplies a positive prior FPS.
After all rendering, browser and memory gates pass, a result below 50% of the
prior is written to `<OutputCsv>.performance-rejections.csv` and rejected.
Candidate B cannot establish or omit this baseline. Parser and candidate-role
fail-closed regression pass.

For A2, A1 `44.2917` supplies the provisional collapse floor `22.14585 FPS`.
This is only a collapse detector; A1/A2 +/-3% stability and the median
baseline are orchestrator decisions, not a single-row sampler assertion.

At reauthorization preflight, AfterFX still held about 127.7 GiB and free
physical memory was about 14 GiB. The user explicitly chose to proceed in
that same DISPLAY6 environment. This preserves the memory finding as a
confound and labels its causal effect **INFERRED**, but does not override the
user's authorized relative-comparison policy.
