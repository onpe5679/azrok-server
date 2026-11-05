# 235 Gate 2c existing wall-time profile boundaries

Date: 2026-07-21

## Scope

This is a source and retained-result audit only. It rechecks the existing
`timeprofile`/bridge/guest/host profile implementations and documents which
measurements can still share a denominator. No browser session was opened and
no production, Emscripten, guest DLL, or browser asset was modified.

The principal retained results are documents 193, 198, 199, and 201. The
inspected implementations are the current source snapshots under
`artifacts/boxedwine/20260719_gate2b_native/Boxedwine` and
`tools/d3d9_web_backend` / `tools/boxedwine_local`.

## VERIFIED -- timer and window boundaries

| Measurement | Clock and reset window | What the timed interval includes | What it excludes | Reuse decision |
|---|---|---|---|---|
| `D3D9WEB_BRIDGE_PROFILE wall_us` | BoxedWine worker `KSystem::getMicroCounter`; reset with the bridge counters every 120 Presents | elapsed wall time between completed Present-side profile timestamps, including guest work, stalls, synchronous main-thread waits, and anything else delaying the render thread | GPU work which remains asynchronous after WebGL returns; concurrent work which does not delay the Present interval | **REUSE** for FPS and per-Present wall cost in visually accepted, non-transition windows |
| bridge `proxy_us` | same worker clock and same reset block as bridge `wall_us` | only intervals around synchronous `dispatchBatch` and direct `dispatch` runtime-thread calls; includes main-thread scheduling/wait, JS dispatch, WebGL calls, and return | guest `d3d9.dll` packet construction; `cpu->memory->memcpy`; append/copy into `batchedCommandBytes`; all guest execution outside the call | **REUSE WITHIN THE SAME BRIDGE RECORD** as a wall-time subset; do not rename it total bridge or total host time |
| guest `packet_copy_us` | guest QueryPerformanceCounter cumulative snapshots carried by Present; JS subtracts a prior guest snapshot | only explicitly instrumented guest proxy byte-copy regions, with per-call timer overhead removed | INT handling, BoxedWine guest-memory copy, batch-vector copy, proxy wait, JS/WebGL | **HISTORICAL BUILD ONLY**; the current source has declarations/reporting but no writer which increments `g_profile_packet_copy_*` |
| guest `upload_int_us` | same guest QPC snapshot family | large direct-upload `D3D9WebCall(base+3)` intervals: INT entry, descriptor handling, compiled guest-memory payload copy, batch append, and any forced flush/wait in that call | guest resource generation/Lock work before the call; unrelated uploads under 4 KiB | **REUSE** only as a per-Present delta from the same guest-profile record |
| guest `present_int_us` | same guest QPC snapshot family | from immediately before `SendCommand(Present)` until return: INT, BoxedWine command copy/append, Present batch flush, synchronous proxy wait, JS/WebGL Present, return | construction of `CommandPresentProfile` before the timer; preceding frame's packet construction | **REUSE** as Present round-trip time; it overlaps bridge `proxy_us` and must not be added to it |
| `D3D9WEB_RUN_TIME_PROFILE sample_us` | worker-local `emscripten_get_now`; independent nominal 10-second window per guest worker; one in 32 `cpu->run()` calls | elapsed sampled `cpu->run()` duration, including interpreter/dispatcher/decode/MMU and any synchronous wait entered by that sampled run | 31 unsampled runs; idle time between runs; a synchronized whole-process wall denominator | **REUSE** for module/block shares inside one accepted `pid,tid` sampled-time window, or a weighted set of the same render thread |
| `RUN_TIME_PROFILE wall_us` | same worker-local window as its `sample_us` | real elapsed duration from that thread's first recorded sample until a later sampled call checks the 10-second threshold | alignment with any other worker, bridge 120-Present reset, or main-thread JS reset | **DO NOT USE** to extrapolate absolute CPU active time or merge workers |
| `D3D9WEB_HOST_JS_PROFILE total_us` | main-thread `performance.now`; reset every 120 `dispatchBatch` calls | `dispatchBatch` packet walk, every contained JS command dispatch, and synchronous WebGL calls | Emscripten proxy scheduling/wait outside the JS function; BoxedWine copies; direct `dispatch` calls; asynchronous GPU completion | **REUSE** as standalone per-batch JS cost; not subtractable from an unjoined `proxy_us` window |
| `D3D9WEB_GPU_PROFILE avg_us` | asynchronous WebGL elapsed-time queries, accumulated for 120 submitted batches and reported when results become available | GPU elapsed time for returned valid query samples | CPU submission, worker/main scheduling, and queries still pending or discarded | **REUSE** only as standalone GPU-per-batch evidence, not a synchronized frame partition |
| external Present-count windows | controller/main-thread wall interval around two observed completed Present counters | all causes which change completion rate during that observation | attribution to any internal component | **REUSE** for release A/B FPS when scene/workload and interval selection are equal |

