# 313 - MT generated-Wasm helper-family census

## Question

After the `getZF()` correctness repair, which remaining generated-Wasm to C++
helper family is actually hot in stable PatHouse? Existing dispatch records show
that `fetchNextOp` is already JIT-backed 99.47% of the time, so another
dispatcher edge optimization is not justified without direct helper evidence.

## Preserved evidence - VERIFIED

- `abi2freezecontrol1-record-20260724-080517.zip` ends at
  `fetchNext=345,000,000`, target-jit `343,173,559` (99.47060%), no-flag
  `1,826,441` (0.52940%), and zero interior/null/no-table/pfn/other/yield.
- The current profiler already categorizes helper entries, but its helper-call
  statistics are intentionally disabled under `BOXEDWINE_MULTI_THREADED` and
  sampled timing is not valid for this decision.
- Condition coverage is already directly measured by 310. This census retains
  `cond` only as a cross-check and does not reopen rejected condition cards.

## Diagnostic contract - VERIFIED static/build/browser

A private accepted-ABI2-shaped, cache-OFF-only runtime will expose an explicit
process-lifetime atomic U64 snapshot for exactly these families:
`mem_r`, `mem_w`, `mem_wc`, `fetch_next`, `emulate`, `flags`, `cond`, `x87`,
`sse`, `movsd32r`, `enter`; and four details: `cache_float`, `movsd_xmm_e64`,
`movsd_e64_xmm`, `movsd32r`.

The private artifact opt-in (`mtHelperCensus=1`), getter ABI and page reader
are bidirectionally fail-closed: an opt-in/runtime disagreement, ABI other
than 1, missing glue export, or missing heap fails startup. The 120-byte
snapshot contains exactly 15 U64 values in the documented order. The source
also rejects a non-MT census build at compile time. Its private Wasm artifact
has exactly 56 exports (the accepted 54 plus the two census exports) and no
dual-entry/register-thread binding.

The diagnostic used `jitCacheUrl=off`, did not request JIT recording or replay,
and did not run Present/FPS scoring. Browser entry reached the visible 1024x768
PatHouse 3D scene; latest async-ring samples had `gaps=0`, `reorders=0`, and
`errors=0`, with no browser console errors.

Audit URL (the absence of `jit-record=true` is intentional) was
`http://127.0.0.1:8765/index_d3d9web_pathouse.html?pathouseav=1&audioGesture=1&audioFreq=44100&root=TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1&ws=ws%3A%2F%2F127.0.0.1%3A9201&p=run_azrok_seh.bat&inputPulse=1&pulseBuild=1&lean=1&leanMarker=1&build=mt-helper-census-20260724&app=Azrok_D3D9Web_pathouse_guesttexrecycle4&runtimeStem=boxedwine.upstreamjit64fn6inlineabi2mthelpercensus1&mtHelperCensus=1&jitCacheUrl=off`.
Private JS/Wasm SHA-256 are `58904A40E2ACD10E5C2A1ED1E21C0C0D3B0B1867B80A90B634421074EEA843D8` and
`0B4C029882F55EBFB2C07FE767A0FAE190B1F12654C92EB917ABFADC330C0C01`.
The final preserved ring line is `callbacks=120 first_seq=9721 last_seq=9840
next_seq=9841 gaps=0 reorders=0 errors=0` at `2026-07-24T03:52:32.338Z`.

## Stable PatHouse measurement - VERIFIED dynamic coverage only

Order is the 11 families `mem_r`, `mem_w`, `mem_wc`, `fetch_next`, `emulate`,
`flags`, `cond`, `x87`, `sse`, `movsd32r`, `enter`; followed by details
`cache_float`, `movsd_xmm_e64`, `movsd_e64_xmm`, `movsd32r`.

- At S0, after the full room was visibly stable, the process-lifetime snapshot
  was `48931,0,50280,704245924,24959501,4283404,85448501,902091,0,0,0,902091,0,0,0`.
- S1 was captured without input or tab change 22.302 seconds later:
  `61530,0,58635,796245728,30897732,5137116,111536073,973112,0,0,0,973112,0,0,0`.
- The exact S1-S0 delta is
  `12599,0,8355,91999804,5938231,853712,26087572,71021,0,0,0,71021,0,0,0`.

`fetch_next` is therefore the most frequent directly observed generated-Wasm
to-C++ helper family in this scene (about 4.13 million entries/second). `cond`
is second (about 1.17 million/s), but it is only a cross-check: all condition
candidate cards remain closed by 301/307/309/311. `cache_float` is a strict
detail subset of `x87`, so it must not be summed with its family; the three
SSE/MOVSD details are zero in this interval.

## Interpretation boundary

These are exact host-helper entry counts, not helper CPU time, per-call cost,
or an FPS result. The independently relaxed atomic loads are not a single
instantaneous vector; only the measured S1-S0 interval is used. Bootstrap,
other rooms, inputs, audio competition, and longer sessions are NOT VERIFIED.
The only newly opened follow-up is static scope analysis of the remaining
`fetch_next` helper path versus the existing fn6 inline path; it is not yet a
candidate or A-B-A card.
