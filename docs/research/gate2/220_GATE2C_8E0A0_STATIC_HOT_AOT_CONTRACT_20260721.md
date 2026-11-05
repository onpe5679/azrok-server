# 220 Gate 2c exact `0x8E0A0` static hot-AOT contract

Date: 2026-07-21

## Scope

This document fixes the static contract for the exact Acknex material-scan
loop latch at original VA `0x1008E0A0`.  It is an implementation input, not a
claim of browser speedup.  Document 219 separately verifies that this exact
entry is live in intact PatHouse; its counter is an entry-frequency lower bound,
not a time percentage.

The binary inspected here is the repository `acknex.dll` with SHA-256:

`876f6870f6858c3829c0830415bf30cf7dd375590810eef231a7e6b1a68eedc6`

No production dispatch code was changed for this static pass.

## VERIFIED -- bytes, instructions, and successors

The PE has image base `0x10000000`.  RVA `0x8E0A0` maps directly into `.text`
and the exact nine-byte basic block is:

```text
1008E0A0  47                         INC EDI
1008E0A1  3B BE 64 02 00 00          CMP EDI,dword ptr [ESI+264h]
1008E0A7  72 B5                      JC 1008E05E
```

Successors are therefore exact and direct:

- CF=1: `0x1008E05E` (`entry - 0x42`)
- CF=0: `0x1008E0A9` (`entry + 9`)

Ghidra places this block inside `FUN_1008DF5D`, body
`[0x1008DF5D,0x1008E0E0]`.  Its static predecessors are the unconditional jump
at `0x1008E06F` and fall-through from `0x1008E09D`; the taken successor returns
to the material-ID scan body.  The block itself has no call, guest store,
x87, SSE, stack, or indirect-control-flow operation.

## VERIFIED -- exact architectural state contract

Let:

```text
newEdi = (EDI + 1) mod 2^32
readAddress = (DS.base + ESI + 0x264) mod 2^32
limit = dword guest memory at readAddress
result = (newEdi - limit) mod 2^32
```

On a completed helper:

1. `EDI = newEdi`.
2. BoxedWine's final lazy tuple is exactly:
   `dst.u32=newEdi`, `src.u32=limit`, `result.u32=result`,
   `lazyFlagType=FLAGS_CMP32`.
3. The taken decision is unsigned `newEdi < limit`, which is the `CMP32` carry
   condition used by `JC`.
4. Physical EIP becomes the relocated equivalent of `0x1008E05E` when taken,
   otherwise the relocated equivalent of `0x1008E0A9`.  Store it through the
   existing CS-aware commit pattern:
   `cpu->eip.u32 = physicalTarget - cpu->seg[CS].address`, followed by
   `cpu->nextOp = cpu->getNextOp()`.
5. All other GPRs, memory, x87 state, XMM state, MXCSR, control flags, and the
   backing `cpu->flags` word remain unchanged. `lazyFlagTypePrev` is unchanged,
   while `oldCF` must receive the incoming carry consumed by `INC`.

Although the `INC32` lazy tuple is replaced by the immediately following
successful `CMP`, BoxedWine's `INC` path first stores the incoming carry in
`oldCF`. A completed helper must evaluate `getCF()` and commit that value to
`oldCF` together with the final state; it need not materialize unrelated flags.

The memory operand uses the default `DS` segment because its base register is
ESI and there is no segment override.  A helper that reads `ESI+0x264` without
adding `cpu->seg[DS].address` is not generally equivalent, even though normal
Wine flat segments usually make DS.base zero.

## VERIFIED -- fault-safe read ordering

The architectural instruction order is `INC` and then the possibly faulting
`CMP` read.  The existing read-only hot-AOT tier cannot commit half a trace and
replay at the second instruction.  It must therefore use a transactional side
exit:

1. Compute `newEdi` and `readAddress` only into host temporaries.
2. Prepare one `WasmMemoryReadRequest{readAddress,4}` with
   `wasmMemoryPrepareReadOnly`.
