# 230 Gate 2c soft-MMU ABA, epoch cost, and `0x8E05E` lock scope

Date: 2026-07-21

## Scope

This is the static follow-up to documents 227 and 229. It asks whether the
current soft MMU already has a mapping generation which can close an exact
unmap/remap ABA, estimates the least invasive generation alternatives, and
decides whether the production-only `0x1008E05E` trace can instead rely on the
existing memory mutex. No production source was changed.

The inspected source snapshot is
`artifacts/boxedwine/20260719_gate2b_native/Boxedwine`.

## VERIFIED -- there is no existing mapping generation

`MMU` is exactly one packed word:

- wasm32/non-`BOXEDWINE_64`: 1-bit read, 1-bit write, 3-bit type, 1 pad bit,
  6-bit flags, and 20-bit `ramIndex`, totaling 32 bits;
- `BOXEDWINE_64`: the same header fields plus a 52-bit `ramIndex`, totaling
  64 bits.

There is no generation, version, or epoch field in `MMU` or `KMemoryData`.
`KMemoryData::onPageChanged` only refreshes optional read/write pointer caches.
It does not count changes.

The decoded-code `writeCounts` structure is not a mapping generation. It is a
sparse byte-per-code-byte saturation counter used by
`DecodedOpCache::isAddressDynamic`, is absent for most data pages, may be
cleared when a Code page changes type, and does not increment for ordinary
mmap/mprotect/COW/file/lazy-RAM transitions. It cannot be reused by the write
plan.

`RamPage` reference counts also carry no allocation generation. Once a page's
reference count reaches zero, its index can enter `freeIndexes` and later be
returned again. Therefore this sequence can recreate the complete tuple
currently captured by `WasmMemoryWrite32Plan`:

```text
Ram/index X -> unmap/release X -> allocate index X -> remap same guest page
with the same type and flags
```

The resulting `ramIndex` and `ramPageBase` are identical even though the
mapping lifetime is different. Final tuple comparison detects ordinary
changes, but not this exact ABA.

## VERIFIED -- `ownerMemory` closes only one class of mix-up

The updated plan now records `KMemory* ownerMemory` and rejects a different
`KMemory`. This correctly closes the cross-address-space shared-RAM case from
the first review.

It does not bind the plan to the lifetime of `KMemoryData`. A `KMemory` can
replace its `data` pointer without changing its own address:

- `KMemory::execvReset(true)` assigns `data = new KMemoryData(this)`;
- the vfork branch of `KMemory::clone` deletes `this->data` and assigns the
  parent's `data`.

Thus `ownerMemory` remains equal across a complete page-table replacement. The
minimum additional lifetime guard is to capture `KMemoryData* ownerData` at
Prepare and require `getMemData(memory) == ownerData` before any Validate or
Commit dereference. This is separate from, and cheaper than, a page generation.

The normal process lifecycle is expected not to execute an old hot helper
concurrently with exec/vfork page-table replacement, but that concurrency has
not been proven. `ownerData` is still required for a fail-closed API and for a
same-`KMemory` replacement fixture.

## VERIFIED -- mutation lock discipline relevant to the stack target

The principal mapping transitions use `KMemory::mutex`:

- mmap, mprotect, mapPages, native mapping, and invalidation/unmap;
- lazy RAM materialization;
- File materialization;
- COW split/type conversion; and
- Code-page copy/invalidation.

`KMemoryData::allocPages` explicitly says callers should hold
`memory->mutex`, except construction and execv where only one thread should
exist. The mutex is recursive, so a trace may hold it while eventually calling
`KMemory::writed`.

Not every raw flag assignment is mechanically centralized. For example the
framebuffer path calls `setPage` and then `setFlags` without a following
`KMemoryData::onPageChanged`. This is an existing cache-update irregularity
and means that merely adding an increment to `KMemoryData::onPageChanged`
would not yet prove coverage for every page in the general API.

## Decision -- current commit-only lock is not an exact ABA proof

The current sequence is:

```text
Prepare without KMemory::mutex
... execute/read/compute ...
lock KMemory::mutex
revalidate tuple
write
```

It is fail-closed for every mutation which leaves a different tuple. It is not
an exact proof against release/reuse/remap to the same tuple between Prepare
and Commit. The narrow time window and expected stability of a current thread's
stack make the event unlikely, but likelihood is not the contract requested by
documents 225 and 227.

For the first production `0x8E05E` helper, an epoch is not required if one
outer `KMemory::mutex` acquisition covers all of the following as one critical
section:

1. owner-memory and owner-data validation;
2. preparation of every material/code/count read and the single-page stack
   write;
3. the call-free trace computation and buffered alias forwarding;
4. final identity/code-guard validation;
5. `KMemory::writed`; and
6. CPU-state commit before releasing the mutex.

