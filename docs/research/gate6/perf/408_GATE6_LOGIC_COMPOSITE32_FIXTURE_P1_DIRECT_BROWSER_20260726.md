# 408 -- Gate 6 logical-composite32 fixture P1 direct-browser repair (2026-07-26)

## Status

**VERIFIED build/direct browser P1 repaired. Fixture gate PASSED; candidate remains private-only.**

The isolated `TestMultiThreadedJitRuntimeLogicComposite32Fixture1` build
completed with only pre-existing warnings. Its sole visible CDP page directly
ran test entry 27.

## P1 failure and repair

The initial fixture failed because it converted condition opcode to a counter
index as `jcc - 0x76`. That is valid only for BE/NBE and sent L/NL/LE/NLE
outside the six-counter array. The fixture now maps
`{BE,NBE,L,NL,LE,NLE}` explicitly to `{0..5}`.

The narrowed rerun established a second runtime representation fact:
decoded TEST's cross-block lazy producer is canonicalized to `FLAGS_AND32`
(15), with `result = left & right`, rather than `FLAGS_TEST32` (42). The
candidate already admits AND32, so this changes only the test oracle.

## Direct final evidence

The same sole browser page, after the incremental `rebuild=3`, reported:

```text
Running 1 Test tests with 1 threads starting at 27
[WASM JIT] first JIT block executed, tableIdx: 8190
Test runtime logical composite32 across indirect JIT block boundary ... OK
0 tests FAILED in 0s
```

The fixture covers 4 producer opcode forms x 3 result boundaries x 6
conditions, each consumed by SETcc, CMOVcc and Jcc across an indirect JIT
block boundary. The witness requires candidate +3/fallback +0 per positive
row; b8, b16, NONE, SUB32, SHL32 and logical-predecessor CFOF require
candidate +0/fallback +3. It also checks all GP registers, result tuple and
logical CF/OF/ZF/SF outcomes.

## Boundary

This closes only the fixture gate. No cache, replay, accepted asset, or FPS
sample was made. The next gate is a new isolated production candidate with
fixture counters and test-only CPU layout removed, then cache-OFF render
integrity before record/replay/performance work.
