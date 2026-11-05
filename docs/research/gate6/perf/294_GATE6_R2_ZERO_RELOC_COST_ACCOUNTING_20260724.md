# 294 — R2 typed direct-tail rejection: zero-reloc fallback and wrapper accounting

## Status

**VERIFIED static/build/browser: R2 remains performance-rejected.** This is a
postmortem of the rejected R2 result in 293; it does not reopen the candidate
or attribute the observed slowdown to an unmeasured dynamic path.

## Exact scope of the zero-reloc exclusion

The pre-repair v3 cache had 3,472 store-sunk typed tails and seven target-array
operands per tail. Of its 24,304 operands, **5,299 = 757 × 7** targeted a
`relocCount=0` entry. Such a target has no slot-0 `DecodedOp*`; its first pair
array word is instead a publication token. Direct admission for those 757
tails is invalid and R2 correctly leaves their original terminal path live.

R1 temporarily added an eighth `nextOp` operand per tail. Its corresponding
invalid-target count is **6,056 = 757 × 8**. R2 excludes these targets before
marker allocation, yielding exactly:

| artifact | direct tails | direct operands | sunk terminal-store bytes |
| --- | ---: | ---: | ---: |
| R1 (never browser-loaded) | 3,472 | 27,776 | 194,432 |
| R2 (browser-tested) | 2,715 | 21,720 | 152,040 |
| delta: excluded zero-reloc paths | 757 | 6,056 | 42,392 |

The 42,392-byte delta is exact static legacy writeback retained in those
fallback tails (`757 × 56` bytes: eight GP stores). It is **not** a dynamic
execution count or time cost.

## Code-size and wrapper comparison

The R1/R2 manifests retain the same 147 groups and 34,322 paired entries.
Their cold wrapper population is therefore unchanged: every paired entry
still has the same public wrapper plus typed body. R2's combined group Wasm
is 53,776,922 bytes versus R1's 53,898,619 bytes (**-121,697 bytes**); its ZIP
is 5,723,590 versus 5,779,405 (**-55,815 bytes**). Thus zero-reloc exclusion
removes code; it does not add wrappers or increase wrapper count.

Subtracting the 42,392 retained terminal-store bytes from the group delta
leaves 79,305 bytes of removed direct-tail guards/relocation machinery across
the 757 excluded sites. This is static artifact accounting only.

No direct runtime counter distinguishes executions of those 757 helper
fallbacks from the 2,715 typed success tails, and no wrapper-entry counter was
enabled during 293's performance legs. Therefore it is **NOT VERIFIED** that
the zero-reloc helper fallbacks, rather than the broader dual-entry wrapper /
typed-body design, caused the roughly 38--40% R2 regression. The decisive
browser fact remains only the whole-candidate A-B-A in 293:
30.03 / 50.00 / 31.07 FPS.

## Decision

The zero-reloc gate is required correctness work and remains in source. R2
must stay disabled. Any future typed-tail revival needs a separate
low-perturbation per-edge execution counter plus a fresh cache-off render gate
before another performance measurement; it must not be mixed into parity or
runtime-lazy Z/NZ work.
