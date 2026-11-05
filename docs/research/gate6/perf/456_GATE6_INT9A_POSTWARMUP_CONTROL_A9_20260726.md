# 456 - INT9A repaired post-warmup control A9

> Status: **VERIFIED observation; baseline not yet fixed.**

Fresh A9 passed the exact clean/detached workload fingerprint, post-warmup
rate-stability gate, visibility/window/launch/memory/working-set gates and
produced 42.7822 FPS.  Its accepted preflight pair was 41.9873/42.3515 FPS.

It agrees with A7 42.5187 FPS by 0.6%, but differs from the valid A8 retry
39.1235 FPS by about 9%.  A8 is not retrospectively invalidated: no gate
failure identifies it as an outlier.  Therefore no accepted baseline and no B
leg are authorized. The next action is a fresh A10 control under the same
contract.
