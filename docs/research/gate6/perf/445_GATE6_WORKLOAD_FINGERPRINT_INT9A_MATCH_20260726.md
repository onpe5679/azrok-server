# 445. Workload-fingerprint INT9A candidate match

Date: 2026-07-26  
Status: **VERIFIED role-neutral command-shape match; FPS contract revision remains open**

A fresh INT9A specialized replay (`154/48,902/41,721`, ABI1) completed the
same non-FPS diagnostic and sealed:

```text
frames=120 batches=21480 bytes=14158560 hash=2109626789
invalidBatches=0 rejectedBatches=0
```

Every command-call and command-byte array entry matches fresh accepted A1
(443) and A2 (444), and the same error-free terminal async-ring window was
observed. Thus the current candidate and controls share this direct
role-neutral command-shape/workload proxy across fresh processes.

This materially narrows the uncertainty exposed by 437: the prior sign
reversal can no longer be dismissed merely as a different emitted D3D command
shape in the admitted diagnostic state. It does not prove semantic room/camera
identity, nor does it prove that a later FPS process will retain the tuple.

The next measurement-contract revision must use the tuple as a per-leg
preflight, then detach the observer before the 30-second FPS interval so its
parsing overhead is absent from both A and B. The new host-priority snapshot
fields from 442 must be recorded alongside that interval. No candidate
performance decision changes in this document.
