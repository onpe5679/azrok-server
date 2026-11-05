# 633 — FACE-on readwait causal join rejects 10%; disabled-state retry race found

Date: 2026-09-01 KST

## Conclusion

- **VERIFIED actual PatHouse combined diagnostic:** the 5-way
  FACE+owner+readwait+causal-WIS runtime registered 143 groups / 44,395 entries
  / 33,912 patches and retained stable owner CPU `0x2143f520`, exact assets,
  fresh visual nonce, pre/before/after PatHouse PNGs, six accepted 120-Present
  windows, no sequence gaps, truncation, overflow, page error, or join error.
- **VERIFIED exact WIS lifecycle:** 720 Presents produced exactly 720 complete
  WIS loads. Each joined one `create_file`, one `get_handle_fd`, six reads
  totalling 130,580 bytes, close, and one `close_handle` on the same KThread.
  Ambiguous, unmatched, timeout, interleaved, parse, shape, and cross-window
  counters were all zero.
- **VERIFIED standalone-10 rejection:** joined handle union was 1,003,570 us.
  Full WIS outer work plus joined handles was 1,538,210 us raw and 1,451,810 us
  after subtracting the combined clock-tax upper. Against 17,366,000 us wall,
  the causal lower is **8.360071%**, missing 10% by 284,790 us. The broader WIS
  lifecycle HLE is therefore not implemented as an independent 10% candidate.
- **VERIFIED read-source context:** the same windows measured 2,235,000 us =
  12.869976% blocking read residency: Wine reply pipe 9.737418%, repeated
  `HP_PZ_R_base_0/1/2.wis` 3.132558% combined. Residency is not added to the
  joined union; the causal join is authoritative for the HLE target.
- **VERIFIED FACE disabled-state race:** during the steady PatHouse windows the
  FACE helper ran repeatedly, but every call incremented
  `FallbackProcessIdentity`; lookup/capture/hit deltas were zero despite 47
  earlier accepted hits. Source inspection proves `getOrCreateState()` installs
  a failed `ProcessState` with `enabled=false`, and all later calls return it
  without revalidation. A transient first identity failure can therefore turn
  the production HLE off for the lifetime of a later PatHouse process.
- **IN PROGRESS:** a compile-gated r6 retry sibling will revalidate disabled
  state only on epoch/global ZIP-generation change or bounded backoff, under a
  single atomic validator. It must prove retry success, cessation of process
  fallback, active HP_PZ lookup hits, zero semantic fallback/tail change, and a
  fresh-process actual PatHouse frame-time reduction of at least 10% before any
  production change.
- **PRODUCTION UNCHANGED:** all combined runtimes/caches remain local explicit
  diagnostics. Deployed FACE r5 and launcher defaults are byte-identical.

## Diagnostic identity

```text
runtime stem  boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1facewishle1ownerthread1readwait3causalwisjoin1
JS SHA        1722e2df80ba672214654355ef04bc9bf9727d3274d9bd9bfda35911a7647e09
Wasm SHA      8c57e13d02a1fcd8823ea53393aaca35fa28b545ebbfa06ac77139155396e40a
cache SHA     e214d7639cadf29d0d1d5a1f88064e6eb8ef55d91793602f8602f6b6a228c25d
manifest SHA  9e2e138d9d9958bcc22072ebed4db62bdef4e57e63316ef96119b391101b0748
reloc base    13009544 / capacity 262144
owner/stamp   13009528 / 13009532
readwait      ABI1 / lazy 65,536-byte shared seqlock
causal join   ABI1 / 6 reads / 130,580 bytes / 2,000,000-us timeout
```

The page requires five explicit diagnostic switches and exact runtime, archive,
manifest, group 0010/0082/0140, owner, FACE, and readwait identities. It does
not infer causal macros from page data; exact runtime JS/Wasm hashes establish
that contract.

## Causal accounting

```text
Presents / wall                     720 / 17,366,000 us
raw WIS outer wait                  475,290 us
outer timing lower                  417,690 us
joined create/getfd/close union   1,003,570 us
joined timing lower                 974,770 us
full WIS + joined raw             1,538,210 us
full WIS + joined lower           1,451,810 us
lower share of wall                   8.360071%
10% target                       1,736,600 us
margin                             -284,790 us
```

The join totals are exactly 720 create, 720 getfd, 720 close lifecycles.
Summing all observed `create_file` pipe time with WIS time would overcount
unrelated opens; this lifecycle union replaces that invalid arithmetic.

## FACE retry root cause

`wasmJitAzrokFaceWisHleHelper()` calls `getOrCreateState()`. The current r5
implementation validates a newly allocated state once, stores the Boolean in
`enabled`, and installs the state regardless of success. An installed state is
returned immediately on every later call. The fallback branch never retries
`validateProcessIdentity()`.

This window directly observed the consequence:

```text
prior successful lookup hits       47
window lookup/hit/capture delta      0 / 0 / 0
window helper entries             1,698
window FallbackProcessIdentity    1,698
```

The r6 candidate must not hash the root/app archive on every helper call. A
disabled process needs an atomic single-validator gate and bounded retry driven
by process/ZIP identity changes plus a coarse call backoff. Existing process
reset/detach and all fail-closed fallback semantics remain mandatory.

## Evidence

- `artifacts/performance/face_owner_causalwis_player_pathouse_20260901.json`
- `artifacts/performance/face_owner_causalwis_player_pathouse_20260901.wait.json`
- `artifacts/performance/face_owner_causalwis_player_pathouse_20260901.join.json`
- `artifacts/performance/face_owner_causalwis_player_pathouse_20260901.attribution.json`
- `artifacts/performance/face_owner_readwait3_causalwis_runtime_cache_verified_20260901.json`
- `tools/browser_diagnostics/Collect-AzrokFaceOwnerReadwaitCombined.mjs`
- `tools/browser_diagnostics/analyze_azrok_causal_wis_handle_join.py`
- `tools/browser_diagnostics/analyze_azrok_wait_shared_snapshots.py`
- `tools/boxedwine_local/bwujit_threaded_abi/source/emulation/cpu/wasm/wasmJitAzrokFaceWisHle.cpp`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-face-owner-readwait3-causalwis-runtime-cache.mjs`
