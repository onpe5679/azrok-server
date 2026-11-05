# 232 Gate 2c Hot-AOT code-guard invalidation contract

Date: 2026-07-21

## Scope

This note asks whether the production `0x1008E05E` fused helper may replace its
per-hit exact `24 + 12 + anchor` byte guard with existing CodePage,
`removeCode`, decoded-op cache, or write-count state. It traces the dispatcher
before deciding the minimum safe invalidation design. No production source was
changed.

The relevant fixed code lies on two guest pages: the function anchor at
`0x1008DF5D` is on page `0x1008D000`; scan block
`0x1008E05E..0x1008E075`, the excluded indirect-call anchor near
`0x1008E097`, and reset/latch block `0x1008E09D..0x1008E0A8` are on page
`0x1008E000`.

## VERIFIED -- decoded-code invalidation does not invalidate Hot-AOT dispatch

`NormalCPU::run` calls `d3d9WebTryHotAOT(this)` before dispatching `nextOp`.
The dispatcher caches `acknexMemory` and fixed entry addresses in
`thread_local` variables. Once resolved, an exact address comparison directly
calls the hard-coded helper.

`KMemory::removeCode` removes decoded/JIT operations from `DecodedOpCache`, but
does not clear the Hot-AOT thread-local entry, signature state, or an AOT
registry. Therefore this sequence is possible:

```text
write executable byte
CodePage calls removeCode and decoded op disappears
CPU returns to the same physical entry
d3d9WebTryHotAOT sees the cached address before decoded-op dispatch
hard-coded helper is called
```

Pending decoded-op deallocation only keeps old `DecodedOp` allocations alive
long enough to avoid pointer lifetime races. It does not certify their bytes
or gate the independent Hot-AOT helper.

Checking that `getDecodedOp(entry)` is non-null is also insufficient. It can
catch the removal window, but the modified bytes may be decoded again and
produce a new non-null op while the address-based dispatcher still selects the
old hard-coded semantics.

Thus the dispatcher can reach a stale helper after normal op-cache
invalidation. Some guard inside the Hot-AOT dispatch/helper is mandatory.

## VERIFIED -- existing write counts are not a code epoch

`DecodedOpCache::removeStartAt` increments `U8` write counts only when
`becauseOfWrite` is true and a decoded page cache already exists. Counts
saturate at `0xFF`, are stored per byte, and may be cleared when a page leaves
Code state. Whole-cache teardown also deletes them.

They cannot serve as a monotonic identity because:

- no decoded page means no count allocation or increment;
- saturation makes later writes indistinguishable;
- clear/recreate produces an ABA back to zero;
- non-write mapping/type/permission changes need not increment them; and
- the Hot-AOT dispatcher neither stores nor checks them.

`writeCounts` should remain a dynamic-code heuristic, not be reused as the
correctness guard.

## VERIFIED -- a simple CodePage epoch still misses raw pointer writes

Changed `CodePage::writeb/writew/writed` operations are well behaved for an
epoch design: they hold `KMemory::mutex`, update the backing, and call
`removeCode` for the changed range.

The writable-pointer API is a harder boundary. `CodePage::getRamPtr` with
`write=true, force=true` calls `removeCode` before returning the raw page
pointer. Single-page `KMemory::getRamPtr` and `lockReadWriteMemory` can then
return that pointer directly. There is no matching release notification for a
direct single-page pointer, and subsequent host writes through it do not call
`CodePage` or `removeCode` again.

An epoch incremented when the pointer is granted can therefore become stale in
this order:

```text
invalidate/bump epoch -> return writable pointer -> validate/cache helper at
that epoch -> caller writes through retained pointer without another bump
```

The same alias can originate while a page is ordinary writable Ram and remain
alive after the backing is converted in place to Code: `getOrCreateCodePage`
uses `setPageType` and preserves the RamPage. Current APIs do not track such
pointer leases. Consequently a global or per-page code epoch alone cannot
prove arbitrary executable backing immutable.

## RX narrowing -- useful but not yet sufficient by itself

If both guarded pages are currently `PageType::Code` with `PAGE_EXEC` and
without `PAGE_WRITE`, normal guest stores and new writable `getRamPtr` grants
are rejected. A monotonic mapping/permission epoch can then detect mprotect,
unmap/remap, backing replacement, and later enabling of write permission.

This is the only plausible narrow route to skipping exact bytes, but two facts
remain NOT VERIFIED:

1. the real Acknex pages `0x1008D000` and `0x1008E000` have that exact RX state
   in the browser; and
