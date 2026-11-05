# 448. Preflight sampler clean-tuple repair

Date: 2026-07-26  
Status: **VERIFIED static repair; live preflight-FPS remains NOT VERIFIED**

Static review of 447 found a P0: exact expected-string comparison alone could
accept a caller-supplied dirty expected tuple. The reader now independently
requires runtime `version=1`, `frames=120`, `invalidBatches=0`, and
`rejectedBatches=0`, and the caller-supplied expected value must match the
clean canonical form `1:120:<batches>:<bytes>:<hash>:0:0` before CDP access.

The reader remains after exact runtime identity and before viewport/memory
checks, settle, warmup, and the 30-second interval. No-fingerprint URLs with
an empty expected value retain the prior sampler behavior. PowerShell parsing
passes. This closes source validation only; a new source-fresh page must still
prove clean detach before the first preflight-enabled FPS sample.
