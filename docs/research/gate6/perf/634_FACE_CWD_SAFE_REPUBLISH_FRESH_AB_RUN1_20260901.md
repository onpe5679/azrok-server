# 634 — FACE CWD safe republish fresh A/B runs 1–2 and pooled rejection

> **QUALIFIED by 636; objective-level result RESOLVED by 639.** Run1/run2 used different measurement phases: r8
> controls began collecting about 0.31 s after PatHouse acceptance while r10
> candidates began about 11.66 s after acceptance following HLE warmup. The
> reported effect remains a candidate signal, not an identified pure r10
> effect. #639 supplies the authoritative prospective equal-phase proof while
> retaining the separate production-promotion drift rejection.

> **Deployment status updated by 635.** The strict A/B rejection below is
> unchanged; r10 was later deployed only as an explicit static canary, never
> as the production default.

Date: 2026-09-01 KST

## Conclusion

- **VERIFIED r9 failure attribution:** the exact CWD census reached the writer
  discovery path but recorded `confirmFailure=3`. The ordinary r9 writer
  diagnostic consequently remained unresolved instead of safely publishing a
  usable hook.
- **VERIFIED static:** the r10 safe-republish implementation passed the scoped
  guest-PEB/CWD audit with no P1 finding and all `7/7` required checks. It pins
  the Wine 11 ntdll mapping, serializes hook publication, rechecks eligibility,
  and fails closed on an unresolved writer.
- **VERIFIED UI-less actual PatHouse activation:** fresh `player / Azrok1`,
  `playable / profile_playable_v2`, server auto-select through the exact C2S
  `0x0005` handler, and Present progression admitted the scene without a UI
  button. r10 recorded hook resolved `1`, unresolved `0`, fixed-C-files
  boundary samples, warmup `256` skips / completion `1` / reset `0`, active
  FACE lookup hits, and zero relative-CWD fallback.
- **VERIFIED fresh A/B run 1 effect, NOT ADMITTED:** A1-B1-A2-B2 used fresh
  server/browser/storage legs and six exact 120-Present windows per leg. Frame
  time improved by median **16.7534%**, 10%-trimmed mean **18.0267%**, and the
  10,000-resample bootstrap 95% interval was **[14.0900%, 22.3318%]**.
  Adjacent effects were **24.7953%** and **12.6455%**.
- **VERIFIED strict rejection for run 1:** control drift was **5.4631%** and
  candidate drift **9.4167%**, both exceeding the configured `<=5%` gate.
  Therefore `acceptedFrameTime10=false` despite every central effect estimate
  exceeding 10%.
- **VERIFIED fresh A/B run 2 effect, NOT ADMITTED:** median improvement was
  **12.4651%**, trimmed mean **12.2726%**, and flat bootstrap 95% interval
  **[7.8834%, 16.1325%]**. Adjacent effects were **8.3732% / 18.1367%**;
  control/candidate drift was **3.5216% / 7.6678%**. The CI lower bound, first
  adjacent pair, and candidate drift each fail the strict gate.
- **VERIFIED pooled 48-window effect, STRICT REJECT:** pooling both runs gives
  median **14.7294%**, trimmed mean **15.1741%**, and flat bootstrap 95%
  **[12.2274%, 18.1727%]**. The run/pair-aware hierarchical interval is
  **[9.5934%, 21.9685%]**; its lower bound remains below 10%. The four adjacent
  pairs are **24.7953%, 12.6455%, 8.3732%, 18.1367%**, and pooled
  control/candidate drift is **6.0375% / 13.5097%**. The unchanged strict gate
  therefore remains `acceptedFrameTime10=false`.
- **PRODUCTION UNCHANGED / UNDEPLOYED:** r10 remains a local explicit
  diagnostic. The production FACE r5 runtime, cache, launcher, and remote
  deployment are unchanged. Any next use is **canary-only**; deployment/default
  promotion is not authorized.

## Why r10 differs from r9

r9 proved the guest CWD must be guarded, but its first writer-hook confirmation
could fail and leave the relative FACE path disabled. The census observed three
confirmation failures. r10 does not loosen the guard: it republishes only while
the exact mapped module and generation remain eligible, and otherwise keeps the
relative optimization disabled. The static audit reported no P1 finding.

## UI-less PatHouse admission contract

The measurement server used the existing playable state and no character UI:

