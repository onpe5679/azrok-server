# 406 - Gate 6 runtime lazy logical-composite b32 semantic boundary (2026-07-25)

## Inputs

405 directly observed 61,281 b32 logical potential helper entries in two cache-OFF visible intervals. This is enough coverage to assess a narrow b32 candidate, but not enough to skip semantic proof.

## Static equivalence result (VERIFIED)

Only these current runtime lazy-flag types are eligible: `FLAGS_OR32` (6), `FLAGS_AND32` (15), `FLAGS_XOR32` (21), and `FLAGS_TEST32` (42). They all have `CF=0`, `OF=0`, `ZF=(result==0)`, and `SF=(result&0x80000000)!=0`. Thus, for exactly those current types only:

| Condition | Equivalent result-only expression |
| --- | --- |
| BE | `ZF` |
| NBE | `!ZF` |
| L | `SF` |
| NL | `!SF` |
| LE | `ZF || SF` |
| NLE | `!ZF && !SF` |

The implementation point, if opened, is only the existing runtime-lazy fallback after compile-known condition propagation fails. It must explicitly compare all four enum values; width arithmetic, producer families, or a broad "logical" category are forbidden.

## Explicit exclusions (VERIFIED)

`FLAGS_CFOF` remains helper-only even when its predecessor is logical b32: the carrier preserves/reads CF and OF from architectural flags while only part of the state follows the predecessor, so the result-only expressions are not equivalent. `FLAGS_NONE`, NULL/out-of-range values, all arithmetic/ADC/SBB/SUB/CMP/INC/DEC/NEG/shift/DSH families, b8, b16, and unknown types also remain helper-only.

## Required proof before implementation

A private indirect-JIT-boundary fixture must exercise all 4 b32 producers × results `{0,1,0x80000000}` × six Jcc conditions (72 rows), plus SETcc and CMOV surfaces. It must prove both candidate hits and exact fallback hits for CFOF (including logical predecessor), b8/b16 logical, NONE, arithmetic, and shift rows, preserving lazy tuple, architectural flags, and all eight GP registers. The existing Z/NZ fixture is only a structural reference: its CFOF predecessor-follow rule is not reusable here.

## Decision

**OPEN, fixture first.** A private b32-only implementation may not be written until the fixture validates this boundary. No cache/replay/FPS card opens.
