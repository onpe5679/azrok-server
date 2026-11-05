# 447. Detached workload-preflight and host-priority sampler contract

Date: 2026-07-26  
Status: **VERIFIED source/parse gate; live preflight-FPS leg remains NOT VERIFIED**

The attached sampler now accepts `-ExpectedWorkloadFingerprint` only with
`workloadFingerprint=1` in the URL. Before warmup it requires the runtime
status snapshot to be present, clean (`invalid/rejected=0/0`), detached, and
equal to the canonical exact tuple:

```text
version:frames:batches:bytes:hash:invalid:rejected
```

For the admitted 443--445 state the required value is
`1:120:21480:14158560:2109626789:0:0`. A fingerprint query without that exact
sampler requirement is rejected; an expected value without the query is also
rejected. Existing no-fingerprint sampler legs retain their prior URL path.

The preflight observer's clean-only detach restores original `dispatchBatch`
before sampler warmup. The sampler additionally records a CIM priority
distribution of the complete CDP-bound Edge tree and competing ChatGPT/chrome
processes before and after the interval; it introduces no uncalibrated
priority threshold.

PowerShell parse passes. Static review of this new reader remains required
before a live preflight-enabled FPS leg.
