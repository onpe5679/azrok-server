# 629 — Cached ZIP global-read-mutex bypass rejected below the 10% gate

Date: 2026-09-01 KST

## Conclusion

- **VERIFIED implementation:** compile flag
  `BOXEDWINE_AZROK_CACHED_ZIP_UNLOCKED_READ` changes only
  `FsZipOpenNode::getReadMutex()`: a promoted immutable
  `azrokRepeatedZipCache` returns `nullptr`, while uncached, STORE and direct
  paths retain `FsZip::readMutex`.  `KFile::filePosMutex` continues to protect
  the open node's private position.
- **VERIFIED build scope:** the candidate exports the exact production generic
  ABI (`relocMapBase=12968408`, capacity 262144, next/depth/bailout/pfn offsets
  `740/1660/132/12`).  Of 244 current-source objects, only
  `source/io/fszipopennode.cpp.o` changes semantically.  The apparent
  `ring_buffer.cpp.o` change reverse-normalizes byte-for-byte after converting
  the embedded assert path's `C:\` separators to `C:/`.
- **VERIFIED performance rejection:** actual PatHouse A1 production was
  `1445 / 30.016090s = 48.1408 FPS / 20.7724ms`; B1 candidate was
  `1527 / 30.015857s = 50.8731 FPS / 19.6567ms`.  Candidate frame time fell
  only **5.3707%**, not the required 10%.  Because the first mandatory adjacent
  control already fails, A2 cannot make the “both adjacent A” rule true and
  was intentionally skipped under the user's immediate-rejection rule.
- **VERIFIED visual/cleanup:** both legs preserved actual room, orange rug,
  blue character, HUD and quest panel before and after their 30-second windows.
  The candidate browser was closed, WSS established count returned to zero,
  and its public JS/Wasm/cache alias were removed.  The exact copies were moved
  to the recoverable evidence folder
  `artifacts/performance/rejected_cachedzipunlock1_assets_20260901/`; source
  gate, isolated build output and verifier/report also remain.
- **NOT VERIFIED activation count:** the release-shaped candidate deliberately
  had no counter export, so the number of promoted-cache mutex bypasses was not
  measured directly.  This cannot rescue the candidate: the observed end-to-end
  effect already misses the required gate by a wide margin.
- **PRODUCTION/REMOTE UNCHANGED:** normal launcher/runtime/cache and remote
  deployment were never modified.

## Admission and semantic boundary

#628 measured a conditional owner-scaled perfect WIS surface of only 10.3602%,
so this was a deliberately narrow, boundary-case admission.  The safety
argument was:

1. a promoted cache vector is fully inflated before publication and immutable;
2. each `FsZipOpenNode` retains its own shared pointer and private `pos`;
3. `KFile::read()` already holds `filePosMutex` across `FsOpenNode::read()`;
4. the archive mutex protects minizip cursor state, which a vector memcpy does
   not touch;
5. a null cache pointer follows the old mutex path exactly.

No write, close, seek, uncached read, STORE entry or direct-handle behavior was
changed.

## Build identity

```text
stem       boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1cachedzipunlock1
JS SHA     0063032750844b19b51fc665588bbab61d6d01990983342eaf5b0bd80fe359e1
Wasm SHA   8f5563a8448f3d87c2e60635715b697a98c7f05680e7e8bd0984db929d345f8b
cache      byte-identical alias of production, SHA 03a322841ae2ff221aba793ab832318349deeb8a3d3a1db2bf5c3ce189a7dbb5
```

The isolated build output remains under
`Build/AzrokTouch2MultiDirectLoopsCachedZipUnlocked1`; the public asset copies
and cache alias were removed after rejection.

## Actual A1-B1 result

Both fresh processes used the same account, app/root, displayed 1024x768
canvas, `143/44395/33912` grouped replay and exact first-stage input only.
After actual 3D acceptance each leg reached 45 seconds total settle, then a
30-second direct-Present window.

| leg | condition | Presents / wall | FPS | frame ms | semantic |
|---|---|---:|---:|---:|---|
| A1 | production | 1445 / 30.016090s | 48.1408 | 20.7724 | actual PatHouse before/after |
| B1 | cache-hit mutex bypass | 1527 / 30.015857s | 50.8731 | 19.6567 | actual PatHouse before/after |

```text
FPS effect        +5.6756%
frame-time effect -5.3707%
required          <= -10.0000%
```

This is a real positive change in this pair, but “positive” is not the goal.
It is less than the explicit revolutionary threshold, so it is rejected rather
than extended or promoted.

## Evidence

- `artifacts/performance/cached_zip_unlock_early_reject_20260831.json`
- `artifacts/performance/cached_zip_unlocked_runtime_20260831.json`
- `artifacts/performance/cachedzip_ab_a1_measure_20260831.csv`
- `artifacts/performance/cachedzip_ab_b1_measure_20260831.csv`
- `artifacts/performance/cachedzip_ab_a1_measure_{before,after}_20260831.png`
- `artifacts/performance/cachedzip_ab_b1_measure_{before,after}_20260831.png`
- `tools/boxedwine_local/bwujit_threaded_abi/source/io/fszipopennode.cpp`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-cached-zip-unlocked-runtime.mjs`

## Decision

Keep the compile gate and verifier only as a reproducible failed experiment.
Do not route, deploy, tune or combine this candidate merely to preserve a
single-digit gain.  The next candidate must independently carry a measured
>=10% removable time surface.
