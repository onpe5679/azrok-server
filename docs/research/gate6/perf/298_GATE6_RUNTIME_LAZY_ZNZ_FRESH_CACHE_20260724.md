# 298 — runtime-lazy Z/NZ fresh record and grouped-cache gate (2026-07-24)

**VERIFIED fresh candidate record, grouped-cache generation, manifest contract,
and static module validation; browser replay and performance NOT VERIFIED.**

## Fresh input and isolated output

The candidate cache-OFF PatHouse session wrote a new raw record at
`tools/boxedwine_local/profiles/azrok-jit-record-raw.zip`: 46,217,305 bytes,
SHA-256 `0734050303F25C0BA7B9927B46A1475A428CD4E219370D58AA324F635DB67C31`.
It was converted without overwriting the accepted ABI2 or rejected parity
artifacts into:

`azrok-jit-grouped-commonfast64-depthlocal-inlinefetch-runtimeznz68.zip`

The output is 5,593,477 bytes, SHA-256
`75A1634DDFCD614281465A228C15C09E572655EADF13281691898940B3FE56B5`.

## Direct pipeline and static facts

The offline pipeline completed `34,799/34,799` modules into 111 groups (4,766
components), rewriting 9,405 direct-tail sites and 249,549 common-dispatch
tails.  Its Wasm aggregate changed from 213,945,875 to 58,096,053 bytes and
the ZIP from 46,217,305 to 5,593,477 bytes.  Error output was empty.

The grouped manifest declares the exact fail-closed runtime-lazy Z/NZ contract:
`cpu-runtime-lazy-znz-v1`, ABI 1, flags/result/lazy-type/lazy-type-prev
offsets `96/108/328/329`, ZF mask 64, NONE 0, CFOF 50, result range 1--49,
and fallback `helpers.cond-z-nz`.  These values came from direct candidate
Wasm exports, not from the raw record (which does not contain these layout
fields).

All 111 archive group modules pass direct `WebAssembly.validate`; the separate
runtime-lazy loader verifier also passes all 17 negative cases and eight page
source-gate fragments.

## Remaining gate

This cache has not yet been registered by a live browser replay.  That replay
must prove the loader's live contract dataset
`1:96:108:328:329:64`, complete visible PatHouse rendering, and fresh
`fn_16/fn_17=0/0` evidence before any 30-second candidate A-B-A performance
sample.
