# 316 - Accepted fetch-next pre-sample reason census

## Scope - REJECTED at replay ABI gate

315 closes direct optimization: accepted replay retains only a cold fn6
fallback. This private diagnostic instead classifies the read-only state seen
immediately before `wasmHelper_fetchNextOp()` calls `getNextOp()`.

The 72-byte snapshot is one mutex-coherent total plus eight mutually exclusive
pre-sample buckets: thread-null sentinel, terminating, process-null, opCache
root null, L1 null, L2 null, leaf null, and unexpected cache hit. The total is
the same MT-helper-census `FetchNext` storage, incremented under the same
diagnostic lock as exactly one bucket; every exported snapshot must therefore
have `total == sum(buckets)`. Thread-null records then preserves the existing
dereference/crash behavior; it is not converted to a normal exit.

The classifier mirrors the exact 10/10/12 `DecodedOpCache` layout but is only a
pre-sample: MT cache mutation can change the later `getNextOp()` result. It is
not called a definitive decoder or replay-fallback cause. `unexpected hit` is
an explicit sentinel for a direct helper caller or race and must be reported,
not silently merged with misses.

## Required gate

The private runtime exposes 56 exports (accepted 54 plus reason 2). It retains
the MT helper-census storage internally, but the reason snapshot reads its
`FetchNext` counter under the same lock rather than exporting duplicate helper
reader glue; this avoids the Windows command-line limit that rejected the
58-export link. It requires `fetchNextReasonCensus=1` and replays only
`azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2.zip` with no
`jit-record`. URL/runtime ABI, exports, snapshot size, manifest inline-fetch
ABI v2, coherent partition, complete visible PatHouse and ring integrity must
all pass before interpreting S0/S1 deltas. This is diagnostic-only: no FPS or
Present capture.

## Gate result - VERIFIED browser fail-closed

The private 56-export build itself compiled and its URL/runtime reason ABI
reached version 1. When loading the accepted grouped cache, the page rejected
it before game startup with
`generic indirect cache ABI mismatch next=740/740 depth=1660/1660
bailout=132/132 pfn=12/12 map=12968624/12964392 cap=262144/262144`.

The new diagnostic globals moved `indirect_reloc_map_base` by 4,232 bytes.
The accepted manifest correctly refuses that different runtime layout. Rebuilding
the cache for this diagnostic would no longer measure the accepted replay
artifact, so it cannot answer 315's question. No scene, counter snapshot,
candidate, or FPS result is claimed. The private files remain non-default audit
artifacts only.
