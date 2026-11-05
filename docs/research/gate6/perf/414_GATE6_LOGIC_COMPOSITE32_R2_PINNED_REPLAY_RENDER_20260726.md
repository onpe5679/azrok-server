# 414 -- Gate 6 logical-composite32 R2 pinned grouped replay render (2026-07-26)

## Status

**VERIFIED private transform, immutable replay identity, and visible replay
render.  No timed performance comparison or adoption decision has occurred.**

The immutable R2 raw archive from 413 was transformed only after the pipeline
checked its raw ZIP-entry manifest digest and exact live runtime overrides:

```text
raw manifest       a0f062874bc2b7005ad2ed47689f5e87c1977349eecc9d812b93a9489f62a901
CPU result/type    108 / 328
CPU nextOp/pfn     740 / 12
```

The first two transform starts failed before output was written: one exposed
the omitted direct-stitch fields in the raw record, and one located no default
Binaryen module from the workspace root.  Both are fail-closed input/config
outcomes, not render results.  The final command explicitly supplied the
directly measured fields and the exact local `binaryen_js.js` path.

It optimized all 30,061 modules into 92 groups and produced the private
artifact below.  Its pinned source identity and semantic descriptor exactly
match the private R2 stem and the production arm:

```text
archive SHA-256:          628cde3eba268ece091d9615e404963d07013996f8d9ffaa4dadc45f93a7fc26
grouped manifest SHA-256: 65cbf8fc5240ee99c93a6b7c7e36edf1fc3a767aca16e47a29fd9fb28bc4c541
groups / entries / patches: 92 / 30061 / 28632
direct tail sites: 9544 (next1,next2 only)
runtime identity: azrok-runtime-logic-composite32-v1
descriptor: ABI 1, result/type 108/328, logical {6,15,21,42},
            conditions {6,7,12,13,14,15}, FLAGS_NULL_ONLY,
            helpers.cond-composite fallback
```

The loader verifier now exercises the extracted identity function with the
exact tuple and independently mutates raw-manifest, archive, grouped-manifest
and stem values; each mutation rejects with its specific fail-closed reason.
It also requires the two layout exports and the replay code compares their
live values to the descriptor before any group registration.

The first pinned replay navigation correctly stopped before guest start at
the old MRG preflight's `unknown-private-runtime-identity` rejection.  This
identified a loader composition defect, not an allowed bypass: the MRG gate
was amended to defer this one recognized identity to its own stricter gate,
while all other unknown identities still reject.  The static/mutation verifier
passed again after that repair.

On the sole visible CDP page, a real CDP pointer click then produced:

```text
JIT group registration: 92 groups, 30061 blocks
runtime ABI/result/type: 1 / 108 / 328
replay live tuple:       1 / 108 / 328
registered patches:      28632
canvas CSS:              1024x768
```

After game startup, direct output showed continuing Present windows and a
healthy 120/120 async-ring window with `errors=0`; the immediate later window
also had `ring_full=0`, `sync_drains=0`, `errors=0`.  The transient Wine SEH
trace preceded this normal rendering and is not a candidate verdict.  No
30-second Present button/capture was invoked, so none of these liveness values
are FPS evidence.

## Boundary and next gate

This closes private candidate cache-OFF -> record -> exact transform -> pinned
replay render.  Accepted, parity, MOVSD, fixture and census assets are
unchanged.  The only next candidate action is fresh-process, visible,
environment-gated accepted-A -> logical-composite32-B -> accepted-A (extend
to B if drift) 30-second Present measurement.  Its result alone may adopt,
reject or leave the optimization undecided.
