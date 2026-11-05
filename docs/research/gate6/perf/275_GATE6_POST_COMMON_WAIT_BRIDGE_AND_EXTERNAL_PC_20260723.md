# 275. Gate 6 — post-common wait/bridge decomposition and external PC sampling

Date: 2026-07-23 KST

## Status

- **VERIFIED:** On the accepted common-dispatch path, browser main-thread D3D round-trip wait is not the missing frame time. The second combined leg measured exactly zero round trips and zero wait over 360 stable PatHouse Presents.
- **VERIFIED:** Pooled wait-only A legs spend 2.7264 ms/frame in captured read/futex waits, far below the approximately 20--22 ms total frame.
- **VERIFIED:** The diagnostic B legs leave approximately 16.0--16.2 ms/frame after subtracting kernel and instrumented bridge time.
- **VERIFIED:** External Windows thread accounting finds one release-runtime thread using 3.9219 CPU seconds in 5 seconds; fixed-interval instruction-pointer samples for that thread land 67.7% in dynamic/unmapped executable code.
- **INFERRED:** Together with the previously identified DedicatedWorker topology, the dominant remaining lever is BoxedWine/WASM guest execution rather than a hidden WebGL main-thread response wait.
- **VERIFIED / ACCEPTED:** The generic-dispatch depth-local candidate preserves the reference render and improves clean single-session PatHouse HUD mean FPS by +6.92% and +4.79% against the two adjacent atomic baselines.

## Measurement method

The user-requested adaptive interleave was used: wait-only A1, combined WAIT+bridge B1, wait-only A2, then B2 because A drift exceeded 3%. All selected windows were stable 1024x768 PatHouse, `document.visibilityState=visible`, and 120 real `COMMAND.PRESENT` calls each. Foreground changes were retained as covariates; only hidden/fully throttled windows would have been discarded.

The combined profiler shares the same 120-Present boundary for WAIT, JIT coverage, bridge and main-reason output. Every selected reason total reconciled `accounted_calls/wait_us` with the expected values. The combined build differs from the wait-only build only by `BOXEDWINE_D3D9WEB_BRIDGE_PROFILE`; its 134 grouped modules differ only in the exact release/profile relocation-map literal required by each runtime.

## A-B-A-B results

| Leg | FPS | frame ms | read ms/frame | futex ms/frame | kernel ms/frame | bridge ms/frame | main round trips/frame | main wait ms/frame |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 wait-only | 49.5118 | 20.1972 | 2.5972 | 0.0167 | n/a | n/a | n/a | n/a |
| B1 combined | 42.5030 | 23.5278 | 2.8861 | 0.0361 | 4.5111 | 3.0619 | 0.00556 | 0.01508 |
| A2 wait-only | 45.2204 | 22.1139 | 2.8139 | 0.0250 | n/a | n/a | n/a | n/a |
| B2 combined | 45.0958 | 22.1750 | 2.6389 | 0.0250 | 3.9278 | 2.0076 | 0 | 0 |

A drift is -8.67%, so the extension to B2 was mandatory. The bridge profiler calls `emscripten_get_now()` twice per bridge call and is diagnostic-only; B FPS and bridge time are therefore not release evidence. The decisive result is direct: B1 has only 9.97 ms total main wait over 360 Presents and B2 has none. The 30 ms/frame boundary-wait hypothesis is rejected on the current common-dispatch runtime.

Pooled A captured wait is:

- read: `(935000 + 1013000) / 720 = 2.7056 ms/frame`
- futex: `(6000 + 9000) / 720 = 0.0208 ms/frame`
- total: `2.7264 ms/frame`

The B residuals after subtracting measured kernel and bridge time are 15.9548 and 16.2396 ms/frame. Because bridge instrumentation adds timer cost, these are conservative lower bounds for non-bridge work.

## External release-runtime thread sampling

The diagnostic page was replaced in the same browser tab with the accepted release runtime/cache before external sampling. The stable PatHouse HUD was approximately 48.5 FPS.

Five-second Windows CPU deltas for the busiest renderer threads were:

