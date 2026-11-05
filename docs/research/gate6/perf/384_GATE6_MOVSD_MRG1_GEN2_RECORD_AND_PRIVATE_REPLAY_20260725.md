# 384 ??MRG1 generation-2 raw record and pinned private replay

Date: 2026-07-25  
Status: **VERIFIED** ??record/transform/loader/served-byte closure; replay
render and FPS remain unmeasured.

## Fresh record

After 383's cache-off render proof, a separate watcher-fresh one-page Edge
process loaded the rebuilt MRG1 stem with `jit-record=true` and
`jitCacheUrl=off`. Real pointer activation started it. Record mode reached
visible PatHouse rendering with advancing direct Presents, zero async-ring
errors and the live 9201->9200 bridge. `wasm_jit_mt_prepare_export()` then
directly exposed 47,770 cache/meta rows; the actual page-owned save button was
activated by pointer and completed at 52,487 v5 entries / 68,374,174 bytes.

The upload's mutable generic alias was first copied byte-for-byte to
`artifacts/boxedwine/mrg1_record_gen2_20260725/generic_r2_alias_before_upload.zip`
at SHA `6BD19F...4AFF`. The uploaded raw was immediately preserved as:

| immutable artifact | bytes | SHA-256 |
| --- | ---: | --- |
| `profiles/azrok-jit-record-movsdruntimezero1-gen2-20260725-180110.zip` | 68,374,174 | `4C83976248EC3FCB98BC1A6DF8F2CC5966369A436723ECC075A1AA688F361F6F` |

The generic alias was restored and re-hashed to `6BD19F...4AFF`. The new raw
manifest is exactly `1f87698cb12ab126c3793d96450da57915de03a633159344972d919bcd9e6444`;
it declares ABI2-compatible runtime offsets `624/628/1660/132`.

## Private no-direct transform and identity replacement

The first transform omitted the explicit local Binaryen path and failed before
output. The rerun supplied the fixed local `binaryen_js.js`, required
`--no-direct-calls`, MRG1 stem and exact new raw-manifest SHA. Its unpublished
output has 165 groups / 52,487 entries / zero direct-tail patches, archive SHA
`697802af74e4cc6164f607b7b1bf0963d0e3776616556f682bace6bce58f2d75`, and
uncompressed grouped-manifest SHA
`fe39ac9d83d71403091fbe0c54f9b2218e6260094f96d1bcd527c139c246a4fa`.

Before publication, the rejected generation-1 served ZIP was preserved under
`artifacts/boxedwine/mrg1_record_gen2_20260725/` at its historical SHA
`2FF1CB...A98A`. The MRG1 loader table and 19-case identity regression were
then changed atomically to the new raw/archive/grouped pins; the old raw/cache
can no longer pass the loader. Only after that pass was the new ZIP copied to
the private served MRG1 URL. HTTP GET returned 7,554,111 bytes with the exact
new archive SHA.

## Boundary

This is not replay registration/render and not a 30-second performance sample.
The next required gate is a fresh watcher process loading this exact MRG1
replay URL, proving the live guard, identity, registered 165/52,487 corpus,
visible real render and advancing Present before any fresh-process
accepted-vs-MRG1 A-B-A(B) measurement.