## VERIFIED -- exact copy and proxy placement

The ordinary INT `base+2` path performs these steps in order:

1. guest `d3d9.dll` constructs a command packet, historically through
   `ByteCopy` for large payloads;
2. BoxedWine executes
   `cpu->memory->memcpy(commandBytes, arg1, arg2)` before any proxy timer;
3. BoxedWine resizes and copies into `batchedCommandBytes`, also before the
   proxy timer;
4. at a flush boundary, `proxy_us` begins immediately before
   `MAIN_THREAD_EM_ASM_INT` and stops after its synchronous return;
5. main-thread JS uses a shared `HEAPU8.subarray`; there is no explicit
   additional JS-heap packet copy in this bridge;
6. `dispatchBatch` walks commands and submits WebGL work.

Direct upload and DirectDrawUP remove the interpreted bulk ByteCopy but not
the compiled copy into the ordered batch. Their `cpu->memory->memcpy` calls
remain outside `proxy_us`. Consequently, `proxy_us / wall_us` is an upper
bound only for deleting the measured synchronous proxy sections. It is not an
upper bound for all host/bridge optimization, and making `proxy_us` zero does
not remove guest packet work or either BoxedWine copy stage.

`present_int_us` encloses the Present-side BoxedWine copy and the synchronous
proxy interval. It therefore overlaps `proxy_us`; adding both double counts
the Present proxy wait. The sampled `d3d9.dll!D3D9WebCall` block can enclose
the same synchronous wait again, so guest sampled module/block shares must
also not be added to bridge proxy percentages.

## VERIFIED -- Present wall interval details

`profileNow` is read after the Present command has been copied, flushed to the
main thread, dispatched, and returned. After a completed window, the next
`wall_us` is therefore the interval from one post-Present completion to the
completion 120 Presents later. It is the best retained common wall denominator
for bridge counters from the same log line.

The first-ever bridge report is special. `profileWindowStart` is initialized
at the first observed Present, while `profilePresents` reaches 120 at Present
120, so its wall interval contains 119 inter-Present gaps. `proxy_us` may also
already contain startup calls made before that first Present because it is not
cleared when `profileWindowStart` is initialized. Only later consecutive
windows, after transition/load rejection, are reusable.

External five/ten-second Present counts measure the same user-visible
completion rate but do not share the bridge counter reset. They remain valid
FPS evidence and cannot be used as the denominator of a particular
`proxy_us` record without a logged join point.

## VERIFIED -- worker clocks are durations, not joined timestamps

The time profiler has a `thread_local` profile and `windowStart` for every
guest worker. The threshold is tested only after that worker happens to take a
sampled `cpu->run()`. An active render worker reports near ten seconds; an idle
worker can report much later. Reports from different `pid,tid` values neither
start nor end together.

BoxedWine bridge durations use the worker's `KSystem` microcounter, the sampled
CPU profiler uses worker `emscripten_get_now`, guest DLL timers use emulated
QueryPerformanceCounter, and host JS uses main-thread `performance.now`.
Their duration units can all be converted to microseconds, but the logs carry
no shared start/end sequence or correlation ID. Equal units do not establish
a common window. Multiple guest workers can also run concurrently, so their
CPU-thread durations may legitimately sum beyond one wall interval.

The bridge counters themselves are function-static rather than thread-local.
Existing measurements are valid for the observed single Azrok render caller,
but mixing from multiple concurrent guest D3D callers is not dynamically
excluded by the implementation.

## Retained values and corrected interpretation

### Document 193 historical pre-optimization window

The eight stable 120-Present averages remain valid for that exact build and
scene:

| Retained value | Valid interpretation |
|---|---|
| `wall_us = 16,107.6 ms`, 7.47 FPS | elapsed Present completion rate |
| `proxy_us = 4,720.6 ms` | 29.31% of the same bridge wall spent inside timed synchronous runtime calls |
| `packet_copy_us = 1,280.6 ms` | historical instrumented guest packet-copy duration; not present in the current source writer path |
| `present_int_us = 407.9 ms` | guest Present round trips; overlaps the Present portion of `proxy_us` |

These four values are not four disjoint bins. In particular, Present INT is a
subset/overlap of proxy work, and guest/bridge snapshot resets have no logged
correlation ID.

