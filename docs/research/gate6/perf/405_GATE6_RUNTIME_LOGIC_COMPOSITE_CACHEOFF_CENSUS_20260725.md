# 405 - Gate 6 runtime lazy logical-composite cache-OFF census (2026-07-25)

## Contract

This is the private diagnostic designed in 402 and built in 404. It is cache-OFF, uses the one visible CDP page only, and does not create a cache, replay, or FPS claim.

The page required private ABI 1 and 5,184 bytes / 648 `U64`, then reached visible/focused PatHouse with CSS 1024x768, advancing direct Presents, and zero async-ring errors. A direct CDP pointer activated both the page run button and the canvas. The two 30-second intervals below are counter deltas, not FPS measurements.

## Reader P1 and repair (VERIFIED)

The first live reader call fail-closed with `runtime logic composite census partition mismatch`. Raw CDP copies directly established ABI 1 and 5,184 bytes, then isolated the defect to page-side array interpretation: C++ stores the snapshot as `helperByType[6][53]` (words 0..317), then `cfofPrevByType[6][53]` (318..635), then `eligibleHelperByWidth[6][2]` (636..647); the reader had incorrectly treated it as six interleaved 108-word rows.

Only the page reader offsets were repaired. The JS source was module-parsed, its served HTML was directly checked for the corrected array-major expression, and the existing sole tab was reloaded and pointer-started again. No Wasm source, artifact, accepted asset, cache, or replay changed for this repair.

## Cache-OFF live coverage (VERIFIED)

Condition row order is BE, NBE, L, NL, LE, NLE. Both intervals passed the reader's invalid-type, CFOF-predecessor, and width recomputation gates: invalid=0, current CFOF=0 with predecessor sum=0, and b8 potential=0 in every row.

| Interval | Helper total | b32 logical potential | Potential share |
| --- | ---: | ---: | ---: |
| S0 to S1 (30 s) | 579,531 | 3,020 | 0.521% |
| S1 to S2 (30 s) | 891,376 | 58,261 | 6.536% |
| Combined | 1,470,907 | 61,281 | 4.166% |

The per-condition `(helper delta, b32 potential delta)` rows were:

| Interval | BE | NBE | L | NL | LE | NLE |
| --- | --- | --- | --- | --- | --- |
| S0 to S1 | 0, 0 | 8,937, 0 | 132,950, 0 | 67,132, 0 | 370,503, 3,011 | 9, 9 |
| S1 to S2 | 19,048, 16,168 | 147,258, 0 | 310,082, 0 | 114,039, 32,336 | 292,405, 5,723 | 8,544, 4,034 |

Direct Present advanced 4,409->7,366 and 7,929->8,824 while all display/focus/ring gates held. Those counts establish liveness only and are not converted to FPS.

## Decision

**VERIFIED coverage.** The narrow runtime TEST/AND/OR/XOR b32 logical class has material, variable workload coverage; b8 has zero observed admission in this scene. This authorizes a new, private, b32-only semantic-equivalence audit and fixture design. CFOF, NONE, arithmetic, shifts, b16, unknown types, and all b8 arms remain helper-only. No inline implementation or performance claim is authorized by this census alone.