Under the verified mutation discipline above, no target mapping lifetime can
change inside that critical section, so an ABA cannot occur. This decision is
specific to the bounded, indirect-call-free `0x8E05E` trace. The path must
still reject cross-page, non-Ram, COW, Code, File, lazy, invalid, and any
unexpected shared target if the native fixture has not explicitly accepted its
concurrency semantics.

The mutex cost is on every helper hit and may erase the optimization. It must
be microbenchmarked before browser enablement. If continuous locking is too
expensive, commit-only locking plus identity is not a valid substitute; add an
epoch.

## Minimum generation alternatives

### Recommended conservative fallback: one memory-wide `U64` epoch

One `std::atomic<U64>` in `KMemoryData` costs 8 bytes per page table, not per
page. Increment it for every mapping identity/permission/type/backing change.
Prepare snapshots both `ownerData` and the epoch; Commit under the memory mutex
requires both to remain equal. Any unrelated page change causes a harmless
side exit. In a steady PatHouse frame, mapping changes should be rare, but that
is NOT VERIFIED by a counter.

For strict C++ synchronization, Prepare must not race unsafely over non-atomic
MMU bitfields. Either snapshot the tuple while briefly holding
`KMemory::mutex`, then release it with the epoch recorded, or redesign the MMU
publication fields as atomics/seqlock data. A single counter read around an
unlocked bitfield snapshot does not by itself remove the C++ data race.

The epoch update must be placed on a transition primitive that covers
`setPage`, type changes, permission changes, raw flag changes, data-table
replacement, and invalidation. Adding it only to the present
`KMemoryData::onPageChanged` is insufficient until exceptional callers such as
the framebuffer flag update are normalized.

### Exact per-page lookup: parallel `U32` generation array

`K_NUMBER_OF_PAGES` is `0x100000`. A flat `U32` generation array therefore
costs exactly 4 MiB per `KMemoryData`. This is especially material in the fixed
1 GiB browser heap. Embedding another word in `MMU` is no cheaper on wasm32
(4-byte MMU becomes 8 bytes, also +4 MiB), and can be worse on a 64-bit host
because an 8-byte MMU may align/pad to 16 bytes (+8 MiB).

A two-level sparse array modeled after the code cache has a 1024-pointer root
(4 KiB on wasm32, 8 KiB on a 64-bit host) and allocates one 4 KiB
`U32[1024]` leaf per 4 MiB guest-address region whose mappings change. Its
worst case is still about 4 MiB plus the root, but typical committed cost can be
far lower. Lookup adds two dependent loads. `U16` or the spare one-bit pad is
not an exact solution because it wraps after 65,536 or two transitions.

A 32-bit counter also eventually wraps; a `U64` per-page array costs 8 MiB but
makes wrap irrelevant in practice. For this first one-address hot trace, the
8-byte memory-wide epoch or one continuous lock is preferable to adding
4--8 MiB per process.

## Required static/dynamic gates

Before production integration:

1. add `ownerData` and a same-`KMemory`/replaced-`KMemoryData` rejection test;
2. choose and document either continuous outer locking or an epoch -- do not
   describe commit-only tuple validation as ABA-safe;
3. if using the outer lock, microbenchmark it against the NormalCPU oracle and
   the unlocked helper;
4. if using an epoch, instrument mapping-change count during PatHouse and prove
   all transition sites increment it;
5. retain the full document-229 page-class tests and add an exact forced
   RamPage-index reuse fixture; and
6. keep browser enablement off until the complete `0x8E05E` differential
   fixture passes with the chosen synchronization strategy.

## NOT VERIFIED

- Concurrent exec/vfork against an executing helper is not reproduced.
- Exact same-index RamPage reuse between Prepare and Commit is not dynamically
  reproduced.
- The actual `0x8E05E` stack page's `PAGE_SHARED/PAGE_FUTEX/PAGE_MAPPED`
  combination and RamPage reference count are not measured.
- Continuous outer-mutex cost and memory-wide epoch invalidation frequency are
  not measured.
- No epoch or per-page generation exists in production code.

## Source evidence

- `source/emulation/softmmu/soft_mmu.h:24-63`
- `source/emulation/softmmu/kmemory_soft.h:37-68`
- `source/emulation/softmmu/kmemory_soft.cpp:40-54, 81-94, 125-159, 206-250`
- `source/emulation/softmmu/soft_ram.cpp:46-115, 150-180`
- `source/emulation/softmmu/codePageData.h:39-71`
- `source/emulation/softmmu/codePageData.cpp:298-380`
- `source/kernel/kmemory.cpp:101-102, 211-212, 280-305, 347-353, 947-985`
- `source/kernel/devs/devfb.cpp:486-495`
- `source/emulation/cpu/normal/wasmMemoryTier.h:44-55`
- `source/emulation/cpu/normal/wasmMemoryTier.cpp:21-33, 250-293`
