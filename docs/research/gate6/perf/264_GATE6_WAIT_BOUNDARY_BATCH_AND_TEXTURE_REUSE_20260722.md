# Gate 6: wait source, D3D boundary batching, and transient texture reuse (2026-07-22)

## Scope

Stable 1024x768 PatHouse, original `Azrok.exe`, one visible browser tab, and the
same local server/profile were used. Performance windows are 120 real
`COMMAND.PRESENT` calls. Unless noted otherwise, Windows foreground was fixed
to the Codex/ChatGPT window `HWND 0x10A82` before and after a run.

## 1. Timer clamp / engine frame cap

- **VERIFIED:** the presenting guest thread did not issue timed Sleep,
  `NtDelayExecution`, timed select/poll, or a nonzero-timeout
  `WaitForSingleObject` in the measured stable PatHouse windows.
- **VERIFIED:** the one WFSO marker per Present requested timeout zero and used
  only about 0.129 ms/frame inside the marked region. It is polling, not an
  8+ ms browser-clamped sleep.
- **VERIFIED:** Acknex descriptors contain `FPS_MAX=60` and `FPS_LOCK=0`.
  Static parser inspection found no fps/vsync command-line switch analogous to
  the earlier `-NX` option.
- **REJECTED:** a 1--2 ms requested guest sleep being clamped to 8+ ms is not the
  observed 30 FPS ceiling. An Acknex fps/vsync command-line unlock was not found.

## 2. Remaining Wine FD time

- **VERIFIED:** corrected FD attribution measured Wine reply fd 4, 64-byte reads
  at about 2.345 ms/frame.
- **VERIFIED:** the other approximately 1.385 ms/frame was fd 70 full-byte file
  reading/copying, not a socket wait.
- **CAUTION:** these are subsets of the measured kernel/syscall time and must
  not be added to it again.

## 3. Exact D3D guest-to-host boundaries

The bridge-reason probe reused the existing one-timer-per-boundary measurement.
No per-command clock was added.

### Unoptimized transport

Five stable windows measured 36.943 ms/frame (27.069 FPS), 8.299 ms/frame D3D
main-thread wait, and 600--602 round trips per 120 Presents: exactly 5/frame.
The steady reasons were Present, direct CreateTexture, direct DestroyResource,
pre-create batch flush, and pre-destroy batch flush.

### Ordered sync-tail batching

`DestroyResource` became order-batchable because guest `Release` ignores the
bridge result. `Init`, `CreateTexture`, `CreateBuffer`, and `CreateDeclaration`
remain synchronous but are appended as the final command of the prior ordered
batch, preserving order and immediate HRESULT.

Six stable windows measured 33.673 ms/frame (29.697 FPS, +9.7%), 7.718 ms/frame
D3D wait, and 240--242 round trips per 120 Presents: 2/frame.

- **VERIFIED:** direct D3D residence fell by 0.581 ms/frame.
- **NOT VERIFIED AS DIRECT CAUSATION:** the remaining 2.689 ms/frame wall change
  varied with kernel/worker scheduling and is not all attributed to batching.
- **VERIFIED visual:** walls, complete carpet UV, table, chairs, character/face,
  Korean text, and UI alpha remained intact.

## 4. Per-frame 256x256 R5G6B5 texture

- **VERIFIED:** stable PatHouse creates, fully uploads, and destroys one
  256x256, one-level, format-23 texture (131072 bytes) each frame.
- **VERIFIED:** exact full-byte comparison found changing contents; upload
  suppression/content caching is invalid.

### WebGL storage pool

A bounded host pool reused only an exact descriptor and context generation,
preserved full uploads, skipped repeated immutable `texStorage2D`, invalidated
bindings, and cleared on actual renderer-canvas context events. Static audit
corrected `TEXTURE0+stage` to `TEXTURE0+stage*2` before the final test.

The same-session alternating test used 11 pairs with identical DrawUP count
(17280/120 Presents) and less than 0.15% bridge-call spread:

