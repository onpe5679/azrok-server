# 355 — accepted cache generic-indirect ABI reject (2026-07-25)

## VERIFIED

The accepted baseline stall from 354 was not a worker failure. A read-only
worker-message probe observed all 32 workers send numeric `cmd:3` (loaded).
With zero registered groups, re-entering the page-owned runtime callback was
safe and directly exposed the original fail-closed exception:

```
generic indirect cache ABI mismatch
next=740/740 depth=1660/1660 bailout=132/132 pfn=12/12
map=12968408/12964392 cap=262144/262144
```

The first number in each pair is the live served ABI2 runtime; the second is
the accepted grouped-cache manifest. Only `relocMapBase` differs (4,016 bytes).
The existing 134-group archive is correctly refused before C++ registration.
This explains the stale staging marker in 354 and proves neither a benchmark
nor a candidate verdict may use the archive.

## Required next step

The mutable generic raw alias is currently the preserved R2 census alias, not
the historical accepted recording. A current ABI2 cache-off record must be
saved under an immutable accepted-specific name, transformed with live exact
generic-indirect offsets, statically audited, and replay-rendered before any
accepted baseline or MRG2 A-B-A measurement.
