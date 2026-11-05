# 378 -- MOVSD MRG1 replay-identity reopen (2026-07-25)

Status: **VERIFIED static/dynamic preflight; private cache transform authorized, replay/FPS not yet measured**

## Candidate separation

The completed 359 performance rejection is **MRG2 only**: private stem
`boxedwine.upstreamjit64fn6inlineabi2movsdruntimezero2`, 95-group no-direct
replay, and its own 30-second A-B-A-B. It must not be reused or retested for
this card.

The reopened candidate is MRG1, the original runtime-zero MOVSD build proven
cache-OFF render-integral in 346. Its private legacy-ABI stem is
`boxedwine.upstreamjit64fn6inlineabi2movsdruntimezero1`; the staged JS/Wasm
still match 346 exactly (`80195D...0572` / `BF4710...5D39`). Its immutable
cache-OFF record is also intact:

```text
azrok-jit-record-movsdruntimezero1-20260725-092900.zip
35,804 v5 entries; archive SHA-256 7171DAD...CAD885B
raw manifest SHA-256 3b0ee71a9101d2d74a6d044f0112b58f69cc9ab54ef12b1076dd9c222b59f56c
```

No rebuild or duplicate record is justified while these exact candidate bytes
and the immutable raw agree; the record stage already exists and the next
unclosed operation is its private grouped-cache transform.

## Reopened fail-closed gate

352 correctly stopped before MRG1 publication because the page only recognized
the later MRG2 pin. The loader now holds explicit MRG1 and MRG2 records.
MRG1's future `/profiles/azrok-jit-grouped-movsdruntimezero1.zip` record starts
with null archive/grouped-manifest pins, which rejects before registration.
The transform may run only with `--no-direct-calls`, exact MRG1 stem and exact
raw-manifest SHA. Its resulting whole-archive and grouped-manifest SHA values
must be written into this MRG1 record before replay can be accepted.

`verify-mrg-replay-identity-gate.mjs` now passes 15 cases: ordinary accepted
legacy remains unmodified; MRG1 unbound state rejects; MRG1/MRG2 crossed
stem/cache/raw combinations reject; and the existing exact MRG2 rows remain
accepted. This is a static gate only.

## Dynamic status

Services 8765/9200/9201/9300 and CDP 9222 were directly live during preflight.
The page was not in a sampling-ready scene (zero CSS canvas and zero Presents)
when inspected, so no navigation, record, replay, or FPS sample was taken.
Fresh-process legs remain mandatory under 374's same-tab retention result.

## Next gate

Generate only the new MRG1 private no-direct cache from the immutable raw,
calculate its two final pins, update the MRG1 record, rerun static identity
cases, then require cache-off/replay render integrity before any visible
30-second accepted-vs-MRG1 A-B-A(B). Accepted assets remain untouched.
