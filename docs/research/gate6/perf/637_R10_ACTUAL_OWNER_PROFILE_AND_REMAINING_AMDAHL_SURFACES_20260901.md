# 637 — r10 actual PatHouse owner profile and remaining Amdahl surfaces

Date: 2026-09-01 KST

## Conclusion

- **VERIFIED actual no-UI PatHouse:** a fresh local server, bridge, Edge storage,
  and ports admitted `player / Azrok1` through the exact preserved C2S `0x0005`
  selection handler. The 35.030745-second stamped window advanced **2,688
  Presents**, had `dataLossOccurred=false`, and produced before/after PatHouse
  PNG witnesses.
- **VERIFIED r10 identity and FACE gate:** the executed r10 JS, Wasm, and cache
  hashes were respectively `35d072...8be3`, `02b952...f268`, and
  `7fd921...9878`. The same artifact required warmup completion, resolved CWD
  hook, fixed `C:\files`, active HLE lookup hits, and every fallback/tail/reset
  counter equal to zero before it could be accepted.
- **VERIFIED exact owner join:** the post-trace re-arm selected CPU
  `0x22e7a130`, Profile `0x10`, 956 chunks, 57,796 samples, and **36,268,034 us**
  of full owner accounting. Delivery used another TID, so the authoritative
  join remains timestamp pid/tid -> unique Profile id -> ProfileChunk pid/id.
- **VERIFIED blocked-read reduction:** the exact guest libc `__read` key
  `v5-1054d1b5-96376265` owns **2,998,713 us = 8.2684%** of full owner wall.
  Under active r10 this formerly dominant surface is now below the standalone
  10% gate even under impossible complete removal.
- **VERIFIED runtime wait remap:** the old runtime's `wasm-function[697]` and
  r10's `wasm-function[705]` have the same signature, four locals, 3,137-byte
  body, and exact canonical body SHA
  `b93daee93508d0c591ddb740d45c4b045a9ebcf3c0f40c2e9f05d6b6fe12f4a6`.
  Only import ordinal, absolute memory offset, and direct callee ordinal move.
  The r10 trace records 3,565,153 us in 705 with the preserved wait call stack.
  The host analyzer now consumes this exact-Wasm evidence rather than
  hard-coding index 697.
- **VERIFIED exact coherent-family rejections:** dispatcher/JIT boundary is
  **3.7620%** full wall; current 85-key HQEMU plan is **4.7595% direct / 5.4570%
  nearest-mapped**; the entire mapped `Azrok.exe` module is **7.7844% direct /
  8.3230% nearest-mapped**; Wine D3D and ntdll direct shares are 1.8807% and
  1.8780%; the largest exact Acknex Ghidra function is 2.5765%. Every one is
  below 10% even at perfect removal.
- **VERIFIED x87 rejection:** x87-containing Acknex blocks occupy 15.4313%, but
  generated code already uses native Wasm f64. Every helper/direct-callee
  descendant combined is bounded by **1.1548%** full wall, so the containing
  block surface is not a causal x87-removal opportunity.
- **VERIFIED renderer rejection:** fixed-function pack leaf time is 4,854,630
  us = **13.8582%** marker wall, but 98.9431% overlaps owner compute. Even a
  perfect full-coverage 3.45x leaf packer saves only **9.8413%** wall; reaching
  10% requires at least 3.5919x before accounting for overlap or incomplete
  coverage. No `ASYNC_RING_FRAME`, `ring_full`, or `sync_drains` witness exists
  in the accepted trace.
- **VERIFIED no remaining admitted standalone axis:** all mapped generated
  direct leaf time (50.1284%), group capability flags (28.66–50.13%), all
  Acknex (30.3710%), branch-bearing Acknex (23.5720%), and `module-other`
  (37.5809%) cross 10% only as heterogeneous containers. Their measured causal
  removal lower bound is zero. They are search surfaces, not implementation
  candidates.