```text
account / character       player / Azrok1
content / namespace       playable / profile_playable_v2
selection                 slot 0 via exact C2S 0x0005 handler
server follow-up          S2C 0003/0007/0005/000A/000B
client follow-up          C2S 0017/0008
scene evidence            exact server gate + fresh Present progression
```

The r10 activation gate additionally required:

```text
hookResolved              >= 1
hookUnresolved            0
relativeFallbacks         0
fixed C-files samples     > 0
warmup completion/reset   >= 1 / 0
FACE lookupHits           > 0
tail/fail-closed errors   0
```

## Fresh A/B run 1

| leg | frame ms, six 120-Present windows |
|---|---|
| A1 r8 | 24.0417, 23.4750, 23.3667, 25.8333, 26.8167, 25.9583 |
| B1 r10 | 18.9333, 21.3583, 18.5750, 19.2250, 17.9000, 18.4167 |
| A2 r8 | 22.8167, 23.2417, 24.5833, 24.0083, 23.1000, 25.0417 |
| B2 r10 | 21.6083, 20.0583, 21.1250, 20.2750, 19.9417, 21.0000 |

```text
median reduction           16.7533819%
trimmed-mean reduction     18.0266502%
bootstrap 95% CI           [14.0899654%, 22.3317574%]
adjacent A/B               24.7953216% / 12.6455026%
control drift               5.4630593%
candidate drift             9.4166667%
strict accepted             false
```

The strict gate requires median, trimmed mean, bootstrap lower bound, and every
adjacent effect to be at least 10%, while both arm drifts must be at most 5%.
Run 1 fails only the drift requirements, but that is still a complete
admission failure rather than a provisional acceptance.

## Fresh A/B run 2

Run 2 repeated the same A1-B1-A2-B2, fresh server/browser/storage, UI-less
server gate, exact identity, and six 120-Present windows per leg contract.

```text
median reduction           12.4651325%
trimmed-mean reduction     12.2725526%
flat bootstrap 95% CI      [7.8834465%, 16.1324971%]
adjacent A/B                8.3732482% / 18.1366672%
control drift               3.5216179%
candidate drift             7.6677953%
strict accepted             false
```

Run 2 fails three independent requirements: bootstrap lower bound >=10%, every
adjacent effect >=10%, and candidate drift <=5%.

## Pooled two-run result

Across 48 measured 120-Present windows, the central estimates remain above
10%. That does not override the variance contract:

```text
pooled median reduction        14.7293546%
pooled trimmed-mean reduction  15.1740992%
flat bootstrap 95% CI          [12.2273815%, 18.1727248%]
hierarchical 95% CI            [9.5934379%, 21.9685439%]
four adjacent pairs            24.7953216 / 12.6455026 / 8.3732482 / 18.1366672%
pooled control drift            6.0374740%
pooled candidate drift         13.5096643%
strict accepted                false
```

The flat resampling interval treats all windows as exchangeable and is
supplementary. The hierarchical interval preserves run/pair clustering and
crosses below 10%; one adjacent pair is also below 10%, and both pooled drift
values exceed 5%. The strict decision therefore remains reject. r10 may only
continue as an explicit canary while deployment and default selection remain
unchanged.

## Evidence

- `artifacts/performance/face_r8_vs_r10_safe_fresh_ab_20260901.json`
- `artifacts/performance/face_r8_vs_r10_safe_fresh_ab_20260901.json.legs/{A1,B1,A2,B2}.json`
- `artifacts/performance/face_r8_vs_r10_safe_fresh_ab_run2_20260901.json`
- `artifacts/performance/face_r8_vs_r10_safe_fresh_ab_run2_20260901.json.legs/{A1,B1,A2,B2}.json`
- `artifacts/performance/face_r8_vs_r10_safe_fresh_ab_pooled_20260901.json`
- `artifacts/performance/face_r10_cwd_safe_player_pathouse_20260901.json`
- `artifacts/performance/face_r10_cwd_safe_player_pathouse_20260901.json.wait-inner.json`
- `artifacts/performance/face_wis_guest_peb_cwd_static_audit_20260901.json`
- `artifacts/performance/face_r9_cwd_writer_player_pathouse_direct2_20260901.json`
- `tools/browser_diagnostics/Run-AzrokFreshAB.mjs`
- `tools/browser_diagnostics/Invoke-AzrokFreshABArm.ps1`
- `tools/browser_diagnostics/fresh-ab-r10-safe-candidate.json`
