# 628 — Current PatHouse blocked `read` source and Wine-request attribution

Date: 2026-08-31 KST

## Conclusion

- **VERIFIED dynamic:** the exact current-B owner trace's generated block
  `v5-1054d1b5-96376265` spans guest EIP `0x1054d1b5..0x1054d1f2` and contains
  the live syscall EIP `0x1054d1c2`.  Six accepted actual-PatHouse windows
  measured `720 Presents / 15,014,000 us`, of which >=1 ms `read` residency was
  `2,847,000 us = 18.9623%` (`3.9542 ms/frame`).  The earlier owner-profile
  `6,385,636 / 30,027,896 us = 21.2657%` was a valid upper surface, but it was
  not all wineserver traffic.
- **VERIFIED source split:** `fd=4`, `object_type=1`,
  `anon_inode:[pipe]`, fixed `len=64` Wine replies were
  `1,460,000 us = 51.2821%` of blocking reads and **9.7243% of current wall**.
  Repeated face WIS reads were `1,387,000 us = 48.7179%` and **9.2380% of
  current wall** (`HP_AK_B_base_0.wis` 1,194,000 us and `_base_2.wis`
  193,000 us).  Either family alone is below the actual-window 10% frame-time
  gate even under impossible complete elimination.
- **VERIFIED Wine 11 request split:** every one of the `1,460,000 us` pipe
  total was attributed to request fd 3.  The exact enum names are
  `create_file(44)` 560,000 us / 38.3562%, `select(29)` 257,000 / 17.6027%,
  `set_queue_mask(116)` 185,000 / 12.6712%, `event_op(31)` 175,000 / 11.9863%,
  `get_handle_fd(48)` 162,000 / 11.0959%, and `close_handle(21)` 121,000 /
  8.2877%.  No single request, and not even the complete fd-4 family in this
  window, can produce a 10% frame-time reduction.
- **VERIFIED admission arithmetic:** these windows require removing
  `1,501,400 us`, or **52.7362% of all measured blocking-read time**, to reduce
  frame time by 10%.  The independent exact-owner window requires removing
  `3,002,789.6 / 6,385,636 us = 47.0241%` of its blocked-read upper surface.
  These are different denominators and are not interchangeable.  Scaling the WIS fraction of blocked reads against the
  longer exact-owner surface gives a conditional `21.2657% * 48.7179% =
  10.3602%` upper bound.  This admits measurement of one structural
  cached-ZIP read-lock candidate, not acceptance: actual A1-B1-A2 still must
  show >=10% frame-time reduction.
- **NOT VERIFIED:** how much of WIS residence is removable global ZIP-lock
  contention versus inflate/cursor work, and how much of `create_file` belongs
  to the same face-resource churn.  Adding WIS and handle-request totals as if
  causal would be invalid without a joined trace.
- **PRODUCTION UNCHANGED:** neither readwait diagnostic runtime nor its rebased
  cache was deployed remotely or selected by the normal launcher.

## Exact accepted measurement

The final runtime/cache pair was isolated:

```text
runtime stem  boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1readwait3
JS SHA-256    c9e7a8c74bcd84646a6db69ce67d627e18c53a6e56a8ddea72d7ce344848d434
Wasm SHA-256  aacc740b370f8dec2948801ebdaa035793ae7a265d67a7822d9ce6f8e9961f05

cache         azrok-jit-grouped-multidirectloops1-currentabi1-readwait3-map12982616-20260831.zip
cache SHA     94504ef5f35516d36156b98f70c223e2a8e379e4879f41a7d4e886ac7c82471c
manifest SHA  40170fa897cc5cbee917da4e7a19bf0d616535bec31a40b59a0ebdb060c15148
groups/entries/patches 143 / 44,395 / 33,912
runtime reloc map      12,982,616 / 262,144
```

The rebased cache differs from production group code in exactly one same-size
`i32.const` reloc-map immediate per group.  All 143 groups validate, and
replacing the new immediate with the production value reproduces every source
group byte-for-byte; aggregate source and reverse-normalized SHA are both
`9c8381a7cc99d205fd95c5c4ce4300f983d5225e2a81871a82f6064499e46d83`.

The profiler publishes no duplicate console rows.  After visual PatHouse
admission, the collector's first address read allocated one lazy 64 KiB shared
buffer at:

```text
ABI / capacity        1 / 65,536
seq / bytes / data    1,395,115,592 / 1,395,115,596 / 1,395,115,600
shared heap bytes     1,477,246,976
contract              odd -> bytes+UTF-8 data -> even release
```

The buffer did not exist during boot or scene transition.  Snapshot sequence
2 was discarded wholesale; consecutive sequences 4, 6, 8, 10, 12 and 14 were
accepted.  Every snapshot had one `META abi=1 truncated=0`, one 120-Present
frame row, one 120-Present coverage row, no sequence gap, and no source
overflow.

Actual 3D semantic witnesses:

```text
before SHA  e1a481a1cb9e580b4eb67badd324ca4d81198b3bc68720096341f8822afc53df
after SHA   bd3b126331446433a2a8c272dd86e0769993f9fe418f362a3e8ed397bce3585a
scene       room floor + orange rug + blue character + HUD + quest panel
```

