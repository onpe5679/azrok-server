# 326 Gate 6 queue reconciliation after continuation

## Status

**VERIFIED documentation reconciliation; no new performance sample.** The
continuation snapshot requested a fresh parity A-B-A after an inconclusive
drifted run. `docs/research/INDEX.md`, which is authoritative, contains the
later completed remeasurement in 295. This record prevents a duplicate sample
and reconciles the stale queue ordering.

## Parity popcnt

Document 295 already ran the required visible, direct-Present A-B-A-B with no
build/cache CPU competition. Its baseline drift correctly extended the run;
the two matched effects were -4.13% and -6.29% (median -5.21%), both outside
the +/-3% noise band. P/NP helper elimination is correctness-verified, but
the candidate is **VERIFIED performance-rejected**. Do not run it again or
mix it into another candidate.

## Z/NZ queue item

Parity's prerequisite is therefore already satisfied. The follow-on Z/NZ card
also completed: 296--300 established its contract, cache-off/replay integrity
and exact real-helper `fn16/fn17=0/0` gate; 301's visible A-B-A-B did not show
a valid uplift (+0.862%/-6.807%, condition mean -2.893%). Z/NZ is opt-in and
**not adopted**. It is not an open next card.

## Dual-entry R2 and MOVSD

R2 itself was already performance-rejected in 293; its optional 308
postmortem census remains blocked only because the canonical source raw is
missing, as independently reconfirmed in 325. It cannot authorize a rerun or
revive R2. The only code card still structurally open is private runtime-zero
MOVSD, but its MRGF3 browser gate is blocked by the browser URL policy recorded
in 324. No browser-policy workaround, cache/replay publication, or FPS sample
is permitted.

## Consequence

The accepted ABI2 stem/cache remains live. The next meaningful action is a
permitted fresh-browser MRGF3 entry-388 run; it must complete the existing
matrix before normal MRG, SMC, cache/replay, or any performance measurement.
