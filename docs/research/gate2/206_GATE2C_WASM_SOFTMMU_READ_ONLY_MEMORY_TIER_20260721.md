# 206 Gate 2c WASM soft-MMU read-only memory tier

Date: 2026-07-21

## Scope

This step follows the runtime-generated module proof in document 205. It
answers how a generated module may reach guest memory without treating an x86
guest virtual address as a WebAssembly linear-memory address. It does not
integrate the tier into `NormalCPU::run` or start a browser game session.

## VERIFIED -- guest VA is not a linear-memory address

The soft MMU divides the 32-bit guest address space into 4 KiB pages. Each
guest page has an `MMU` entry containing direct-read/direct-write bits and a
`ramIndex`. `ramPageGet` converts that index into the actual host/WASM page
base by shifting it left 12 bits. `KMemory::readdInline` and `readb` use that
physical page plus the guest page offset only when `canReadRam` is set.

Consequently a generated module must not execute `i32.load guestAddress`.
It needs a validated guest-page-to-linear-page translation for every memory
access.

## VERIFIED -- why the first tier is read-only

- A zero-backed anonymous Ram page can have read permission while
  `ramIndex == 0`; the interpreter allocates it on first access.
- A File page loads file data and changes page type on demand.
- A CopyOnWrite write can allocate and copy a new physical page before the
  store.
- Invalid and permission-denied accesses enter `seg_mapper`/`seg_access`.
- Cross-page scalar reads are decomposed byte-by-byte by `KMemory`, while
  ordinary same-page reads use one physical page.

Pre-materializing all pages with `getRamPtr(..., force=true)` would therefore
move faults and COW/file side effects ahead of their original instruction.
Likewise, committing one generated guest store before discovering a later
unsupported page would make an interpreter side exit non-restartable.

The implemented first tier accepts only fixed 1/2/4/8-byte reads whose pages
are already `canReadRam`. It performs no allocation, file load, COW split, or
permission fault. Any unresolved page, address wrap, invalid width, or block
containing a guest write must side-exit before GPR/flags/EIP commit.

## VERIFIED -- implementation and differential oracle

`wasmMemoryTier.{h,cpp}` builds a read plan containing each guest page,
offset, length, and physical RamPage identity. It supports a scalar crossing
one page boundary, validates every captured page identity and direct-read bit
again before reading, and publishes result values only after the complete
plan succeeds. Aliased guest mappings retain their shared physical identity.

`testWasmMemoryTier.cpp` verifies against real `KMemory` behavior:

- preparation rejects an unmaterialized anonymous page without allocating it;
- after interpreter materialization, same-page and cross-page values match
  `KMemory::readd`;
- two guest mappings of one RamPage observe the same post-plan alias write;
- a COW split invalidates the stale physical-page plan and preserves the old
  alias value;
- permission revocation and unmap invalidate the plan; and
- a failed validation leaves the caller's sentinel result vector unchanged.

MSVC x64 Test builds successfully and reports:

```text
Test WASM Memory Tier ... OK
0 tests FAILED in 0s
```

## Boundary / next step

This is a safe side-exit contract and reference helper, not yet emitted WASM
memory code. A generated read-only block may consume equivalent translation
records and must repeat all page guards before committing CPU state. Blocks
whose later effective addresses depend on earlier loads need translation in
the generated module rather than a static entry-register preflight.

Guest writes remain unsupported until the compiler can preserve instruction
ordering with either provably non-faulting complete preflight plus an alias-
aware write buffer, or precise interpreter continuation at the faulting
instruction. File/on-demand/COW writes must continue through `KMemory`.

## NOT VERIFIED

- The runtime emitter does not yet lower x86 memory operands through this
  tier.
- No Emscripten/browser execution or FPS result follows from this unit test.
- Concurrent page remap behavior has not been stress-tested; generated code
  must retain the same immediate identity/permission guard used here.
- Store ordering, memory-dependent effective addresses, branches, x87, and
  SIMD integration remain separate gates.
