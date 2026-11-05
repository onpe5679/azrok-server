# 319 `Movsd` segmented-REP boundary and MOC3 plan

Status: **VERIFIED static/dynamic design; MOC3 diagnostic required before candidate**

## Direct facts

318's exact cache-OFF visible PatHouse interval puts 2,657,088 of 2,666,306
observed string-`Movsd` fallbacks (99.654%) in EA32 REP DF0 bucket 5:
`hasSetSeg[ES] || hasSetSeg[op->base]`.  This is not the flat traced-stub
cold path.  `dynamic_movsd_op` checks the segment-address route before it can
call `movsr`; only the latter has the `runCount==0` / `OP_FLAG2_TRACED_STUB`
policy.  **VERIFIED:** `jit/jitStrings.h:66-72,282-299`.

For A5 string MOVSD, the source segment is decoded `op->base` (DS by default,
replaced by a segment prefix) and the destination is always ES.  **VERIFIED:**
`decoder.cpp:3742-3754,3985-3999,6438-6447`.  `hasSetSeg` does not establish a
nonzero runtime base: FS/GS begin set and the WineVDM path sets all six flags;
the interpreter still reads `cpu->seg[ES].address` and `cpu->seg[base].address`
per invocation.  **VERIFIED:** `kprocess.cpp:95-96,850-855` and
`normal/normal_strings.cpp:133-143`.

## Candidate boundary

The direct `wasmHelper_movsd32r` route is rejected: it cannot replace the
mixed-block emulate path's EIP/NEXT, dirty-GP, decoded-op, partial-fault and
SMC/bailout handling.  **VERIFIED:** `jitWasmCodeGen.cpp:5438-5442,14319-14391`.

Static inspection does show a possible future narrow implementation: a new
scalar generated-Wasm REP loop only for hot `EA32 && REP && hasSetSeg` MOVSD,
using runtime `seg[base].address` / `seg[ES].address`, the existing per-access
read/write slow paths and bailout checks, DF branches, partial-progress sync,
and leaving all `runCount==0` policy in emulate.  `getTmpSegAddress` is the
required runtime address accessor; `getReadOnlySegAddress` is unsafe here due
to its `seg & 3` local alias.  **VERIFIED static:**
`jitStrings.h:21-124,282-299`; `jitWasmCodeGen.cpp:11222-11239,11259-11266,
11593-11625,11793-12050`.

It is not a candidate yet: actual source segment, route cause, runtime base
state and request-size distribution are unmeasured.  No claim about CPU time
or FPS follows from call/request counts.

## Required MOC3 diagnostic

MOC3 is a distinct private cache-OFF-only diagnostic, never record/replay/FPS.
At B5 codegen it may place only `{sourceSeg (3 bits), hasSetES,
hasSetSource}` in helper scratch.  At the real helper entry it must count:

1. source segment (six ways);
2. route cause (ES-only, source-only, both, impossible);
3. runtime base-zero state `{ES.address==0, source.address==0}` (four ways);
4. pre-call ECX requested-dword exact bins `0..255` plus `>=256` overflow.

Every category must sum exactly to B5 calls, with invalid segment/tag a
separate fail-closed counter.  `runCount` is deliberately excluded from the
causal census: static control flow proves B5 never reaches `movsr`'s cold
check.  Only if the zero-base categories prove an adequate guarded subset may
a separate static audit consider reusing flat `movsr`; a nonzero base or an
overflow bin forbids claiming that narrow route complete.  The fully segmented
generated loop remains a later semantic implementation card regardless.

No source or runtime behavior changed in this analysis.