### Documents 199 and 201 sampled guest shares

Document 199's four accepted `pid=71,tid=72` windows support the weighted
sampled-time shares `acknex 42.4%`, `d3d9 36.6%`, and `other 20.9%`, including
the then-present proxy ByteCopy hotspot. Document 201's post-DirectDrawUP
windows support its later `acknex about 60--61%`, `d3d9 about 7--9%`, and
other `30--32%` sampled-time characterization.

Both are distributions of sampled render-thread `cpu->run()` elapsed time,
not percentages of a frame's wall time. They cannot be applied to an assumed
50 ms frame and then combined with bridge/JS/GPU timings. A sampled
`D3D9WebCall` includes synchronous waiting, so the module totals are not pure
guest instruction-execution costs either.

### Host JS and GPU

Document 198's `0.32--0.39 s / 120 batches` remains valid as host
`dispatchBatch` CPU-side duration for those exact batches. Document 184's
roughly 2 ms GPU query result remains valid GPU evidence. Neither has a join
key to a specific bridge 120-Present record, and host batch counts are not
guaranteed equal to Present counts when size/resource flushes occur.

## Values to discard

| Value or calculation | Verdict | Reason |
|---|---|---|
| old `D3D9WEB_CPU_PROFILE.samples` converted to module CPU percent | **DISCARD** | instruction-count sample, per-thread denominator, report trigger only at a sample |
| `active_pct_x100` / `est_active_us` from run-time profile | **DISCARD** | timer quantization and 1/32 extrapolation already exceeded wall time |
| `wall_us - proxy_us = guest CPU` | **DISCARD LABEL** | the residual is valid unclassified wall, but includes guest copies, guest execution, waits, scheduling, and other host work |
| `proxy_us - HOST_JS total_us = proxy scheduling` | **DISCARD** | independent reset windows, batch-only JS timer, possible direct calls, no join ID |
| guest module shares + `proxy_pct` + JS/GPU percent | **DISCARD** | synchronous waits overlap and windows differ |
| multiplying sampled Acknex/D3D9 shares by a 50 ms frame budget | **DISCARD** | sampled guest-run denominator is not frame wall time |
| current `packet_copy_us=0` as proof of no packet construction | **DISCARD** | current source no longer increments the advertised packet-copy counters; zero can mean absent instrumentation |
| first 120-Present bridge profile after startup | **DISCARD** | 119 frame gaps plus startup proxy accumulation |

## What can be combined now

1. In one non-first `D3D9WEB_BRIDGE_PROFILE` line, `wall_us`, `proxy_us`,
   Presents, batch/direct/upload counters, and bytes have one reset window.
2. In one `D3D9WEB_GUEST_PROFILE` delta with `present_delta=120`, guest QPC
   timers and copy-site counts share one guest snapshot interval; overlapping
   timers must still not be summed.
3. In one `D3D9WEB_RUN_TIME_PROFILE` line, module and block values share
   `sample_us`; accepted windows from the same render `pid,tid` may be weighted
   by `sample_us`.
4. In one `D3D9WEB_HOST_JS_PROFILE`, total/average/max share exactly 120 batch
   calls.

No retained log supplies a single correlation ID that joins all four groups.
A true frame-budget partition still requires one render-thread Present epoch
and common monotonic timestamps/counters emitted together for guest execution,
guest command construction, BoxedWine copy 1, BoxedWine copy 2, proxy wait,
main-thread JS, and asynchronous GPU completion.

## Source evidence

- `source/emulation/cpu/normal/normalPlatformMultiThreaded.cpp`: sampled
  `cpu->run()` timer, thread-local window, 1/32 selection, report/reset.
- `source/opengl/d3d9web.cpp`: guest-memory copy, batch-vector append,
  `MAIN_THREAD_EM_ASM_INT`, `proxy_us`, and bridge 120-Present wall window.
- `tools/d3d9_web_backend/d3d9_web.cpp`: guest QPC counters, direct upload,
  Present timer, and current orphaned packet-copy counters.
- `tools/boxedwine_local/web_backend/host/d3d9web-runtime.js`: guest snapshot
  deltas, batch JS timer, Present handling, and GPU query aggregation.

## Status

- **VERIFIED static + retained dynamic interpretation:** the usable local
  denominators and all overlap/exclusion boundaries above.
- **NOT VERIFIED common frame partition:** existing logs have no cross-worker
  epoch or join key.
- **NO RUNTIME CHANGE:** no browser, guest, server, production, or Emscripten
  asset was started or modified.

