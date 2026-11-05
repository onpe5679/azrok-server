# 227 Gate 2c soft-MMU transactional dword-write contract

Date: 2026-07-21

## Scope

This note fixes the fail-closed guest-write contract needed by document 225's
`0x1008E05E` fused scan iteration. It follows the current BoxedWine soft-MMU
implementation from `KMemory::writed`/`writedInline` through `MMU`, `RWPage`,
copy-on-write, code, file-backed, and invalid pages. It does not modify or run
production code.

The inspected source snapshot is
`artifacts/boxedwine/20260719_gate2b_native/Boxedwine`. The two central source
hashes are:

- `source/emulation/softmmu/kmemory_soft.h` SHA-256
  `D50877766518013EBEB53E26CAC84B806379F4E4B194A0B2E3E7E2C7AF58ECE6`
- `source/kernel/kmemory.cpp` SHA-256
  `F1D5FE55B84C66100876A740ABE46D35761CF1FCDA3D8964D8AC967E744FE206`

## VERIFIED -- what the ordinary dword writer does

`KMemory::writedInline` uses its direct host-RAM store only when all of the
following are true:

1. `(address & 0xFFF) < 0xFFD`, equivalently the four-byte operand is wholly
   inside one 4096-byte guest page;
2. this build does not define `UNALIGNED_MEMORY`; and
3. the selected `MMU` entry has `canWriteRam == 1`.

It then stores the dword through
`ramPageGet((RamPage)mmu.ramIndex) + pageOffset`. At offsets `0xFFD..0xFFF`, it
instead executes four ordered `writeb` calls. Consequently a dword can touch at
most two pages, and the ordinary cross-page implementation does not preflight
both pages transactionally.

`MMU::onPageChanged` recomputes the cached bit as:

```text
page->canWriteRam(mmu) && (flags & PAGE_WRITE)
```

`RWPage::canWriteRam` additionally requires nonzero `ramIndex`. In the current
page table, the only page implementation which can return true is the ordinary
RAM/RW page. Therefore `canWriteRam == 1` currently proves all of the following:

- the page has write permission;
- a materialized `RamPage` exists (`ramIndex != 0`);
- no lazy file-page or zero-page materialization is required;
- no copy-on-write split is required; and
- no code-page invalidation callback is required.

For a reusable helper, checking `PageType::Ram`, `PAGE_WRITE`, and nonzero
`ramIndex` in addition to `canWriteRam` is deliberately redundant but makes the
contract fail closed if another page class later changes its `canWriteRam`
policy.

## VERIFIED -- why the other page types must side-exit

| Page state | `canWriteRam` | Ordinary write behavior | Transactional helper |
|---|---:|---|---|
| materialized `Ram` + write permission | true | direct host-RAM write | eligible after identity checks |
| lazy `Ram` with `ramIndex == 0` | false | allocates/materializes RAM under the memory mutex | side-exit |
| `CopyOnWrite` | false | locks, clones a multiply referenced private page or converts it to `Ram`, then writes | side-exit |
| `Code` | false | compares changed bytes, handles shared backing, writes, then calls `removeCode` for the changed range | side-exit |
| `File` | false | resolves the file-backed mapping on demand, then writes | side-exit |
| invalid/none | false | invokes the normal segmentation/mapping path | side-exit |

A direct store into `CopyOnWrite` would leak the write to another address space.
A direct store into `Code` would leave translated code alive after its guest
bytes changed. These exclusions are semantic requirements, not merely cautious
performance guards.

## VERIFIED -- flags and page identity

`PAGE_SHARED`, `PAGE_FUTEX`, and `PAGE_MAPPED` do not participate in the current
`writedInline` fast-path predicate. `PAGE_FUTEX` is set by
`getRamPtr(..., futex=true)` and is consulted by `KMemory::clone`: a non-shared
futex page is copied immediately instead of being converted to COW. It is not a
normal write notification or wake-up hook. Shared RAM therefore remains
eligible under the same rule used by the ordinary writer; its writes are
intentionally visible through the shared backing.

Eligibility alone is not a stable host pointer. `PageType`, flags, `ramIndex`,
and the pointer returned by `ramPageGet` may change when mappings or page
ownership change. A speculative write plan must snapshot at least:

```text
guest page number, PageType, flags, canWriteRam, ramIndex, host page base
```

and compare the same tuple immediately before commit. A changed tuple causes a
complete side exit with no guest memory or CPU-state change.

The host mutex type used by this snapshot is `std::recursive_mutex`, via
`BOXEDWINE_MUTEX`. COW and code-page mutation take `KMemory::mutex`. This proves
that a helper may hold the memory mutex while calling the normal `KMemory`
write entry without self-deadlocking on those recursive acquisitions. It does
not by itself prove that every possible mapping mutation or ordinary RAM write
is serialized by that mutex; see the NOT VERIFIED section.

## VERIFIED -- observer boundary

No generic watchpoint or memory-write observer was found in the current
soft-MMU and kernel write paths searched for this note. There is, however, a
project-specific observer in `KMemory::writed`: it logs the exact dword value
`0x33006D00` up to 32 times before calling `writedInline`.

