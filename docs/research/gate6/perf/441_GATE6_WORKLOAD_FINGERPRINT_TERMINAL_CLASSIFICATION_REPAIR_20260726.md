# 441. Workload-fingerprint terminal classification repair

Date: 2026-07-26  
Status: **VERIFIED diagnostic failure and static repair; clean runtime remains NOT VERIFIED**

## First sealed window

The repaired callback-order accepted diagnostic visibly reached real Presents
and sealed a 120-terminal-Present fingerprint window. It proved the observer
can parse and publish a tuple, but the tuple reported `invalidBatches=40` and
is therefore inadmissible under 439's reader contract. No FPS measurement was
taken.

The live window itself had `frames=120`, `batches=21,480`,
`bytes=14,158,560`, hash `2109626789`, and `rejectedBatches=0`; contemporaneous
runtime output had 120/120 submitted/reaped Presents with no async error. This
does not override the nonzero invalid field.

## Cause and repair

The parser originally used `null` for both a malformed batch and a well-formed
batch whose final command was not Present. The latter is expected during the
guest flow and must not be called malformed. `null` now means only a failed
length/opcode bound check; valid parsed batches carry `terminal=false/true`,
and only success (`0x6001`) terminal batches contribute to the 120-frame
window. The original host dispatch is still invoked exactly once and returns
its unchanged result.

Static audit verifies optional chaining compatibility with the existing page,
synchronous main-loop state (no observer race), exact host success semantics,
and no remaining P0. A new fresh accepted diagnostic run is required; the
earlier nonzero-invalid tuple is retained but cannot establish stability.
