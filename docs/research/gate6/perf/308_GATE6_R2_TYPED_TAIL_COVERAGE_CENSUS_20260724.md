# 308 — R2 typed direct-tail coverage census

## Status

**VERIFIED static/build/fresh-record; dynamic census BLOCKED fail-closed.** This is a diagnostic-only
postmortem continuation of rejected R2 (293), required to separate the actual
execution coverage of retained zero-reloc helper fallbacks from cold-wrapper
entry volume. It does not reopen R2, does not produce an FPS sample, and cannot
by itself attribute the observed whole-candidate regression to either cost.

## VERIFIED fixed static population

R1 and R2 both contain 147 groups and 34,322 paired entries. R1 has 3,472
store-sunk typed tail sites, 27,776 patch operands and 194,432 sunk terminal
GP-store bytes. R2 has 2,715 sites, 21,720 operands and 152,040 bytes. The
exact difference is 757 tails, 6,056 operands and 42,392 retained bytes.

The 5,299 figure from the original malformed cache is `757 x 7`; R1's repaired
nextOp form has eight operands per site, hence the R1/R2 exact delta is
`757 x 8 = 6,056`. It is invalid to use the 3,316 zero-reloc *entries* in the
R2 manifest as a substitute for the 757 exact source-tail sites.

## Verified probe boundary

The private diagnostic must add four `(CPU*) -> void` helpers that only perform
relaxed atomic U64 increments, plus a 32-byte snapshot ABI:

| counter | exact location | meaning |
| --- | --- | --- |
| wrapper | paired wrapper body entry | cold public wrapper entered |
| typed body | typed body entry | wrapper or admitted direct tail entered typed body |
| admitted tail | guarded tail's success arm immediately before typed `return_call` | all publication, bailout, yield and depth guards passed |
| zero-reloc fallback | original matched eight-store + `fn_6` terminal path for the separately identified 757 source sites | retained zero-reloc helper fallback executed |

The pipeline must retain a distinct zero-reloc target set after its normal
admission filter. It may insert the probe only after the exact threaded
fetch-return and eight-GP-store suffix match; a target-entry or reloc-array
count is insufficient. The counter cache must declare its helper indices,
snapshot ABI and exact static `2715 + 757 = 3472` split. A normal R2 loader or
counter loader must reject the other cache before registration.

## VERIFIED implementation and build gate

The private target is
`azrokMultiThreadedJitAudioO3AsyncRingThreadedTailCensus`, built with the
separate `BOXEDWINE_WASM_JIT_THREADED_TAIL_CENSUS` macro and three new public
snapshot/getter exports. Its page rejects any missing, extra or mismatched
census ABI before group registration: version 1, four distinct helper imports,
32-byte snapshot, and the fixed `34,322 / 2,715 / 757` static populations.
The pipeline independently fails closed if a newly recorded source cannot
reproduce 34,322 wrapper sites, 2,715 admitted tails, 757 exact zero-reloc
fallback markers, 21,720 direct-call patches, and the `2,715 + 757 = 3,472`
total. It never emits an ordinary R2 archive when the counter option is set.

The marker helpers cross into C++ and therefore are observational
instrumentation only, not a low-overhead optimization or a timing sample.
They change no guest CPU state apart from process-lifetime relaxed atomic
counter storage. The page exposes an explicit refresh function/event instead
of a periodic timer, so the later visible interval can be sampled without a
page-side polling loop. The separate low-priority build completed through the
Git-Bash POSIX toolchain after the native-Windows `make` shell was verified
unsuitable (`mkdir -p`/`grep` unavailable). The built diagnostic Wasm validates
directly in Node (59 exports); its generated glue binds all three census
exports plus the required dual-entry pair exports. Pipeline syntax and the
pre-existing 9-case threaded-GP loader gate also pass. The new census loader
gate verifies 13 page fragments, seven pipeline fail-closed fragments, and
nine valid/malformed manifest cases. Browser record/replay and dynamic counter
values remain **NOT VERIFIED**.

## Required dynamic gate

Run only the private counter artifact: cache-off render, isolated record,
verified counter manifest/replay, normal `(100,500)` then `(90,722)` selection
pulses, and snapshots after registration, after each pulse and after an
uninterrupted visible PatHouse interval. No Present/FPS timer is collected.
The runtime must satisfy `typedBody == wrapper + admittedTail` for snapshot
deltas; a failure invalidates the diagnostic. Zero-reloc coverage may rank a
future investigation, but neither zero nor nonzero coverage proves a time
cost or authorizes re-enabling R2.

## Fresh-record corpus gate -- VERIFIED blocked

The private counter runtime was visibly driven from character selection using
the normal `(100,500,140)` then `(90,722,140)` pulses and reached the complete
PatHouse 3D scene before saving its cache-off record. The isolated raw is
`profiles/azrok-jit-record-r2tailcensus1-20260724-112023.zip`, with 34,226
entries, 50,714,251 bytes and SHA-256
`6BD19F44148B8BE19BA51F6C6AB4CDAB011FF02350A41F478F3221729F304AFF`.

This is **not** the rejected R2 corpus. The static census gate intentionally
requires 34,322 wrapper entries, 2,715 admitted tails, 757 zero-reloc markers
and 21,720 patches. The new record is six entries short; the two retained
older raw archives are both 41,792-entry corpora. The known original R2 input
was 50,346,643 bytes/34,322 entries, but no matching ZIP remains anywhere in
the workspace (only the R1/R2 output manifests and grouped archives remain).
Consequently the diagnostic pipeline was first rejected for the omitted raw
`pfnJitCode/nextOp` fields, then stopped before expensive transformation once
the already-known 34,226 versus 34,322 mismatch was verified. No counter cache
was emitted, no replay was attempted, and no dynamic counter value is claimed.

Re-enable this *coverage-only* card only if the exact 34,322-entry R2 raw
corpus is recovered. Do not relax the fixed static population or substitute a
newer record: doing so would no longer quantify the rejected R2's 757-site
zero-reloc fallback scope against its 34,322 wrapper population.