- **PRODUCTION/REMOTE UNCHANGED:** this investigation used fresh local
  diagnostic processes only. r10 remains an explicit canary and no remote or
  production file, service, or routing default changed.

## Accepted identity and window

```text
runtime stem   ...multidirectloops1facewishle1r10cwdrepublish1
runtime JS     35d072b873077702ca2d2d09bfdb78b5b1c8b9608b85d40f67520f4e78cc8be3
runtime Wasm   02b95215e12232eef772a54c0775cd057b5ea833356862082f10e11aba1ef268
cache          7fd921fe3fad86ce280360a876a6b946a2fdee718fc51a596119f2dd10ee9878

marker span    35,030,745 us
Presents       +2,688
owner CPU      0x22e7a130
Profile        0x10
samples        57,796
owner wall     36,268,034 us
data loss      false
```

The owner profile envelope exceeds the marker span slightly, as in #632. Owner
shares use the 36,268,034-us owner denominator; renderer shares use the
35,030,745-us marker denominator. The two denominators are not mixed.

## Full owner decomposition

```text
selected active                         33,268,598 us  91.7296%
exact libc __read blocked                2,998,713 us   8.2684%
idle/mailbox                                   723 us   0.0020%
mapped generated direct leaf            18,180,575 us  50.1284%
mapped generated nearest attribution    22,640,786 us  62.4263%
```

The mapped rows are mutually exclusive at the direct-leaf and nearest-mapped
accounting boundaries. They are not mutually replaceable code: 5,430 keys span
many guest modules, Ghidra functions, opcode mixes, and generated groups.

The exhaustive grouped-Wasm decomposition also closes the possibility that a
single AOT group or generic runtime-helper family was hiding a 10% surface:

```text
largest grouped module, group-0014     4.3318% direct / 4.9373% nearest
second grouped module, group-0078      2.9635% direct / 3.0517% nearest
generic runtime helpers, wait/dispatch excluded              9.3094% direct
largest Azrok.exe 64-KiB RVA bucket    1.5107% direct / 1.5107% nearest
```

The generic-helper number is deliberately a heterogeneous upper bound across
many unrelated runtime functions; even that union is below 10% before asking
how much could actually be removed.

## Exact candidate table

| Surface | Full-wall share | Perfect-removal decision |
|---|---:|---|
| remaining guest libc `__read` | 8.2684% | standalone 10 impossible |
| `wasmStartJITOp + NormalCPU::run` leaf | 3.7620% | standalone 10 impossible |
| current HQEMU 85-key plan | 4.7595% direct / 5.4570% nearest | standalone 10 impossible |
| all mapped `Azrok.exe` | 7.7844% direct / 8.3230% nearest | standalone 10 impossible |
| Wine D3D thunk | 1.8807% direct | standalone 10 impossible |
| Wine ntdll.so | 1.8780% direct | standalone 10 impossible |
| largest exact Acknex function `FUN_1004a6d0` | 2.5765% direct | standalone 10 impossible |
| x87 helper/callee descendant upper | 1.1548% | standalone 10 impossible |
| renderer pack at 3.45x | 9.8413% saving upper | standalone 10 impossible |

Top-N unions were computed at both mutually exclusive boundaries:

| Ranking | top 1 | top 10 | top 100 | Causal interpretation |
|---|---:|---:|---:|---|
| direct leaf | 1.0640% | 6.4923% | 17.4269% | top100 crosses 10 only by mixing unrelated keys |
| nearest mapped | 2.2249% | 10.4957% | 27.2119% | top10/top100 are unrelated caller containers |

The ten largest exact Acknex Ghidra functions likewise sum to 11.9213%, but
they are ten different functions and transformations; their measured common
causal-removal lower bound is zero. The largest one alone is 2.5765%. No
function, grouped module, exact multi-block plan, Azrok RVA bucket, or runtime
helper family supplies a coherent 10% lower bound.