The page remained visible, registered `143/44395/33912`, and advanced to
13,290 Presents after collection.

## Why `0x1054d1b5` and `0x1054d1c2` are the same read path

The owner time profile maps its blocked dynamic frame to grouped entry
`v5-1054d1b5-96376265`.  The current grouped manifest gives that block
`emulatedLen=62`, so its interval is `0x1054d1b5..0x1054d1f2`.  The syscall
profiler records `CPU::eip` at the actual `int 0x80`, `0x1054d1c2`, which lies
inside that exact block.  Wine 11/glibc source/disassembly identifies this as
the cancellable `read` syscall path.  This is a direct range join, not a
histogram or name inference.

## Accepted-window totals

```text
wall                       15,014,000 us / 720 = 20.8528 ms/frame
technical FPS              47.9552
>=1 ms blocking read        2,847,000 us / 720 = 3.9542 ms/frame
blocking share              18.9623%
ideal complete elimination  frame reduction 18.9623%
10% target removal          1,501,400 us = 2.0853 ms/frame
required blocked fraction   52.7362%
```

### Source identity

| fd / object | identity | calls | blocking us | max us | wall share |
|---|---|---:|---:|---:|---:|
| `4 / KTYPE_UNIX_SOCKET(1)` | `anon_inode:[pipe]`, len64 only | 1,276 | 1,460,000 | 26,000 | 9.7243% |
| `73 / file(0)` | `.../HP_AK_B_base_0.wis` | 325 | 1,194,000 | 22,000 | 7.9526% |
| `73 / file(0)` | `.../HP_AK_B_base_2.wis` | 53 | 193,000 | 23,000 | 1.2855% |

The rotating fd number is not treated as file identity; the lifetime-safe
`KObject::selfFd()` path is.

### Wine server request identity

| id | Wine 11 enum | calls | blocking us | share of fd4 | wall share |
|---:|---|---:|---:|---:|---:|
| 44 | `create_file` | 417 | 560,000 | 38.3562% | 3.7299% |
| 29 | `select` | 257 | 257,000 | 17.6027% | 1.7117% |
| 116 | `set_queue_mask` | 174 | 185,000 | 12.6712% | 1.2322% |
| 31 | `event_op` | 175 | 175,000 | 11.9863% | 1.1656% |
| 48 | `get_handle_fd` | 134 | 162,000 | 11.0959% | 1.0790% |
| 21 | `close_handle` | 119 | 121,000 | 8.2877% | 0.8059% |

All request rows carry `request_fd=3`, and their sum equals fd4 blocking time
exactly.  `create_file` is the largest request but only 3.7299% of wall, so a
single request HLE is rejected by the 10% rule.

## Diagnostic failures and correction

1. Browser-level and direct-worker CDP console collection both failed because
   live Emscripten workers did not service `Runtime.enable`/`Debugger.enable`;
   even a fresh wait-for-debugger preattach produced zero native AZROK rows.
   This route was stopped instead of repeatedly retried.
2. `readwait2` put the 64 KiB publisher in static linear data.  Its exact
   runtime reached the tutorial transition and then raised a worker
   `RuntimeError: memory access out of bounds`.  A same-account `readwait1`
   control reached actual PatHouse with no exception, proving a diagnostic
   runtime regression.  The rejected readwait2 assets are retained at JS/Wasm
   SHA `e2dc687f... / e66def3c...`.
3. `readwait3` allocates the publisher only on the first address export, after
   visual PatHouse acceptance.  Before that, publisher writes are no-ops.  It
   passed the same transition and the complete shared snapshot run.

## Next >=10% admission gate

`FsOpenNode::read()` asks `getReadMutex()` before every read.
`FsZipOpenNode::getReadMutex()` currently returns the archive-wide
`FsZip::readMutex` even when `azrokRepeatedZipCache` is already an immutable
node-owned vector; `KFile::filePosMutex` still serializes that open handle.
The conditional owner-scaled WIS upper bound is 10.3602%, so a compile-gated
candidate may return `nullptr` only for proven cache hits while leaving every
uncached/STORE/direct path unchanged.

This is admission to A1-B1-A2 measurement, not a performance claim.  It must
also prove that the measured WIS reads are cache hits.  If both adjacent
candidate legs do not reduce actual PatHouse frame time by >=10%, reject it
immediately.

## Evidence

- `artifacts/performance/read_wait3_actual_pathouse_shared_snapshots_20260831.json`
- `artifacts/performance/read_wait3_actual_pathouse_read_attribution_20260831.json`
- `artifacts/performance/read_wait_profile_shared_runtime_lazy3_20260831.json`
- `artifacts/performance/read_wait_profile_shared_lazy3_cache_rebase_20260831.json`
- `artifacts/performance/read_wait3_lazy_actual_pathouse_before_20260831.png`
- `artifacts/performance/read_wait3_lazy_actual_pathouse_after_20260831.png`
- `tools/browser_diagnostics/Collect-AzrokWaitSharedSnapshot.mjs`
- `tools/browser_diagnostics/analyze_azrok_wait_shared_snapshots.py`
- `tools/boxedwine_local/bwujit_threaded_abi/source/kernel/syscall.cpp`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/rebase-grouped-cache-reloc-map.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-wait-profile-shared-runtime.mjs`
