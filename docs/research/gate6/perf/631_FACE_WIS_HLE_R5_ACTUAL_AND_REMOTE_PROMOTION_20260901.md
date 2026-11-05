# 631 — FACE-WIS HLE r5 actual result and supplemental remote promotion

Date: 2026-09-01 KST

## Conclusion

- **VERIFIED implementation:** exact Azrok.exe lookup/capture boundaries
  `0x00551198 -> 0x005511b1` now bypass the repeated Wine open/read/close WIS
  loader after two identical original captures.  The candidate is pinned to
  the exact executable, root/app archives, 113 `HP_*.wis` rows, helper 36,
  runtime ABI, and grouped-cache bytes.
- **VERIFIED actual PatHouse effect:** control A1 was `1440 Presents / 30.050s
  = 47.9201 FPS = 20.86806 ms/frame`.  Active HLE B1 was `1560 / 30.046s =
  51.9204 FPS = 19.26026 ms/frame`, or **7.7045949% lower frame time**.
- **VERIFIED active semantics:** the measured B1 window had `1621/1622`
  lookup hits, one scheduled probe miss/refresh, one stable tail comparison,
  all fallbacks zero, all tail-change/disable counters zero, and three active
  entries in `Admitted` phase.
- **VERIFIED strict-gate result:** the same-method result is below the 10%
  revolutionary gate.  A worker-sample optimistic cross-check was
  `18.79319 ms/frame`; even compared against A1's wall frame time it is
  `9.942803%`, still below 10%.  A2 was therefore skipped for the standalone
  promotion decision.
- **USER DECISION / ACCEPTED SUPPLEMENTAL:** the measured 7.7% implementation
  is retained and promoted as a production component rather than deleted.
  It is **not** described as a standalone 10% success.  The next performance
  goal remains a separate approximately-10%-level surface.
- **VERIFIED remote deployment:** `playazrok.com` now launches the exact r5
  runtime/cache by default.  A fresh server-list launch registered
  `143 groups / 44,395 entries / 33,912 patches`, reached actual PatHouse, and
  reported remote HLE `1413/1420` hits, three admitted entries, stable tails,
  and zero fallback/error counters.  The old multi-direct runtime/cache remain
  immutable rollback URLs.

## Final runtime and cache identity

```text
runtime stem  boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1facewishle1
JS bytes/SHA  332064 / b6cf4b8a386e5cd8417d93a247ed6eff31b0e03742a3e55e1a295cdbb6bc1220
Wasm bytes    3094493
Wasm SHA      68d7c2139293934a9b320b37f430220385c917ba10b6942d1aace39601c122d4
reloc map     12984728 / 262144
helper/tmpReg 36 / 116
cache         azrok-jit-grouped-multidirectloops1-currentabi1-facewishle1-map12984728-r5-20260901.zip
cache SHA     b66eb03460d1d4197ace6baaf41dd26cbbb922759ee991ce54bd869e755d5582
manifest SHA  e19f1e266c7a59f59f751f8b2ce696d80410252642a5265fc70429e32a368c1d
```

All 143 grouped modules validated and reverse-normalized byte identity passed.
The final rebased target hashes are `237c4be9...32e50` for group 0082 and
`d3ea8dcd...bc1c7` for group 0140.

## Correctness defects found before acceptance

The final result required direct runtime evidence rather than treating a
fail-closed fallback as success:

1. **Descriptor layout:** the original loader writes descriptor `+0=255`,
   `+4=256`; the initial check was reversed and would never admit an entry.
2. **Exec lifetime:** process state was initially freed before other guest
   threads quiesced.  Reset now occurs after `terminateOtherThread` has removed
   every sibling thread.
3. **RX code comparison:** `KMemory::memcmp()` requested a writable pointer on
   an RX CodePage and caused `kpanic`.  The HLE now uses chunked
   `performOnMemory(..., true)` read-only comparison, matching the existing
   Acknex helper contract.
4. **DOS separators:** the guest creates `Data\Texture\HP_*.wis`, while
   BoxedWine VFS splits only `/`.  VFS lookup now changes separators only and
   preserves archive path case.  The 113 ZIP rows independently matched CRC,
   central offset, compressed/file lengths, method, and SHA-256.
5. **Runtime/cache aliasing:** generated JS requests the stem-specific Wasm
   filename, not only `boxedwine.wasm`.  Candidate `locateFile` now versions
   that exact filename.  Live ABI caught an old cached Wasm before guest
   execution.
6. **Browser diagnostics:** the page verifies exact URL opt-in, archive,
   manifest, JS/Wasm query URLs, rebased target bytes, and live ABI.  Each
   button click takes one counter/entry snapshot; there is no timer or
   per-frame sampling.

## Actual measurement

```text
A1 wall                 30.050s
A1 Presents             1440
A1 frame time           20.8680556 ms

B1 wall                 30.046s
B1 Presents             1560
B1 frame time           19.2602564 ms
B1 frame-time reduction 7.7045949%

B1 HLE lookup           1622
B1 hits/misses          1621 / 1 (scheduled probe)
B1 capture entries      1622
B1 refresh/stable       1 / 1
B1 all fallbacks        0
B1 tail changed/disabled 0 / 0
```

The page Present bridge publishes complete 120-Present samples, so endpoint
wall counting omitted 62 HLE lookups at a sample boundary.  Summing the 13
worker samples inside the window gave `1560 Presents / 29.31737s =
18.7931859 ms/frame`.  It is recorded as a diagnostic cross-check, not used to
inflate the acceptance result.

## Deployment and rollback

Updated production/default files:

- `tools/boxedwine_local/index_d3d9web_pathouse.html`
- `tools/boxedwine_local/azrok_launch.js`
- `tools/boxedwine_local/azrok_server_list.html`
- final FACE JS/Wasm and r5 grouped cache

Remote SHA-256 values matched local bytes.  Public HTTPS returned 200 for the
page, launch script, JS, Wasm, and cache; immutable assets retained long cache
headers.  The user-facing in-app browser tab was left open on the actual remote
PatHouse scene.

Rollback remains:

```text
boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1
/profiles/azrok-jit-grouped-multidirectloops1-currentabi1-20260830.zip
```

## Next broad-performance boundary

#621 already performed a bounded condition-C split: expanded current-scene AOT
was the dominant part of the former +39.4%, while the C-to-B mean was +9.7622%
with 97.4507% key overlap and high B drift.  It also observed 44,969 baseline
and 5,592 top-tier compilations and rejected eager `--no-liftoff`, but its B4
profile ended before the canonical room window and lost trace data.

Therefore the next approximately-10% search is not another repeat of all three
old tasks.  The missing decisive measurements are:

1. stable actual-B owner CPU-time attribution for the remaining dispatcher/JIT
   boundary;
2. stable-window per-hot-function Liftoff/TurboFan ownership;
3. only if that residual surface is at least 10%, a region/PIC/dispatcher
   implementation with an actual fresh-process gate.

## Evidence

- `artifacts/performance/face_wis_hle_final_b1_r5_measurement_20260901.json`
- `artifacts/performance/face_wis_hle_final_b1_r5_decision_20260901.json`
- `artifacts/performance/face_wis_hle_final_b1_r5_premeasure_snapshot_20260901.json`
- `artifacts/performance/face_wis_hle_remote_default_smoke_20260901.png`
- `artifacts/performance/face_wis_hle_runtime_cache_pairing_r5_20260901.json`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-face-wis-hle-runtime.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-face-wis-hle-page-bridge.mjs`

