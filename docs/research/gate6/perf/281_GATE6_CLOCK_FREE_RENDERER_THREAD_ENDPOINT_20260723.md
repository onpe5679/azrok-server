# 281. Gate 6 clock-free renderer-thread endpoint measurement

Date: 2026-07-23 KST

## Status

- **VERIFIED dynamic:** The accepted chain64/depth-local PatHouse runtime was measured with only two OS thread-accounting endpoints over 30.116 seconds. No timer or counter was added to the guest block, JIT dispatcher, D3D bridge, or frame loop.
- **VERIFIED dynamic:** The busiest renderer TID consumed 24.875 CPU seconds, or 0.826 core. The paired real-Present ratio was 50.408 FPS, giving approximately 16.39 CPU ms/Present for that one thread.
- **VERIFIED dynamic:** The second renderer TID consumed 13.9375 CPU seconds, approximately 9.18 ms/Present. The first is 78.5% larger.
- **VERIFIED gate:** This exceeds the predeclared guest/WASM-owner thresholds: at least 12 ms/Present, at least 0.70 core, and at least 25% larger than the next renderer thread. The remaining large lever is the primary DedicatedWorker/V8-Wasm execution path, not main-thread D3D wait.
- **NOT VERIFIED:** One paired ratio of 50.408 FPS does not establish stable 50 FPS. The immediately preceding controlled A64 windows averaged 44.45--45.95 FPS.

## Method

`tools/boxedwine_local/measure_renderer_threads.ps1` reads every thread's `TotalProcessorTime`, user/kernel split, and `QueryThreadCycleTime` only at the start and end of the window. The browser-side HUD already exposes accumulated `COMMAND.PRESENT` count/time in `#fps-counter` data attributes, so no new runtime build or per-frame instrumentation was required.

The PowerShell endpoint sampler and 1 Hz DOM reads were launched concurrently. Renderer PID 102836 and all retained TIDs were stable for the complete window. The page remained visible and the HUD remained numeric.

The HUD transport receives three equivalent copies of a 120-Present report in this topology, so raw accumulated Present count is not a physical count. As established in 274/275, the ratio `deltaPresents / deltaElapsedMs` remains exact because both numerator and denominator are multiplied equally. CPU ms/Present is therefore computed from `FPS * OS wall seconds`, not from raw `deltaPresents`.

## Results

- OS wall: 30.116 s
- paired HUD ratio: 4,680 / 92,842.455 ms = 50.40797 FPS
- estimated physical Presents in OS wall: 1,518.01

| rank | TID | total CPU | user | kernel | core | CPU ms/Present |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 103412 | 24,875.000 ms | 23,125.000 | 1,750.000 | 0.8260 | 16.39 |
| 2 | 54160 | 13,937.500 ms | 10,671.875 | 3,265.625 | 0.4628 | 9.18 |
| 3 | 98596 | 5,265.625 ms | 2,781.250 | 2,484.375 | 0.1748 | 3.47 |
| 4 | 83004 | 4,359.375 ms | 4,125.000 | 234.375 | 0.1448 | 2.87 |
| 5 | 72104 | 3,906.250 ms | 1,671.875 | 2,234.375 | 0.1297 | 2.57 |

`GetThreadDescription` returned empty descriptions for these Chromium threads, so role names are not inferred from that API alone. The top-thread ownership is supported jointly by the already verified 275 fixed-wall PC samples (67.7% dynamic V8/Wasm on the busiest runtime thread) and the current 0.826-core endpoint. This measurement does not assign the 16.39 ms to one guest function; it identifies the execution domain and rules out another dispatcher micro-optimization chosen without evidence.

## Decision

Continue on a broad guest/WASM execution reduction. Do not return to main-thread D3D batching, browser timer-clamp, or one-instruction table readiness variants as the primary 50-FPS strategy.

