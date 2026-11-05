# 454 - Accepted control rate / async synchronous-drain correlation

> Status: **VERIFIED correlation and mechanism boundary; causality NOT VERIFIED.**

## Read-only runtime evidence

On the already-detached accepted A6 page, the exact sealed workload snapshot
remained `1:120:21480:14158560:2109626789:0:0` with matching command arrays and
no fingerprint error. Existing textarea output contains 120-Present windows
with submitted/reaped `120/120`, no ring error and no ring-full wait.

| existing row class | count | elapsed-ms median | range |
| --- | ---: | ---: | ---: |
| `sync_drains=0` | 70 | 724.375 | 607.370-1008.190 |
| `sync_drains=120` | 129 | 3112.820 | 2698.885-3991.985 |

One `sync_drains=109` row was 14302.425ms. This is a strong same-process,
same-fingerprint association, not an FPS sample or a causal identification.

## Static mechanism boundary

`d3d9web.cpp` increments `synchronousDrains` only when the guest worker calls
`reapNextAsyncBatch(true)` and futex-waits until a main-thread async
`dispatchBatch` callback has returned and marked its slot completed. The
boundary reaper used to print the 120-Present row is nonblocking. Therefore
`sync_drains` counts worker-side waits for JS dispatch completion; it is not
GPU/compositor completion or scanout FPS.

The page also has an unbounded output path: recurring ring/runtime `klog` text
is appended to the hidden textarea, and page code reads its entire value every
500ms. This is a process-local performance candidate, but its contribution is
NOT VERIFIED until output length/CPU and rate are directly correlated.

No production code, browser flags, cache or candidate asset changed. The next
fresh accepted control uses the repaired temporal rate gate; its diagnostics
must remain read-only before any causal conclusion.
