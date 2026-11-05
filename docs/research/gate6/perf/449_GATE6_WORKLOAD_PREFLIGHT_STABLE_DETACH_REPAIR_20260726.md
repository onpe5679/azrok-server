# 449. Workload preflight stable-detach repair

Date: 2026-07-26  
Status: **VERIFIED live early-window mismatch and static repair; FPS remains NOT VERIFIED**

The first source-fresh preflight-enabled accepted page reached real Present but
its first 120-Present window was bootstrap-adjacent, not the stable 443--445
shape:

```text
frames=120 batches=4105 bytes=2322636 hash=1748807967 invalid/rejected=0/0
```

It automatically detached before the expected stable tuple could be observed.
The sampler would reject this mismatch, so no 30-second FPS window was started.

Automatic detach is removed. The observer now continues publishing clean
windows, while `azrokDetachWorkloadFingerprint()` is an explicit CDP action
that succeeds only after a clean published snapshot. A future preflight must
observe the exact stable tuple, invoke that detach, confirm detached state,
then start the sampler in the same fresh process. Node extraction parses the
repair.
