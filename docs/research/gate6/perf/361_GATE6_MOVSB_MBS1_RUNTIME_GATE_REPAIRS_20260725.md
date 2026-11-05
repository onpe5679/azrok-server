# 361 -- MOVSB MBS1 runtime-gate repairs (2026-07-25)

## VERIFIED fail-closed repairs before census evidence

Two private MBS iterations were rejected before any accepted snapshot.

1. MBS2 had the new 559-word layout but its compiled MBS ABI export still
   returned 1.  Direct CDP invocation proved `abi=1`, `words=559`,
   `bytes=4472`; the V2 page expected ABI 2, so it could not be a valid
   reader.  No guest coverage snapshot was accepted.
2. MBS3 corrected the C++ export.  Direct CDP proved `abi=2`, 559 words and
   4,472 bytes, and reached visible 1024x768 FFP/Present with async-ring
   errors=0.  Its first refresh then threw `TypeError: bins.reduce is not a
   function`: the page reduced the bin array before using it for the weighted
   byte equation.  The refresh rejected before publishing a dataset, so that
   attempted S0 is invalid.

MBS4 retains the verified MBS3 Wasm (`0263925...21A299`) but uses new private
served names and a corrected reader: `binCalls` is kept separate from the
weighted requested-byte reconstruction.  The loader gate now requires both
the `contexts = binCalls + overflowCalls` and independent byte conservation
expressions.  MBS4 JS/Wasm return HTTP 200 and accepted/MRG assets remain
unchanged.

## Status

The MBS cache-OFF census remains **NOT VERIFIED** pending MBS4 runtime ABI
and successful named snapshot reads.  Neither rejected private iteration is
performance, replay, cache, or optimization evidence.
