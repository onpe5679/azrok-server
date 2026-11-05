# 290. Gate 6 PatHouse replay pair gate

## VERIFIED static/offline repair; browser replay still pending

The deployed `assets_d3d9web/boxedwine-shell.js` is byte-identical to its
source counterpart (SHA-256
`0089D3030AE46E72CD3A6869910AC1592DB74EB712456A28B48A7D0179C27436`) and
contains the complete register-thread pair fail-closed validator. It requires
the v3 MT two-token contract, pair ABI 1, GP-tail ABI 1, all wrapper and typed
exports, and the pair registration API.

However, the actual PatHouse page bypasses that shell path for replay.
`index_d3d9web_pathouse.html` `prepareAzrokJitReplay()` has its own ZIP parser,
stager, and registration loop. It explicitly rejects
`runtimePublication.tokenWords !== 1` and registers every entry only through
the legacy single-slot `_wasm_jit_mt_register_group_entry(...)` API. It neither
checks the GP-tail getter nor reads a typed export name. A v3 dual-entry cache
is therefore correctly blocked today; merely relaxing the one-token condition
would permit stale or half-pair publication.

## Required repair: fail-closed

For v3/typed metadata, the page must require the same pair ABI 1 and GP ABI 1
capabilities as the shell, validate the exact two-token/8-GP contract and
every wrapper/typed entry, and call only
`_wasm_jit_mt_register_group_entry_pair(...)`. Any allocation, export lookup,
registration, count, or manifest mismatch must abort before publication. The
legacy single-slot API remains available only for v2 tokenWords=1 caches; v3
has no fallback. A distinct `AZROK_JIT_REPLAY_REGISTERED_PAIR` marker and
dataset state are required for direct replay proof.

## Repair and verifier: VERIFIED

`validateAzrokJitReplayContract()` now keeps v2 on the exact one-token legacy
path, while any v3 or typed declaration requires the exact pair/8-GP contract,
both runtime getters equal to 1, the pair registration API, and a typed name
for every entry. The v3 publication loop allocates and registers wrapper and
typed names only through `_wasm_jit_mt_register_group_entry_pair(...)`; v3 has
no legacy fallback. The page emits `AZROK_JIT_REPLAY_REGISTERED_PAIR` and
`data-jit-replay-pair=registered` only for that branch.

`verify-pathouse-dual-entry-replay-gate.mjs` passes five direct cases: v2
accept, complete v3 pair accept, missing GP rejection, missing pair API
rejection, and v3 one-slot metadata rejection. The existing shell verifier
also passes all nine cases. These are page-contract proofs only; no fresh
record or browser replay has yet been claimed.

## Next evidence

Create one fresh cache-off dual-entry record at
`profiles/azrok-jit-record-raw.zip`, transform only that input into
`profiles/azrok-jit-grouped-threadedtailabi2.zip`, and replay it with the same
`boxedwine.threadedtailabi2` runtime. Do not reuse the accepted v2 parity67
cache. Browser replay must prove the pair marker and exact group/entry/patch
counts before any PatHouse A-B-A.
