# 311 Runtime-lazy composite-condition boundary

## Status

**VERIFIED static; no candidate selected.**

The full-condition census (310) shows steady PatHouse execution in BE/NBE and
the signed L/NL/LE/NLE families. This does not provide a safe pure-result
runtime candidate.

`JitWasmCodeGen::getCondition` already emits pure Wasm for these conditions
only when `currentLazyFlags` is a compile-known logic or SUB producer. The
logic path uses the known result; the SUB path uses known `dst/src` operands
and signed/unsigned comparisons. When the compile-time cache is `FLAGS_NULL`,
the runtime helper must call `CPU::getCF()` and/or `CPU::getOF()` in addition
to ZF/SF.

Direct CPU implementation shows `getCF()`/`getOF()` dispatch through the
runtime lazy-flag type. CF needs producer-specific `result`, `dst`, `src`, and
for shift/rotate cases `oldCF`; OF has separate producer formulas and CFOF
semantics. Thus a result-only predicate would silently be incorrect, while
copying the full 49-type CF/OF evaluator is a new broad semantic
reimplementation, not a local inline candidate.

The previously measured B/NB zero-CF subset is the only currently proved
narrow CF contract and had exact zero dynamic coverage (307). It cannot be
used to justify BE/NBE. No safe narrow OF contract is presently proved for the
signed family. Therefore no build, cache or FPS card is opened from 310's
coverage numbers; future work must first prove a smaller operand/flag contract
with differential fixtures.
