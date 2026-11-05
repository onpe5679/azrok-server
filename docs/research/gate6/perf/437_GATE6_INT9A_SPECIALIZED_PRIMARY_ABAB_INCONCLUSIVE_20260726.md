# 437. INT 0x9A specialized primary fresh-process A-B-A(B) is inconclusive

Date: 2026-07-26  
Status: **VERIFIED individual samples and hygiene; NOT VERIFIED performance effect**

## Contract and first accepted reference

Every leg used a watcher-provided fresh Edge process at the primary-display
rectangle `(710,20)-(1800,1590)`.  The launch contract retained all three
anti-throttling flags, one ordinary CDP page target, a visible/focused page,
CSS canvas `1024x768`, unchanged outer rectangle, and zero upper-window
overlap before and after its measurement.  The attached sampler also verified
the exact replay identity, no build processes, complete Edge process tree,
working-set ceiling, and free-physical-memory floor before and after every
row.  Each row is a visible direct-Present 30-second interval.

The first two fresh accepted legs were stable:

| leg | stem/cache | Present FPS | Present delta / wall | free memory before | Edge WS after |
|---|---|---:|---|---:|---:|
| A1 | accepted, 94/30,550/28,944 | 40.8569 | 1,226 / 30,007.168 ms | 141,320.07 MiB | 4,200.92 MiB |
| A2 | accepted, 94/30,550/28,944 | 40.8876 | 1,227 / 30,009.070 ms | 143,076.86 MiB | 4,278.80 MiB |

Their separation is `+0.0751%`, so their provisional primary reference is
40.87225 FPS.  The collapse floor was 20.436125 FPS.  This is a local
same-session reference only; it is not a 60-FPS target claim.

## Remaining fresh legs

The private B identity was exact `154/48,902/41,721`, specialized helper ABI
1, and `int9aSpecialized=1`; A identities were the accepted 94/30,550/28,944
replay.  The following rows all independently passed the structural contract
above and are retained verbatim in
`artifacts/performance/int9a_specialized_primary_20260726.csv`:

| order | role | Present FPS | Present delta / wall | free memory before | Edge WS after |
|---|---|---:|---|---:|---:|
| B1 | private INT9A | 34.5520 | 1,037 / 30,012.746 ms | 143,114.93 MiB | 3,878.64 MiB |
| A3 | accepted | 27.2212 | 817 / 30,013.347 ms | 139,724.67 MiB | 4,193.27 MiB |
| A4 (stability extension) | accepted | 42.6813 | 1,281 / 30,013.155 ms | 140,554.52 MiB | 4,178.47 MiB |
| B2 | private INT9A | 104.7108 | 3,143 / 30,015.996 ms | 138,987.76 MiB | 3,573.42 MiB |

All four values exceed the collapse floor and no window, visibility,
working-set, free-memory, process-tree, replay-identity, or build-CPU gate
failed.  Therefore they are **VERIFIED observations**, not deleted or relabeled
as failed harness rows.

## Performance decision

No performance adoption or rejection is authorized.  The required adjacent
comparison is not stable: B1 is `-15.4952%` against A2 but `+26.9305%`
against the immediately following A3; A3 itself is `-33.4243%` against A2,
and the added fresh accepted A4 rebounds to `+4.3869%` against A2.  The final
B2 is `+145.3318%` against preceding A4 (and `+284.6664%` against A3).
These sign changes are far beyond the ±3% noise rule.

Thus an identity-correct, visible, fresh-process test can still have an
unobserved scene/runtime-state axis.  Its cause is **NOT VERIFIED**: the
existing contract proves window and resource hygiene, but it does not prove
that the guest simulation/render workload is the same in every 30-second
interval.  It would be incorrect to attribute B1's slowdown or B2's speedup
to the specialized helper, or to claim a 60-FPS result.

The INT9A private record/replay/render result in 436 remains valid.  Before
any retry, a separate measurement-contract card must identify and gate a
directly observable same-scene/same-workload witness; it must be validated on
fresh accepted controls before it can be used to judge the private candidate.