| TID | CPU seconds / 5 s | wall utilization |
|---:|---:|---:|
| 19392 | 3.9219 | 78.44% |
| 124792 | 2.7188 | 54.38% |
| 79144 | 1.5781 | 31.56% |

ETW stack profiling could not be enabled without the system-performance policy privilege, so no privilege escalation was attempted. Instead, the three threads were sampled externally 300 times at 10 ms intervals by briefly reading their x64 instruction pointer. Module ownership was resolved against the renderer process module list:

| TID | dynamic/unmapped | chrome.dll | ntdll.dll |
|---:|---:|---:|---:|
| 19392 | 67.7% | 2.0% | 30.3% |
| 124792 | 8.0% | 31.7% | 60.3% |
| 79144 | 7.3% | 0.7% | 91.7% |

This is a fixed-wall sampler, not a privileged CPU-stack sampler, so `ntdll` wait samples remain in the denominator. It nevertheless directly shows that the busiest release-runtime thread spends most observed wall positions in dynamically generated executable memory rather than Chromium native rendering code. The exact function distribution inside those V8/WASM pages remains **NOT VERIFIED**.

## Next candidate: dispatcher depth snapshot local

The common generic dispatcher checks `cpu->wasmJitDirectChainDepth`, then on the successful tail reads the same field again before incrementing it. Static review verifies that only `table.size`, bounds comparison, `table.get`, and reference-null checks occur between the two reads; there is no imported call, guest block execution, or re-entry point. Reusing the first value in a new i32 local preserves:

- the per-CPU linear-memory depth field and outer C++ save/reset/restore scope;
- exception and nested-activation restoration;
- all null/slot/bounds/yield/bailout guards;
- one depth store only after every accepted tail;
- the existing 64-block bound.

The pipeline option `--mt-generic-depth-local` was generated as an isolated cache candidate:

- artifact: `profiles/azrok-jit-grouped-commonfast64-depthlocal1.zip`
- SHA-256: `B90407588D5B01C50D66613E90611B7CDC29C8D697512312C8C505A3ECB8BAFC`
- 134/134 valid Wasm groups and 41,625/41,625 manifest entries
- all 41,625 entry bodies, imports, exports and 32,439 direct-call patch payloads byte-identical to atomic releaseabi1
- dispatcher-only change in all 134 groups: depth linear load 2 -> 1, store remains 1, one `local.tee` and one `local.get`
- reverse-normalizing those three changes reproduces all 134 baseline dispatcher bodies byte-for-byte; unexpected differences 0

### Clean single-session adaptive A-B-A

Each leg closed its prior browser tab and directly required the old renderer process to exit and port 9201 to have zero established connections before creating the next single tab. The next leg then required exactly one visible tab and one established game WebSocket. This prevents accumulation of live game processes between conditions.

The page stdout/textarea transport can flush old 120-Present lines later than wall time; even a clean single session emitted approximately 19 seconds of queued window text during an external 10-second interval. Therefore console-line count was not used as the A-B-A clock. The already accepted low-overhead HUD was read once per second for 30 seconds. Every HUD value itself comes from the runtime's latest real 120-Present `delta/elapsed_ms` sample.

All legs were visible and retained `WindowsTerminal` (`Claude Code`) as foreground. Reference walls, carpet, furniture, character face, Korean UI and 1024x768 canvas were intact in B.

| Leg | 30 samples mean FPS | median FPS | min--max | renderer CPU / 30 s |
|---|---:|---:|---:|---:|
| A1 atomic | 38.2000 | 38.1000 | 36.9--40.7 | 67.938 s |
| B depth-local | 40.8433 | 41.9000 | 37.3--44.3 | 62.109 s |
| A2 atomic | 38.9767 | 38.3500 | 36.0--45.1 | 66.312 s |

A mean drift is +2.0332%, inside the adaptive +/-3% stop rule. B mean effects are +6.9197% against A1 and +4.7882% against A2; median effects are +9.9738% and +9.2570%. Both adjacent comparisons agree and renderer CPU also falls against both A legs. The candidate is accepted as the new cache baseline, but its 40.8433 mean remains below the final stable 50-FPS gate.
