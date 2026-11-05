# 369 -- FISTP FQ1 cache-OFF browser outcome census (2026-07-25)

Status: **VERIFIED static and dynamic; diagnostic coverage only**

## Runtime identity and integrity

The existing sole CDP `page` target was used throughout. It was visible and
loaded only the private FQ1 route:

```text
runtimeStem=boxedwine.upstreamjit64fn6inlineabi2fistpqwordcensus1
jitCacheUrl=off
fistpQwordCensus=1
```

The URL has no record, Present-capture, replay, or other census flag. Resource
Timing directly named the private JS and Wasm. The live page reported FQ1 ABI
1 and 5,188 words; canvas CSS was 1024x768 (backing 640x480) and direct
Present advanced 453 -> 1,343. Observed async-ring windows had `errors=0`.
One later window had `ring_full=1` / `sync_drains=8`; this is retained as
evidence, so no claim is made that the ring was never full.

## Reader repair

**VERIFIED static:** the generated helper tag and the operation-local
`CPU::runNextSingleOp()` normal/catch boundary from 368 are unchanged. The
loader verifier passes after the page-reader repair.

The first raw live snapshot had valid cached-ST0 lanes while ABI/layout,
entry partition, outcome partition, invalid-tag and invalid-metadata checks
all passed. Therefore the former page-only `cached!==0` rejection was not a
source-level FQ1 contract and was removed. Cached-ST0 remains an observed
helper-boundary context axis; it must not alone classify an inline versus
helper dispatch route. The reader still fail-closes on layout, entry/outcome
partition, invalid tag, or invalid metadata.

## Direct snapshots

Each read used ABI-gated `azrokRefreshFistpQwordCensus()`. All rows satisfy:

```text
fn8Total = otherOpcode + invalidTag + invalidMetadata + context
context = normal-pop + normal-no-pop + fault
```

| Snapshot | fn_8 total | other opcode | invalid tag/meta | FISTP context | normal-pop | no-pop | fault | cached-ST0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S0 before pulse | 4,014,271 | 3,407,066 | 0 / 0 | 607,205 | 607,205 | 0 | 0 | 10 |
| S1 30 s after pulse 1 | 4,692,859 | 3,939,354 | 0 / 0 | 753,505 | 753,505 | 0 | 0 | 10 |
| S2 30 s after pulse 2 | 7,276,007 | 6,314,078 | 0 / 0 | 961,929 | 961,929 | 0 | 0 | 22 |

| Independent post-input interval | fn_8 delta | other-op delta | FISTP delta | normal-pop | no-pop | fault | cached delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| S0 -> S1, 30 s | 678,588 | 532,288 | 146,300 | 146,300 | 0 | 0 | 0 |
| S1 -> S2, 30 s | 2,583,148 | 2,374,724 | 208,424 | 208,424 | 0 | 0 | 12 |

The cumulative nonzero context records are four sparse records; their S2
normal-pop counts are 956,803, 6, 22 and 5,098. No record has no-pop or
fault. This is positive production-scene normal-pop coverage, not a claim
that protected destinations never fault: FQF1/FQF2 independently prove the
required normal and protected-destination rows (365, 367).

## Decision

FQ1 is complete as a private cache-OFF outcome census. The two 30-second
post-input intervals did not observe no-pop or fault, which is reported only
as bounded scene coverage. No accepted runtime, cache, replay, or performance
path changed. The next isolated card may proceed under its own gate.
