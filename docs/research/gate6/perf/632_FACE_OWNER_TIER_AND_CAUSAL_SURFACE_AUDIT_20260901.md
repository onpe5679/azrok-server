# 632 — FACE-on exact owner/tier window and causal 10% surface audit

Date: 2026-09-01 KST

## Conclusion

- **VERIFIED actual PatHouse window:** a separately named FACE+owner diagnostic
  reached the original 3D room through the preserved `player` account's
  canonical `Azrok1` slot and the server's verified C2S `0x0005` selection
  handler. Pre-arm, before, and after PNGs show the room, orange rug,
  furniture, pink character, HUD, status bars, clock, and menu. The accepted
  trace advanced 2,683 Presents, lost no trace data, and retained zero page
  runtime errors.
- **VERIFIED exact owner join:** the post-`Tracing.start` owner stamp selected
  CPU `0x1edd7340`, Profile `0xc`, and 953 chunks by `(pid, Profile.id)` even
  though delivery used another TID. It yielded 58,679 samples and 36,319,446
  us of owner-profile wall accounting.
- **VERIFIED dispatcher rejection:** exact runtime-Wasm body witnesses identify
  `wasmStartJITOp` and `NormalCPU::run`. Their mutually exclusive leaf sum is
  576,184 us = **1.586434%** of full owner wall; impossible complete removal
  gives only +1.612007%. Dispatcher/JIT-boundary work is not a standalone 10%
  candidate.
- **VERIFIED current HQEMU-plan rejection:** the 91-block plan maps 83 keys and
  owns 1,660,833 us = **4.572848%** direct leaf (5.253023% inclusive ceiling).
  Complete removal cannot reach 10%.
- **VERIFIED V8 compilation rejection / NOT IDENTIFIABLE per function:** the
  same marker window contains 24 baseline and 67 top-tier tasks, but Chrome
  omits a comparable module/function identity from top-tier events. `67/24`
  is not a tier-up reach rate. Baseline+top-tier compilation is only 39.623 ms
  / 35.036411 s = **0.113091%**; a deliberately generous outer envelope is
  0.126837%. Compilation overhead is rejected, while generated TurboFan code's
  steady-state quality is not inferred from these events.
- **VERIFIED x87 rejection:** x87-containing exact blocks own 14.076189%, but
  actual group bodies already use native Wasm `f64` load/store/promote and
  arithmetic. The descendant helper/callee upper is only 389,622 us =
  **1.072764%**. Static helper membership was a containing-block illusion;
  removing every helper still cannot produce 10%.
- **VERIFIED renderer bounds / NOT VERIFIED criticality:** `CrRendererMain`
  has fixed-function packing leaf time 4,952,294 us = **14.1347%** of the
  35.036411-second marker span, but 98.955% of packing intervals overlap owner
  compute and the trace has no ring-full/drain/backpressure witness. Named GL
  draw calls are only 32.400 ms; applying #615's 44.7059% call reduction to
  those calls saves at most 0.04134% wall. Multi-draw is rejected. Even a
  perfect 3.45x packing acceleration has only a 10.0377% non-critical upper
  with 0.0377 percentage-point margin, so it is supplemental rather than an
  independent 10% candidate. The rejected `uboDirtySplit` remains rejected.
- **VERIFIED remaining residency surface / NOT VERIFIED removability:** the
  exact owner profile contains 6,868,163 us = **18.910429%** in the libc
  `__read` block. FACE counters show only five original-loader misses after
  excluding 47 HLE hits. Applying the prior directly measured six reads per
  lifecycle and 23 ms maximum gives a conditional WIS upper of 690,000 us =
  1.89981%, leaving a conditional non-WIS lower of 17.01062%. The current trace
  lacks fd/path/request identity, so strict current bounds remain
  0..6,868,163 us and causal removability remains zero until a combined
  FACE+owner+readwait join is measured.
- **PRODUCTION UNCHANGED:** the deployed FACE r5 runtime/cache and launcher
  remain byte-identical. All owner/read/tier assets here are local diagnostics.

## Accepted diagnostic identity

