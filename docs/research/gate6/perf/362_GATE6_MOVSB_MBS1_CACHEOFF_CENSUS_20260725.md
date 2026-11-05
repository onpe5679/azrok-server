# 362 -- MOVSB MBS1 cache-OFF generated-fallback census (2026-07-25)

## VERIFIED runtime gates

The sole existing CDP tab ran the MBS4 private stem with
`movsbSegmentedRepCensus=1` and `jitCacheUrl=off`; it contained no record,
replay, Present-capture, or other census URL mode.  Direct runtime calls
proved ABI=2, word count=559 and snapshot bytes=4,472.  The visible document
and CSS canvas reached 1024x768 after normal input pulses, direct Presents
advanced from 1,374 to 1,948 across the measurement period, and the last two
async ring reports both had `errors=0`.

MBS2 and MBS3 are excluded by 361.  MBS4's reader successfully performed two
mutex snapshots with all page-side partition and byte-conservation gates.
This is a coverage diagnostic, not an FPS, cache, record, replay, or
optimization result.

## VERIFIED S0 -> S1, 30 seconds of post-input direct rendering

| Counter | Delta |
|---|---:|
| generated `fn_8` total | 2,015,456 |
| other opcode | 1,760,999 |
| invalid opcode tag | 0 |
| MOVSB total | 254,457 |
| invalid MOVSB metadata | 0 |

The exact shape split `[REP, EA16, sticky-segment]` was:

| Shape | Delta |
|---|---:|
| 001 (EA32 REP, no sticky segment) | 5,485 |
| 101 (EA32 REP, sticky segment) | 248,972 |
| all remaining six shapes | 0 |

Thus `1,760,999 + 5,485 + 248,972 = 2,015,456`; the fn8 and MOVSB shape
partitions hold exactly.

All 248,972 sticky EA32+REP calls landed in one valid context: source segment
3 (DS), source-only sticky cause, live ES/source both zero, DF=0, warm=0.
Its ECX call partition held exactly: 248,935 calls in bins 0..255 plus 37
overflow calls.  The independent requested-byte accumulator was 21,235;
the page recomputed the same value from weighted bins plus 16,080 overflow
bytes.  `invalidMetadata=0` is required negative evidence, not merely a
favorable count.

## Consequence

The data quantifies MOVSB fallback coverage and supports a later separate
candidate design/audit.  It does **not** authorize reuse of MOVSD routing,
does not establish partial-fault/SMC/EIP correctness for a new MOVSB route,
and does not authorize cache/replay/FPS.  Per queue order, the next
independent census card is FISTP qword.