3. Read it through `wasmMemoryReadPrepared` and revalidate the plan with
   `wasmMemoryValidateReadOnly`.
4. If any step is not ready, return `false` with original EDI, flags/lazy
   tuple, EIP, `nextOp`, and all other guest-visible state untouched.  The
   interpreter will then execute `INC` and reproduce any later guest fault in
   architectural order.
5. Only after all checks succeed, commit EDI, the final `CMP32` tuple, and EIP.

This block requires no guest-write tier.  A four-byte operand crossing a page
boundary is acceptable only if the existing read-only planner admits and
revalidates both resident direct-read spans.  Address-width overflow rejected
by that tier must side-exit rather than invent wrapping host access.

### Release-path allocation constraint

Document 219 observes at least 33,554,432 dispatcher-visible entries in one
PatHouse session.  The differential fixture may reuse the generic
`WasmMemoryReadPlan` vectors as an oracle, but a release helper must not create
`std::vector` objects or heap allocations per latch hit.  The production form
needs the equivalent scalar, no-allocation four-byte plan: check the one or two
covered MMU pages for `canReadRam`, snapshot their `ramPageGet` identities,
assemble the little-endian dword, recheck both page identities/permissions,
and only then commit.  This is a performance requirement derived from the
verified entry frequency; it does not weaken any of the fault-order rules
above.

## VERIFIED -- binary and containing-function guards

The minimum exact block guard is all nine bytes, not only the first dword:

```cpp
memory->readd(entry)      == 0x64BE3B47u && // 47 3B BE 64
memory->readd(entry + 4u) == 0x72000002u && // 02 00 00 72
memory->readb(entry + 8u) == 0xB5u
```

The production helper should additionally retain the existing relocation and
process guard (`getModuleName(address).endsWith("acknex.dll", true)`, same
`KMemory*`, RVA-derived entry) and spread identity checks across the containing
function.  Suitable exact anchors from the same binary are:

```cpp
memory->readd(entry - 0x143u) == 0x8B55FF8Bu && // FUN_1008DF5D prologue
memory->readd(entry - 0x042u) == 0x0254868Bu && // 1008E05E scan-body entry
memory->readd(entry + 0x034u) == 0x8DFC458Bu    // 1008E0D4 epilogue start
```

As with the current transform helpers, signature state may be cached per
thread only while both `KMemory*` and relocated entry match.  Recheck at least
the exact block entry during dispatch so code mutation disables the helper.
The guard must fail closed to the interpreter; it must never turn a signature
mismatch into a guest fault or successful AOT dispatch.

## Implementation-ready differential cases

Before production enablement, the native oracle should compare interpreter and
helper state for at least:

- `newEdi < limit` taken;
- `newEdi == limit` fall-through;
- `newEdi > limit` fall-through;
- EDI wrap (`0xFFFFFFFF -> 0`) with both branch outcomes;
- nonzero DS.base and nonzero CS.base;
- a resident cross-page dword;
- unmapped/nonresident read side exit proving byte-for-byte state preservation;
- signature mismatch at the entry and at one containing-function anchor.

Capture all GPRs, materialized flags plus the raw lazy tuple, EIP, `nextOp`,
x87/XMM/MXCSR, and sentinel memory.  This catches the two most likely subtle
errors: omitting DS.base and publishing the increment before a failed read
preflight.

## Evidence

- `docs/research/218_GATE2C_RELOCATION_AWARE_MULTI_ENTRY_PROBE_SET_20260721.md`
- (로그 원본은 공개본에서 뺐다) — acknex_next_aot_candidates_ghidra_20260721
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/source/emulation/cpu/normal/wasmMemoryTier.cpp`
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/source/test/cpu/testHotAOTBranchRead.cpp`
- direct PE `.text` byte extraction from the hash-fixed repository
  `acknex.dll`

## NOT VERIFIED

- Exact fraction of frame time attributable to this block; document 218's
  4.113% is only the whole containing-family ceiling, and document 219's
  33,554,432 count is not a time sample.
- Native differential execution for this block.
- Production enablement, browser rendering equivalence, or FPS gain.
