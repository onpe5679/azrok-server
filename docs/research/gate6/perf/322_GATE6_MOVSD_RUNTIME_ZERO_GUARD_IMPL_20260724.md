# 322 Runtime-zero MOVSD guard implementation

Status: **VERIFIED implementation/build/static ABI; differential/browser NOT VERIFIED**

The private Wasm-only macro overrides the EA32 REP hasSetSeg MOVSD route.
Cold runCount keeps the original emulate/traced-stub decision. Warm execution
loads CPU-local source and ES bases, takes exact emulate when their OR is
nonzero, and otherwise uses existing flat movsr. It uses a structured Wasm
If/Else boundary and explicitly frees both scratch locals after the join.

This is not published or replayable. The corrected private MRG1 build completed
at 2026-07-24 15:21 KST after static audit caught and repaired the missing
`OP_FLAG2_TRACED_STUB` assignment in the cold path before publication. The
artifact compiles as Wasm, retains the accepted legacy ABI export count (54),
and is deliberately distinct from the accepted asset: JS
`80195DB565C5000935130E534F4724EC1570DFE9F6D6FAB85C02665739DB0572`, Wasm
`DA8CCAF88E062F37A0C409E5C4BA52F90398372A12105F78627B4D194A8C12CB`.

Mandatory same-block segment-mutation, partial-fault and SMC differential
tests remain required before a private counter build or any cache-OFF browser
integrity run. No cache, replay, FPS, or deployment claim follows from this
build result.
