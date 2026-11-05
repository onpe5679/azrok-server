# 263 — Gate 6 MT chain8 rejection and foreground wait/pacing measurement (2026-07-22)

## Conclusion

- **VERIFIED / REJECTED:** A correctly wired pthread MT chain loop that executes up to eight consecutive compiled blocks preserved the accepted 1024×768 PatHouse render, but a strict foreground 15-second sample measured **27.8867 FPS** (20.0–34.0) versus the retained BrokerAbi reference **33.9333 FPS**. That is **-17.82%**. A later settled sample was 31.8667 FPS, still below the reference, so chain8 is rejected and isolated behind an explicit build flag.
- **VERIFIED dynamic:** Execution-weighted diagnostic counts showed the next block was callable JIT code in 99.9969% of sampled compiled-block exits. This proved that the pthread path returned to its outer dispatcher after nearly every compiled block, but the chain8 browser result proved that removing those returns with the safe C++ chain loop did not reduce frame time.
- **VERIFIED static/code:** The MT chain now defaults to one block. Only the dedicated `azrokMultiThreadedJitAudioO3MtChain8` target defines `WASM_JIT_MT_CHAIN_BLOCK_LIMIT=8`. A PROFILE-only stale `cpu->nextOp` dereference was removed; chain-target sampling now occurs only after the live decoded-op cache refetch. Publication revalidation, termination/yield guards, and final hazard release remain in the opt-in experiment.
- **VERIFIED foreground dynamic:** In five stable PatHouse windows totaling **600 Presents**, with foreground HWND `0x10A82` / PID 15032 / title `ChatGPT` confirmed before and after, the presenting game thread made **zero** `select`, `nanosleep`, `clock_nanosleep`, and `poll` calls. Futex residence totaled only **2 ms**. Therefore a 1–2 ms guest sleep becoming an 8 ms browser timer clamp is not the current 30 FPS ceiling.
- **VERIFIED foreground dynamic:** The same five windows spent **2,571 ms / 600 frames = 4.285 ms/frame** in >=1 ms blocking `read` syscalls on the presenting guest thread. Per-window totals were 469, 557, 441, 497, and 607 ms per 120 Presents; maxima were 20, 25, 6, 42, and 25 ms. This first probe did not bucket the file descriptor or caller, so attributing all of it to Wine/wineserver is **NOT VERIFIED** pending an explicit WaitForSingleObject marker.
- **VERIFIED scope caveat:** `blocking_read_us` is a subset of the same syscall residency already accumulated in BoxedWine `kernelTime`; the two values must not be added. The read bucket also includes any file, pipe, or socket read longer than 1 ms until the marker build isolates WFSO-internal reads.
- **VERIFIED static:** Acknex engine descriptors define `FPS_MAX` at `0x10248DE8` (storage slot `0x10298118`, default fixed `0x0003C000` = 60), `FPS_MIN` at `0x10248E00` (default 4), and `FPS_LOCK` at `0x10248E18` (default 0). The limiter at `0x100191F0` derives target milliseconds from `FPS_MAX` and calls `Sleep` at `0x100193A8`, but no Sleep/NtDelay syscall occurred in measured PatHouse frames.
- **VERIFIED static:** The Acknex command-line parser at `0x10018096..0x100185FC` has no FPS/maxfps/vsync option. `-WND` writes `VIDEO_SCREEN=2` and is the safe windowed-mode option; `-NWND` hides the initial window and is not a windowed-mode switch. D3D9 presentation parameters are assembled at `0x1005CEB0`; no separate vsync CLI flag exists.

## Measurement implementation

The dedicated `BOXEDWINE_AZROK_WAIT_FRAME_PROFILE` build reuses the `ksyscall()` entry/end microcounter reads already paid by the normal runtime. It adds no clock read inside a syscall and snapshots only on an existing D3D Present boundary. Thread-local buckets report requested and actual time for select/nanosleep/clock_nanosleep/poll/futex, and explicitly label Wine blocking read request time as `N/A`.

Build and deployed diagnostic asset:

- target: `azrokMultiThreadedJitAudioO3WaitProfile`
- runtime: `boxedwine.upstreamjit32waitprofile1`
- JS SHA-256: `6BEB513BE83063789F9ACA486AD35424E8FD3493483FD1A1A0B6232B88985B36`
- WASM SHA-256: `F97AB81C63BE439E72AF4229FEB470A3ACF412FA267415D717BE5C678E2381C5`
- full Emscripten O3 build: PASS

### Exact WaitForSingleObject attribution follow-up

- **VERIFIED static/build; browser result NOT VERIFIED:** Wine 11 `kernelbase!WaitForSingleObject/Ex` now has a diagnostic-only begin/end marker carrying the exact Win32 timeout and immediate caller return address. The marker uses private EAX `0x7f00`, intercepted before BoxedWine's Linux syscall table; Linux i386 syscall 436 remains untouched. BoxedWine attributes only >=1 ms reads enclosed by an active marker and aggregates by caller for 120 Presents. This classification build adds two marker syscalls per measured wait and is not a performance reference.
- **VERIFIED package:** The diagnostic root is cloned from the retained `bgmloop3-dsound80ms1` root and changes exactly one ZIP member, `opt/wine/lib/wine/i386-unix/kernelbase.dll.so`. ZIP integrity passes with all 8,656 entries retained.
- runtime stem: `boxedwine.waitmarker1` deployed under the page loader's actual `tools/boxedwine_local/assets_d3d9web/` path (the same-named copies at the server root are not used by this page)
- JS SHA-256: `23B54C020954A3104C3828ED1A18145567A1BFE23C27266FE7956D8A2493DCEB`
- WASM SHA-256: `AB8B2E8EB4CDBC0C968162E1F4F972350BBF818A78657D1EF949D3F1F946D82A`
- root: `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-waitmarker1.zip`
- root SHA-256: `3E6D2798DD9F6CFB2041C54E4629E666D56C698958E01683667F3914411D98B6`
- marker `kernelbase.dll.so` SHA-256: `92BA845907B6C424DF78F2042BF8C33BC258A7CE9612000C14FC233F97245CFD`

### Strict-foreground WFSO attribution result

- **VERIFIED foreground dynamic:** Six stable windows totaled **720 Presents**. All >=1 ms presenting-thread reads were `457, 420, 360, 518, 444, 513 ms` per 120 Presents, totaling **2,712 ms / 720 frames = 3.7667 ms/frame**.
- **VERIFIED foreground dynamic:** Reads enclosed by the exact `WaitForSingleObject/Ex` marker were only `15, 15, 14, 14, 17, 18 ms`, totaling **93 ms / 720 frames = 0.1292 ms/frame**. This is **3.429%** of the >=1 ms read residence. The remaining **2,619 ms = 3.6375 ms/frame = 96.571%** was outside the WFSO marker and must not be described as WFSO or physics wait time.
- **VERIFIED foreground dynamic:** Every window contained exactly 120 marked WFSO calls, hence **720 calls / 720 frames = one call per Present**. Every call reported requested `req_us=0`; the marker's timeout-result count was also zero. All calls came from the single immediate return address `0x1FA3F04A`.
- **REJECTED:** The physics/render loop is not losing a large frame interval inside `WaitForSingleObject`. The observed call is a zero-time poll and its enclosed >=1 ms reads average only 0.1292 ms/frame. The earlier 3.7667 ms/frame aggregate read bucket is dominated by non-WFSO reads and needs separate FD/caller attribution before any wake-policy change.

## Decision

1. Keep BrokerAbi as the performance reference; do not extend the multi-block JIT chain.
2. Reject browser timer-clamp/Sleep pacing as the 30 FPS root cause for PatHouse.
3. Keep the WFSO large-physics-wait hypothesis rejected. Attribute the remaining non-WFSO >=1 ms reads (3.6375 ms/frame in the marker run) by exact FD/caller before changing wake behavior.
4. Do not claim an Acknex 30 FPS cap: the binary default is 60, `FPS_LOCK` defaults to 0, the parser has no FPS CLI switch, and the measured frame loop issued no limiter sleep.