```text
runtime stem  boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1facewishle1ownerthread1
JS SHA        dfd6d569baa8f59ac36c0d1b9a700d25f84ae51d47718eb4680ccc353d48d908
Wasm SHA      26018e9c8f0d6b383c564dc5283ea56b02b2ab0f210299a9c994f0b79ac70508
cache SHA     28bf6e58bbd59665c55a364a97490039cec90730e9adbbcf8858baccd1982997
manifest SHA  abb11a57925603a7589dd70bc9ec3a3a99d908f78a93f16967cfa698e8e379e9
groups/keys/patches 143 / 44,395 / 33,912
reloc/owner/stamp    12984904 / 12984888 / 12984892
```

The loader requires all three explicit diagnostic switches and validates the
runtime, archive, manifest, group 0010/0082/0140 bytes, owner semantics, FACE
semantics, and relocation rebase. The production default remains FACE r5.

## Exact window

```text
marker span                 35,036,411 us
owner profile wall          36,319,446 us
selected compute            29,451,283 us
excluded blocked read        6,868,163 us
mapped direct leaf          16,973,430 us / 46.733725%
Presents                     +2,683
data loss                    false
window errors                0
```

Owner-profile summed deltas include the profiler start/stop envelope outside
the marker span; owner percentages use 36,319,446 us. Renderer percentages use
35,036,411 us. These denominators are not mixed.

## Exact candidate accounting

| Surface | Direct/exclusive share | Decision |
|---|---:|---|
| Dispatcher runtime pair | 1.586434% owner wall | standalone 10 impossible |
| Current HQEMU plan union | 4.572848% owner wall | standalone 10 impossible |
| Acknex x87 blocks | 14.076189% owner wall | native f64; causal helper upper 1.072764% |
| Acknex branch-bearing blocks | 21.285036% owner wall | containing-block upper only |
| All mapped generated blocks | 46.733725% owner wall | heterogeneous container only |
| FACE-on blocked `__read` | 18.910429% owner wall | exact residency, removable lower 0 |
| Renderer fixed-function pack leaf | 14.1347% marker wall | concurrent/non-critical upper |
| Named GL draw host calls | 0.09248% marker wall | multi-draw 10 impossible |

The only exact-key set above the 20% search threshold is branch-containing
block membership. A sample attributed to one block includes all guest
instructions in it, not just its branch or tail. Treating the full 21.285036%
as dispatcher-removable would repeat the container fallacy. The directly
body-identified dispatcher pair is the authoritative causal boundary.

## V8 tier boundary

`wasm.CompileBaseline` includes module-local `funcIndex` and body size, but the
same index appears with incompatible sizes across modules. All 67
`wasm.TopTierCompilation` rows have empty args and no linking id. Compilation
chunks, `OnFinishedUnits`, `AddCompiledCode`, `PublishCode`, and `LogCode` do
not join top tier to a baseline module/function cohort. Exact per-function
Liftoff-to-TurboFan reach is therefore **NOT IDENTIFIABLE** in this schema.

## Next gate

The next diagnostic combines readwait3's shared-seqlock publisher with the
exact FACE+owner runtime. It must preserve current identities, reach visually
confirmed PatHouse, and join the conditional 17% non-WIS surface to current
fd/object/path and Wine request id in the same window. No Wine request fast
path is admitted from residency alone. A request family must prove at least
10% full-wall causal removability before implementation and then pass a
fresh-process visual PatHouse A/B.

## Evidence

- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.verified.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.owner.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.owner_summary.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.dispatch_tier.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.candidate_families.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.direct_leaf_locality.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.x87_exact_surface.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.tier_forensics.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.host_renderer_profiles.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.blocked_read.json`
- `artifacts/performance/face_owner_tier_trace_player_pathouse_20260901.blocked_read_bounds.json`
- `tools/browser_diagnostics/Collect-AzrokFaceOwnerTierTrace.mjs`
- `tools/browser_diagnostics/verify-azrok-face-owner-tier-trace.mjs`
- `tools/browser_diagnostics/analyze-azrok-face-owner-window.mjs`
- `tools/browser_diagnostics/analyze_azrok_time_weighted_candidate_families.py`
- `tools/browser_diagnostics/analyze_azrok_direct_leaf_locality.py`
- `tools/browser_diagnostics/analyze_azrok_x87_exact_surface.py`
- `tools/browser_diagnostics/analyze_face_owner_tier_forensics.py`
- `tools/browser_diagnostics/analyze_face_host_renderer_profiles.py`
- `tools/browser_diagnostics/analyze_azrok_owner_blocked_read.py`
- `tools/browser_diagnostics/analyze_azrok_face_blocked_read_bounds.py`