2. no writable host pointer to their current RamPage backing was granted and
   retained before the pages became RX/Code.

For a general proof, each page needs a permanent `everDirectWritableAlias`
taint set whenever any direct writable pointer is issued while that RamPage is
backing the mapping. Tainted executable pages must retain the exact matcher.
The current MMU has no such taint.

## Minimum epoch/identity design if the optimization is pursued

A safe cache cannot be keyed only by `KMemory*` and entry. At minimum it needs:

```text
ownerMemory
ownerData
entry address
two guarded guest page numbers
their PageType, flags, ramIndex, and host bases
one monotonic executable/mapping epoch
exact-signature state for that epoch
```

Initial validation and every revalidation after an epoch change must occur
under `KMemory::mutex`, require untainted RX Code pages, and compare every exact
semantic byte and anchor. Only then may the cache record `valid at epoch E`.

The epoch must change for all of:

- a changed CodePage write;
- granting a direct writable alias to either guarded backing;
- any permission change, especially enabling write;
- Code/Ram/COW/File/None type or RamPage-backing changes;
- unmap/remap and exec reset; and
- same-`KMemory` `KMemoryData` replacement, also caught by `ownerData`.

A memory-wide `U64` epoch is only 8 bytes and makes unrelated code/mapping
changes cause a harmless one-time exact revalidation. A range-specific epoch
could avoid false invalidation, but needs a registered-range lookup on every
mutation and is more invasive for only two pages.

The helper must also validate the epoch at its final transaction boundary,
under the same memory mutex used by CodePage writers, before any memory or CPU
state is published. This applies even to a fused path which has no guest write:
otherwise a code mutation during buffered execution can still commit stale
registers, flags, or EIP.

This scheme is not production-ready until direct writable aliases are tracked
or independently ruled out for both guarded backings.

## Immediate decision -- retain exact matching

The existing infrastructure cannot satisfy both correctness and removal of the
per-hit byte reads. `removeCode`, op-cache presence, and writeCounts are not
valid substitutes, and no complete epoch/alias-taint path exists. Therefore the
first production `0x8E05E` release must retain an exact guard on every hit.

The exact guard can still be made cheaper without weakening it:

1. prepare the two resident Code-page identities once per hit;
2. while holding the transaction's existing memory mutex, compare the fixed
   regions directly from those two page bases using fixed-size word loads or
   `memcmp`;
3. cover all `24 + 12 + anchor` bytes, not merely the first opcode;
4. perform one consolidated page-identity validation rather than one per
   region; and
5. publish no CPU or guest-memory state until every comparison succeeds.

A hash is not an exact substitute because collisions exist. Hash-then-compare
only helps when mismatches are common, whereas this hot path should almost
always match. Consolidated direct comparison is the appropriate optimization.

The byte guard should be timed separately before more infrastructure is built.
If its measured share is not material, the epoch design has no performance
justification.

## Required dynamic gates before revisiting the decision

- Log PageType, all flags, ramIndex, host base, and refcount for both guarded
  Acknex pages in the real browser session.
- Add a mutation fixture proving decoded-op removal alone still reaches the
  Hot-AOT dispatcher and that the exact guard side-exits unchanged.
- Exercise changed bytes in every fixed region and each anchor, followed by
  restore-to-original, to catch signature-cache ABA.
- Exercise mprotect RW -> write -> RX and unmap/remap with identical bytes and
  with altered bytes.
- Exercise a retained writable pointer if the page API permits constructing
  one in the fixture.
- Measure consolidated exact comparison versus the current multiple matcher
  calls and versus the proposed epoch load.

## NOT VERIFIED

- Real-browser RX/RWX flags and prior writable-alias history of the two Acknex
  pages are not measured.
- No code/mapping epoch or writable-alias taint exists in production.
- Concurrent CodePage mutation versus a running fused helper is not exercised.
- The exact guard's isolated and frame-level cost is not measured.
- The production fused helper under development was not modified by this
  investigation.

## Source evidence

- `source/emulation/cpu/normal/normalCPU.cpp:590-735, 919-953`
- `source/emulation/cpu/normal/hotAotMaterialLatch.cpp:7-69`
- `source/emulation/softmmu/soft_code_page.cpp:27-148`
- `source/emulation/softmmu/codePageData.cpp:83-117, 147-184, 187-225, 227-290, 298-380`
- `source/emulation/softmmu/kmemory_soft.cpp:206-250`
- `source/kernel/kmemory.cpp:484-625, 655-755, 919-944`
- `source/emulation/softmmu/soft_mmu.cpp:27-80`