| metric | pool OFF | pool ON | OFF - ON |
|---|---:|---:|---:|
| wall mean | 29.8051 ms/f | 29.9899 ms/f | -0.1849 ms/f |
| FPS from mean | 33.551 | 33.345 | -0.207 FPS |
| wall median paired delta | | | +0.1518 ms/f |
| wall bootstrap 95% CI | | | [-1.0474, +0.6174] ms/f |
| D3D wait mean delta | | | +0.0071 ms/f |
| D3D wait 95% CI | | | [-0.0931, +0.1101] ms/f |

Pool windows were exactly `hit=120 miss=0 return=120 evict=0`; only 7/11 pairs
improved (one-sided sign test p=0.2744).

- **REJECTED for performance:** effect direction is not established and direct
  D3D wait reduction is not detected. The pool stays disabled in production.

### Direct RGB565 typed view

On little-endian aligned input, WebGL RGB565 accepts a `Uint16Array` view of the
existing bytes. This removes a new 128 KiB allocation and 65536-word JS copy
while retaining browser upload/staging.

The measurement phase was aligned to worker #121/#241 boundaries. Each copy
window reported `direct=0 copy=240`; each direct window reported
`direct=240 copy=0`. Across 12 pairs with identical DrawUP count:

| metric | copy | direct | copy - direct |
|---|---:|---:|---:|
| wall mean | 30.0187 ms/f | 29.6706 ms/f | +0.3482 ms/f |
| FPS from mean | 33.313 | 33.703 | +0.391 FPS |
| wall median paired delta | | | -0.0866 ms/f |
| wall bootstrap 95% CI | | | [-0.2155, +0.9394] ms/f |
| bridge mean delta | | | +0.0941 ms/f |
| bridge 95% CI | | | [+0.0157, +0.1752] ms/f |
| D3D wait mean delta | | | +0.0924 ms/f |
| D3D wait 95% CI | | | [+0.0173, +0.1706] ms/f |

- **VERIFIED micro-effect:** the bridge path is lower by about 0.094 ms/frame.
- **NOT VERIFIED as whole-frame uplift:** wall CI includes zero, median and mean
  disagree, and only 6/12 pairs improved. Keep the safe direct view but do not
  credit it with a demonstrated FPS increase.

## 5. No-profile release recheck

The profiler runtime was replaced by a fresh `-O3` release built from the same
source. The deployed stem is `boxedwine.upstreamjit32bridgebatch`; its Wasm SHA-256
is `6FF2A6443E70A725DD024C07EF517CCDC056553B04E959E8220ADD759643CE44`.
It contains neither `D3D9WEB_BRIDGE_FRAME_PROFILE` nor `D3D9WEB_MAIN_REASON`.

The old release did not expose the current HUD counter, so both runtimes were
compared with timestamps of the same host 120-Present marker. Each condition
used ten strict-foreground intervals in a fresh but visually identical PatHouse
session:

| release | 1200 Presents | aggregate FPS |
|---|---:|---:|
| prior `upstreamjit19o3` | 37.196 s | 32.262 |
| new `upstreamjit32bridgebatch` | 35.892 s | 33.434 |

- **VERIFIED release effect:** ordered batching improves the contemporaneous
  no-profile release by 3.63%. This is smaller than the profiler build's 9.7%,
  so the profiler percentage is not reused as the release claim.
- **VERIFIED visual/runtime:** accepted PatHouse rendering, BGM/SFX path, server
  heartbeat, and single connected client remained live after the measurement.
- **FAILED target:** 33.434 FPS remains below the 50 FPS project gate.

## Decision

1. Keep ordered sync-tail D3D batching; it is the only newly measured material
   gain (+9.7%, with 0.581 ms/frame directly resident in D3D wait).
2. Keep the safe RGB565 direct view as a bridge-cost cleanup without an FPS claim.
3. Disable the transient WebGL texture pool in production.
4. Do not resume chain/JIT variants or timer-clamp work from these results.
5. Measure the no-profile release runtime separately; profiler builds are not
   the final FPS gate.
