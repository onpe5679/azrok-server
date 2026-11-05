# 417 -- Gate 6 logical-composite32 post-scene A-B-A-B rejection (2026-07-26)

## Verdict

**VERIFIED whole private logical-composite32 candidate: REJECTED.**

The only eligible comparison used four fresh-profile, one-page, visible
30-second direct-Present rows after the corrected post-scene working-set
contract.  All rows used the isolated watcher Edge, required anti-throttling
argv, CSS 1024x768, zero upper-window overlap, stable HWND/viewport, target
process-tree working set, free-memory floor, no build process, and the
50%-collapse floor.  Candidate rows additionally required exact private
replay `92/30061/28632`, logical ABI `1`, and live tuple `1:108:328`.

```text
fresh A1 accepted  1405 / 30.006674s = 46.8229 FPS
fresh B1 candidate 1204 / 30.012279s = 40.1169 FPS
fresh A2 accepted  1279 / 30.002533s = 42.6297 FPS
fresh B2 candidate 1163 / 30.012734s = 38.7502 FPS

B1/A1  -14.3221%
B1/A2   -5.8945%
B2/A2   -9.1005%
median  -9.1005%
```

The median is decisively outside the ±3% noise band, so this private stem,
record, grouped cache and production arm cannot be adopted.  The first B2
attempt produced no row: `CloseAsync` raced a later CDP text event after the
window and masked the completed measurement.  It is excluded.  The fresh
B2 retry used best-effort `CloseOutputAsync` cleanup and is the valid fourth
row above.

## Harness corrections retained

The run exposed measurement-harness defects before timing and repaired them
fail-closed: later legs now use a healthy A's **post-sample** working set;
the target HWND is selected from the CDP browser window rather than all Edge
windows; unrelated user Edge process trees are recorded but excluded from the
target-tree working-set total; and CDP close cleanup cannot hide a completed
result.  The failed preflight attempts and old B1 working-set rejection are
not FPS evidence.

## Cause accounting

405's direct census admits only 61,281 / 1,470,907 composite helper entries
(4.166%); 407 already established that this is coverage, not a time bound.
The rejected private cache also has a separately recorded corpus shape of
92 groups / 30,061 entries / 28,632 patches, versus accepted's 94 / 30,550 /
28,944: -2 groups, -489 entries (-1.60%), and -312 patches (-1.08%).  Both
use direct calls.  Consequently this A-B-A-B rejects the **whole private
candidate**, but does **not** prove that the six-condition inline formula
itself is the -9.10% cause; the separate record/cache workload is a remaining
confound.  No narrower arm-only timing witness exists, and no causal claim is
made beyond the rejection.

The practical conclusion is still decisive: an optimization whose observed
eligible coverage is only 4.166% and whose complete private deployment loses
9.10% median FPS has no performance case for further tuning.  Preserve the
semantic fixture and replay evidence, leave the accepted stem untouched, and
move to 401's INT 0x9A joined-census diagnostic rather than contaminate it.
