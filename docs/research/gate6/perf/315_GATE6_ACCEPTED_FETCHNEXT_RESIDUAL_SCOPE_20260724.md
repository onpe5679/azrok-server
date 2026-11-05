# 315 - Accepted fn6-inline residual fetch-next scope

## Question

313 found `fetch_next` to be the highest-frequency helper family in a private
cache-OFF diagnostic. This record tests whether that observation opens a safe
optimization on the accepted grouped replay path.

## Accepted cache audit - VERIFIED static

- `helpers.fn_6` is `wasmHelper_fetchNextOp()`: it updates `cpu->nextOp` via
  canonical `cpu->getNextOp()` unless the thread is terminating.
- Binaryen inspection of all 134 groups in
  `azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2.zip` finds exactly
  134 `call $fimport$6` occurrences: one common-dispatcher cold fallback per
  group. None of the 41,625 block bodies retains a separate fn6 call.
- The pipeline redirects 245,517 exact `local.get cpu; call fn_6; return`
  tails to the common dispatcher with `needsFetch=1`. Its 10/10/12 opCache hit
  traversal runs inside Wasm. A further 54,960 persistence fast-success tails
  enter with `needsFetch=0`, and 10,813 hot next1/next2 direct tails bypass
  the dispatcher entirely.
- The only fn6 residual paths are mutually exclusive: CPU thread null, opCache
  root null, L1 null, L2 null, or leaf `DecodedOp*` null. Terminating and null
  process return `nextOp=null` without helper invocation.

## Decision - NOT A CANDIDATE

The five residual branches are canonical decoder/cache slow paths. Replacing
them with new Wasm logic would duplicate `getNextOp()` cache/decode semantics
without measured attribution to any one branch. The 91,999,804 cache-OFF
diagnostic entries in 313 must not be reinterpreted as calls on accepted replay.
Therefore no code change or A-B-A opens.

## Follow-up measurement - NOT VERIFIED

Only a private, fail-closed reason-split census may reopen this area. It must
bucket the five residual reasons plus terminate/process-null consistently with
the existing fetch-next total, prove an exact bucket-sum invariant across a
visible cache-OFF PatHouse S0/S1 interval, and preserve no-cache/no-record/no-
FPS and renderer-integrity evidence. Until then this is static scope closure,
not a performance result.
