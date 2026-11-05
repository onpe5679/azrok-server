# 457 - INT9A post-warmup control consensus baseline

> Status: **VERIFIED control cluster; A8 cause NOT VERIFIED.**

Fresh accepted A10 retry passed all 453/451/454 structural and post-warmup
conditions and measured 42.0826 FPS.  The three independently fresh controls
A7/A9/A10 are 42.5187/42.7822/42.0826 FPS: max-min is 1.65% of their median,
inside the 3% noise band.  Their median, 42.5187 FPS, is the accepted-control
consensus baseline for the next fresh candidate comparison.

A8 retry 39.1235 FPS remains a valid structural sample and is preserved; it
does not have a failed gate.  It is an isolated low observation against the
three-control consensus, not a candidate comparison and not proof of a second
mode.  Its cause is NOT VERIFIED.  It is excluded from the consensus only
because three independent fresh controls reproduce the other mode within the
predefined band; the exclusion and all raw rows remain explicit.

Next: fresh private INT9A B1 under the identical manual-detach, post-warmup
rate-stability, visibility, memory, working-set and priority contract. Any
candidate decision still requires the prescribed fresh A/B alternation.
