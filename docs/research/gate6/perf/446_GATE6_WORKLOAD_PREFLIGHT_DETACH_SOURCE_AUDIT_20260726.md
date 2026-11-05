# 446. Workload preflight detach source audit

Date: 2026-07-26  
Status: **VERIFIED static detach gate; runtime preflight/FPS remains open**

445 established that the command-shape proxy matches across fresh accepted and
INT9A candidate diagnostics, but its packet parser must not run during an FPS
interval. The observer now publishes a 120-Present snapshot and restores the
original bound `dispatchBatch` only after the successful 120th dispatch has
returned. Thus subsequent async callbacks execute the original host dispatcher
with no parser/hash hot-path overhead.

Static audit confirms the restore is safe within the synchronous main-thread
dispatch call: the current call's original result/side effects are complete,
the full JSON snapshot is published before detached state, and later callbacks
observe either the wrapper or the original dispatcher, never partial state.

A review P1 found that dirty snapshots could previously claim detached. It is
repaired: only `invalidBatches=0` and `rejectedBatches=0` publish
`workloadFingerprintDetached=1`; dirty snapshots retain an explicit error and
continue diagnostic observation. Node extraction parses the repaired function.

The next card must add a sampler-side reader that requires the exact clean
fingerprint and detached state before its 30-second interval, while retaining
the 442 host-priority before/after record. No FPS measurement was taken.
