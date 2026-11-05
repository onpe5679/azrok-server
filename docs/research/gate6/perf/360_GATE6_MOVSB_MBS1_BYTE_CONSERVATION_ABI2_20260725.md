# 360 -- MOVSB MBS1 byte-conservation census ABI repair (2026-07-25)

## VERIFIED P1 found before guest start

Read-only static review of the staged MBS1 diagnostic found that its
558-word/4,464-byte snapshot had ECX bins, overflow-call count and overflow
bytes, but no independently accumulated requested-byte total.  It could
derive an estimate from those fields but could not prove the required
`requested bytes = ECX-weighted total` conservation equation against an
independent recorder value.  Per 330 this is a fail-closed P1, so the already
prepared cache-OFF MBS1 page was **not started**, no guest input was sent, and
no coverage value was accepted.

## VERIFIED private ABI v2 repair

MBS1 now accumulates `requestedBytesTotal` under the same mutex, only after a
valid EA32+REP+sticky (shape 5) context is admitted.  The browser independently
reconstructs that quantity as `sum(ECX bin index * bin count) + overflowBytes`
and rejects if it differs.  The new private snapshot is 559 U64 / 4,472 bytes;
runtime ABI is 2.  Existing equations remain fail-closed:

```
fn8 = otherOpcode + invalidTag + sum(shape[0..7])
shape5 = invalidMetadata + sum(valid contexts)
sum(valid contexts) = sum(ECX bins) + overflowCalls
invalidMetadata = 0
requestedBytesTotal = weighted ECX bins + overflowBytes
```

The page requires the exact V2 layout and a new private stem
`boxedwine.upstreamjit64fn6inlineabi2movsbsegcensus2`; it cannot accept the
old 558-word `...movsbsegcensus1` artifact.  This preserves fail-closed
identity and leaves accepted ABI2, the current accepted cache, and private
MRG assets untouched.

## VERIFIED rebuild and staged-byte gates

The isolated Build/MBS1 target was rebuilt as one `nice -n 19`,
`LOW_PRIORITY_JOBS=1` job.  It completed with existing warnings only and no
`error:` diagnostics.  The output Wasm validates, has 58 exports (the
accepted legacy 54 plus the four MBS APIs), and is 3,049,487 bytes, SHA-256
`CB0BD207676653BFB31A2FA163EAECAF5B0696344647FC81E19F84604D6FFC73`.
The JS glue is 327,646 bytes, SHA-256
`3E509825B4AF27E7E1C7A1434A6B2B894BDFB3F6DAB5A48D9E16B91960FE263F`.

Only new V2 served names were created; both returned HTTP 200 and match the
rebuilt bytes.  The dedicated loader gate passes with
`words=559`, `bytes=4472`, `shapeWords=8`, `contextWords=288`, and the
requested-byte-total requirement present.

## Next gate

MBS1 is still a private cache-OFF **coverage-only** card.  Navigate the sole
existing tab to the V2 URL, require runtime ABI/layout before guest start,
then require a visible 1024x768 PatHouse with zero async-ring errors before
named mutex snapshots.  No cache/record/replay or FPS result is authorized.