The current exact HQEMU plan remains the only implementation-shaped
multi-block family in this profile. Expanding from that plan to every branch
block raises the containing surface to 23.5720%, but does not raise measured
dispatcher removal above 3.7620%; doing so would repeat the container fallacy.

## Comparison with the previous accepted owner trace

There is no accepted r8 owner-CPU trace artifact; r8 contributed frame-window
controls in #634. The authoritative owner-profile comparator is therefore
#632's accepted FACE owner trace, not an inferred r8 profile.

| Surface | Previous owner | r10 owner | Change |
|---|---:|---:|---:|
| blocked `__read` | 18.9104% | 8.2682% | -10.6422 pp |
| dispatcher pair | 1.5864% | 3.7620% | +2.1755 pp |
| current HQEMU plan | 4.5728% | 4.7595% | +0.1867 pp |
| mapped `Azrok.exe` | 6.6019% | 7.7844% | +1.1825 pp |
| largest Acknex function | 2.4217% | 2.5765% | +0.1548 pp |
| x87 helper/callee upper | 1.0728% | 1.1548% | +0.0821 pp |
| renderer pack leaf | 14.1347% | 13.8582% | -0.2765 pp |

r10 removes the previous profile's only exact 10%+ blocked-read surface. The
relative increases elsewhere do not create a new exact 10% candidate; the
only rows still above 10% are the already rejected mapped/x87/renderer
containers.

## Runtime wait classifier correction

The old renderer analyzer treated only `wasm-function[697]` as a runtime wait.
r10 added runtime functions, moving the identical wait body to index 705. This
made an initial host report incorrectly label the full 3.565-second wait leaf
as owner compute and report 100% renderer overlap.

The correction is fail-closed:

1. pin both Wasm SHA-256 identities;
2. compare signature, result, locals, and emitted body length;
3. canonicalize only build-relative import ordinal, absolute memory offset, and
   direct callee ordinal;
4. require exact canonical body SHA equality;
5. require the current trace call stack and exact guest `__read` key evidence;
6. pass the resulting evidence file to the host analyzer.

The corrected renderer result uses `wasm-function[705]` and reports pack/owner
overlap 98.9431%. Numeric function indices are never again treated as portable
semantic identities by this path.

## Collector and verifier hardening

`Collect-AzrokFaceOwnerTierTrace.mjs` now supports a server-state acceptance
path that records no-UI protocol evidence honestly instead of setting a DOM
nonce and labelling it human acceptance. The verifier checks account,
character, content profile, namespace, exact opcode sequence, heartbeat count,
and Present progression. It also records and validates FACE, warmup, and CWD
snapshots around the exact owner trace.

Boot-time CDP stalls, delayed worker creation, and short Present plateaus found
in rejected retries were converted into bounded retry/refresh gates. Retry 4
is the sole accepted trace; the failed attempts never entered an accepted
measurement window. Fresh local ports were verified closed after cleanup.

## Evidence

- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.verified.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.owner.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.owner_summary.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.runtime_wait_shift.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.host_renderer_profiles.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.dispatch_tier.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.candidate_families.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.direct_leaf_locality.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.x87_exact_surface.json`
- `artifacts/performance/face_r10_owner_tier_trace_player_pathouse_retry4_20260901.remaining_guest_surface.json`
- `artifacts/performance/face_prior_vs_r10_owner_surface_comparison_20260901.json`
- `artifacts/performance/20260901T032035276Z.face-owner-tier.before.png`
- `artifacts/performance/20260901T032035276Z.face-owner-tier.after.png`
- `tools/browser_diagnostics/Collect-AzrokFaceOwnerTierTrace.mjs`
- `tools/browser_diagnostics/verify-azrok-face-owner-tier-trace.mjs`
- `tools/browser_diagnostics/verify_runtime_wait_function_shift.mjs`
- `tools/browser_diagnostics/analyze_face_host_renderer_profiles.py`
- `tools/browser_diagnostics/analyze_r10_remaining_guest_surface.py`