Therefore these operations are not currently observer-equivalent:

```text
memory->writed(address, value)     preserves the project observer
memory->writedInline(address, ...) bypasses it
*hostPointer = value               bypasses it
```

The absence of another hook in the searched files is not a permanent API
guarantee. A reusable optimized writer must commit through `KMemory::writed`,
or move all observers into one centralized checked-write API used by both the
interpreter and helper. Raw host-pointer commit is not approved by this
contract.

## Proposed fail-closed contract for the `0x8E05E` helper

The smallest safe first release should support only the actual single dword
write at `[SS:EBP+8]` and reject page crossing. It should perform these steps in
order:

1. Compute the SS-based effective address with the same 32-bit wrap and segment
   rules as the interpreter. Reject any address/segment condition for which the
   ordinary operand resolver would fault or take a special path.
2. Reject offsets `0xFFD..0xFFF`. This avoids the ordinary writer's four-byte,
   potentially partial cross-page behavior in the first release.
3. Before changing memory, registers, lazy flags, or EIP, require the target
   entry to satisfy all of:
   `canWriteRam == 1`, `PageType::Ram`, `PAGE_WRITE != 0`, and
   `ramIndex != 0`.
4. Snapshot guest page, full flags, page type, `canWriteRam`, `ramIndex`, and
   host page base. Buffer the new counter value; do not publish it yet.
5. If a later read inside the fused iteration overlaps the buffered four-byte
   range, forward the buffered bytes. If forwarding is not implemented, reject
   that invocation before commit. In particular this applies to the latch read
   `[DS:ESI+0x264]` identified in document 225.
6. Complete every other read, code guard, branch decision, and successor
   validation needed by the chosen call-free path. The side exit at
   `0x1008E076` must occur before the first PUSH and before any buffered write is
   published.
7. At the final commit point, hold `KMemory::mutex`, re-read the full target
   tuple, and reject if any field or host base differs. Then call
   `KMemory::writed(address, bufferedValue)` while the page remains eligible.
   This preserves the current observer and reaches the ordinary one-page direct
   store.
8. Only after the write returns, commit the helper's buffered registers, lazy
   flags, and direct successor EIP. On every earlier failure, return with the
   complete guest CPU and memory state unchanged so the interpreter replays the
   original entry.

This is intentionally stronger than checking a cached host pointer once. The
first-release decision is: **single-page, materialized writable Ram only; all
other cases side-exit unchanged.**

## Cross-page extension contract

A later general helper may accept a dword at offset `0xFFD..0xFFF`, but only
after all four bytes have been prepared as one transaction:

- reject guest-address overflow before evaluating `address + 1..3`;
- identify both pages without a fixed-array overrun;
- preflight and snapshot both pages using the same writable-Ram tuple;
- perform every read and alias-forwarding decision before the first byte write;
- revalidate both identities together under the memory mutex; and
- commit the four little-endian bytes only after both pages pass.

Calling the existing cross-page `writedInline` after only the first-page check
is not transactional: its four `writeb` operations can expose a prefix before a
later page faults or changes. Until a two-page atomic checked-write API and its
differential tests exist, page crossing remains a mandatory side exit for
`0x8E05E`.

## NOT VERIFIED

- No production helper implements this write plan yet.
- No native differential fixture has exercised writable RAM, read-only RAM,
  lazy-zero, COW, Code, File, invalid, aliasing, or cross-page write cases.
- It is not proven that every page-table mutation and every RAM write from all
  host threads is serialized by `KMemory::mutex`. The proposed immediate
  revalidation closes ordinary mapping drift but is not claimed as a general
  multi-host-thread atomic-memory model.
- A generic debugger watchpoint facility outside the searched soft-MMU/kernel
  paths has not been ruled out.
- The value written by the `0x8E05E` counter has not been bounded so as to prove
  that the project-specific `0x33006D00` observer can be omitted.
- Browser correctness and FPS benefit remain unmeasured.

## Required next dynamic gate

Before a browser build, extend the native relocated-interpreter differential
fixture with at least: aligned and unaligned one-page RAM writes, offset
`0xFFC`, crossing offsets `0xFFD..0xFFF`, read-only, lazy-zero, COW with two
owners, Code with a live compiled block, File, invalid, DS/SS alias/no-alias,
incoming CF variants, every call-free successor, and full no-commit comparison
on every rejected case. Only an exact passing fixture authorizes production
enablement.

## Source evidence

- `source/emulation/softmmu/kmemory_soft.h:93-108`
- `source/emulation/softmmu/soft_mmu.cpp:77-80`
- `source/emulation/softmmu/soft_rw_page.cpp:117-128`
- `source/emulation/softmmu/soft_copy_on_write_page.cpp:24-72`
- `source/emulation/softmmu/soft_code_page.cpp:28-150`
- `source/emulation/softmmu/soft_file_map.cpp:24-75`
- `source/emulation/softmmu/soft_invalid_page.cpp:24-70`
- `source/kernel/kmemory.cpp:890-904, 930-981`
- `source/util/synchronization.h:72-80`
- `include/kmemory.h:31-37, 144-164`
