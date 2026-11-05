# 379 -- MOVSD MRG1 private replay cache ready (2026-07-25)

Status: **VERIFIED transform/filesystem/static gate; browser replay and FPS not yet measured**

## Private transform

The immutable MRG1 raw from 352/378 was transformed without rebuilding or
rerecording candidate bytes. The pipeline used only the private MRG1 input and
the mandatory legacy-safe route:

```text
--no-direct-calls
--mrg1-runtime-stem boxedwine.upstreamjit64fn6inlineabi2movsdruntimezero1
--mrg1-raw-manifest-sha256 3b0ee71a9101d2d74a6d044f0112b58f69cc9ab54ef12b1076dd9c222b59f56c
```

It completed with 35,804/35,804 optimized modules, 114 merged groups, zero
rewritten tail sites, 32,358 relocation entries, and a 5,312,521-byte output:

```text
profiles/azrok-jit-grouped-movsdruntimezero1.zip
archive SHA-256: 2ff1cbffeec905d81b9c3d3bbf8cc78080a1c747896cef815d1ac1a42da9a98a
uncompressed grouped-manifest SHA-256: 166fcdef0a01f2a8172317e57a4054ad4db09eff4fefb92444dc5d9490cf1632
```

The grouped manifest independently contains
`azrok-mrg1-movsd-runtime-zero-v1`, the exact MRG1 stem, the exact immutable
raw-manifest SHA and required guard ABI 1. The accepted replay/cache and the
already-rejected MRG2 private artifact were not overwritten.

**VERIFIED served-byte preflight:** a read-only in-memory HTTP GET from 8765
returned 5,312,521 bytes with the exact archive SHA above. No compiler or
cache-generation process remained active. This proves serving identity only;
it is not browser registration or render evidence.

## Loader closure

The explicit MRG1 table record now has both final pins. Static identity
regression passes 19 cases, covering exact MRG1 pre-runtime/runtime acceptance,
wrong archive/grouped/raw rejection, MRG1/MRG2 crossed identity rejection, and
the retained exact MRG2 rows. Thus a cache can register only at the exact MRG1
stem/cache/identity/guard/archive/manifest intersection.

## Browser boundary

After cache generation ended, direct replay preflight required exactly one CDP
page and found zero. No target was navigated, no replay resource was fetched,
and no Present/FPS sample exists. This is an environment condition, not a
candidate result. On the next direct one-page CDP confirmation, navigate only
that target to MRG1 replay, prove registered groups/blocks plus visible
PatHouse, then perform fresh-browser accepted-vs-MRG1 A-B-A(B). Per 374, do
not use same-tab transitions for performance legs.
