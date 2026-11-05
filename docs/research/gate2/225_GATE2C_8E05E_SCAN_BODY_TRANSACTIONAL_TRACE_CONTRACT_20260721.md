# 225 Gate 2c exact `0x8E05E` scan-body transactional trace contract

Date: 2026-07-21

## Scope

This is the static contract for the material-ID scan body beginning at
original VA `0x1008E05E`, through the paths which return to the
`0x1008E0A0` latch. It separates the call-free paths from the indirect D3D
draw boundary and proposes the largest first transactional trace that does not
execute a call. No browser session or production code was changed.

The inspected repository `acknex.dll` SHA-256 is
`876f6870f6858c3829c0830415bf30cf7dd375590810eef231a7e6b1a68eedc6`.

## VERIFIED -- exact blocks, bytes, and successors

### A. Scan and material comparison: `0x1008E05E..0x1008E06B`

```text
1008E05E  8B 86 54 02 00 00    MOV EAX,dword ptr [ESI+254h]
1008E064  8B 04 B8             MOV EAX,dword ptr [EAX+EDI*4]
1008E067  3B 45 0C             CMP EAX,dword ptr [EBP+0Ch]
1008E06A  75 05                JNZ 1008E071
```

Equal falls through to `0x1008E06C`; not-equal goes to `0x1008E071`.
The first two operands use DS and `[EBP+0Ch]` uses SS. The final lazy tuple is
`CMP32(materialId,param_2)`; JNZ consumes ZF without replacing it.

### B. Equal-run increment: `0x1008E06C..0x1008E070`

```text
1008E06C  FF 45 08             INC dword ptr [EBP+8]
1008E06F  EB 2F                JMP 1008E0A0
```

This is an SS-based read-modify-write. It preserves the carry from block A in
`oldCF`, publishes the `INC32` lazy tuple, and reaches the latch. It is the
first guest-write requirement in the trace.

### C. Mismatch run-length test: `0x1008E071..0x1008E075`

```text
1008E071  39 5D 08             CMP dword ptr [EBP+8],EBX
1008E074  76 27                JBE 1008E09D
```

The counter read uses SS. The resulting lazy tuple is
`CMP32(counter,EBX)`. Unsigned `counter <= EBX` goes to block E; otherwise
execution falls through to the indirect-call setup at `0x1008E076`.

### D. Indirect D3D draw boundary: `0x1008E076..0x1008E09C`

```text
1008E076  FF 75 08             PUSH dword ptr [EBP+8]
1008E079  8B 8E 30 02 00 00    MOV ECX,dword ptr [ESI+230h]
1008E07F  8B 11                MOV EDX,dword ptr [ECX]
1008E081  8B C7                MOV EAX,EDI
1008E083  2B 45 08             SUB EAX,dword ptr [EBP+8]
1008E086  33 DB                XOR EBX,EBX
1008E088  8D 04 40             LEA EAX,[EAX+EAX*2]
1008E08B  50                   PUSH EAX
1008E08C  FF B6 3C 02 00 00    PUSH dword ptr [ESI+23Ch]
1008E092  53                   PUSH EBX
1008E093  53                   PUSH EBX
1008E094  6A 04                PUSH 4
1008E096  51                   PUSH ECX
1008E097  FF 92 48 01 00 00    CALL dword ptr [EDX+148h]
```

The call is the decompiler's seven-argument D3D draw boundary. This entire
block is excluded from the first transactional trace. When block C selects
it, the helper must exit at physical `0x1008E076` before any PUSH, GPR setup,
flag change, or call.

### E. Reset empty run: `0x1008E09D..0x1008E09F`

```text
1008E09D  89 5D 08             MOV dword ptr [EBP+8],EBX
```

This SS-based guest write does not alter flags and falls through to the latch.

### Existing latch: `0x1008E0A0..0x1008E0A8`

```text
1008E0A0  47                   INC EDI
1008E0A1  3B BE 64 02 00 00    CMP EDI,dword ptr [ESI+264h]
1008E0A7  72 B5                JC 1008E05E
```

The count read uses DS. It branches back to the scan body when unsigned
`newEDI < count`, otherwise falls through to `0x1008E0A9`. Document 220
contains its full standalone contract. Ghidra's CFG independently records A,
B, C, D, E, and the latch as six basic blocks with exactly these edges.

## VERIFIED -- read, write, and flag surfaces

| Path | Ordered reads | Ordered writes | Final state before successor |
|---|---|---|---|
| equal | DS `[ESI+254h]`; DS `[array+EDI*4]`; SS `[EBP+0Ch]`; SS `[EBP+8]`; DS `[ESI+264h]` | SS `[EBP+8]=old+1` before latch read | incremented EDI; final latch `CMP32(newEDI,count)` |
| mismatch, JBE | first three A reads; SS `[EBP+8]`; DS `[ESI+264h]` | SS `[EBP+8]=EBX` before latch read | incremented EDI; final latch `CMP32(newEDI,count)` |
| mismatch, fall | first three A reads; SS `[EBP+8]` | none | EIP `0x1008E076`; final `CMP32(counter,EBX)`; EAX remains material ID |

MOV, JMP, Jcc, and LEA do not replace flags. On a path that reaches the latch,
its final CMP replaces the earlier A/C/INC lazy tuple, but raw `oldCF` must
still match the intervening INC semantics. On equal, latch INC consumes the
carry preserved by block B's INC; on mismatch/JBE it consumes CF from block C.
The mismatch fall path does not execute the latch and retains block C's tuple.

All 32-bit effective-address calculations use modulo-2^32 offset arithmetic
and the named segment base. A conservative helper may reject overflow and
replay in the interpreter, but it must not omit DS/SS or turn a wrapped guest
address into a host pointer.

## Proposed largest first call-free transactional trace

The useful first unit is a **single fused scan iteration** beginning at
`0x1008E05E`:

1. execute A;
2. on equal, execute B and then the latch;
3. on mismatch/JBE, execute E and then the latch;
4. on mismatch/fall, stop at `0x1008E076` before block D;
5. after the latch, return either to `0x1008E05E` or `0x1008E0A9`.

This covers every call-free successor and removes the separate dispatcher
round-trip through the latch, without crossing an indirect call. It is larger
than A+B while remaining bounded to at most one guest write and one scan
iteration per invocation.

A first implementation should not loop over multiple entries inside one
transaction. A later read fault would occur architecturally after earlier
iteration writes, and arbitrary aliasing would require write-forwarding across
an unbounded read set. The single-iteration form has a finite plan and can
replay wholly from `0x1008E05E` on any failed preflight.

## Transactional write requirements

Before changing EAX, EDI, flags, EIP, `nextOp`, or guest memory, prepare all
reads required by the selected path and a writable direct-RAM plan for
`SS.base+EBP+8`. The write tier must:

- accept only resident directly writable RAM/COW state whose write semantics
  have already been materialized;
- buffer the final dword rather than publish it during speculation;
- revalidate read and write page identity/permission immediately before
  commit;
- leave all CPU and memory state unchanged on any failure;
- commit the guest dword in architectural order before final CPU state/EIP.

The buffered write `[SS:EBP+8,+0Bh]` can alias the later latch read
`[DS:ESI+264h,+267h]`. Exact behavior requires forwarding buffered bytes into
that read or rejecting overlap before commit and replaying in the interpreter.
Assuming stack and object memory never alias is not a reusable-tier contract.

## VERIFIED -- code guard anchors

The call-free regions can be guarded as exact byte arrays:

```text
1008E05E..1008E075 (24 bytes)
8B 86 54 02 00 00 8B 04 B8 3B 45 0C 75 05 FF 45
08 EB 2F 39 5D 08 76 27

1008E09D..1008E0A8 (12 bytes)
89 5D 08 47 3B BE 64 02 00 00 72 B5
```

Anchor the excluded call boundary so a changed successor is not absorbed:

```cpp
memory->readd(entry + 0x18u) == 0x8B0875FFu; // 1008E076
memory->readd(entry + 0x39u) == 0x014892FFu; // 1008E097 CALL
```

Retain relocation/module/`KMemory*` and containing-function guards from 220.
Hot exact-byte checks should use document 223's allocation-free resident-page
matcher, not repeated general `KMemory::readd` calls.

## Required native differential cases

- equal path with carry-state variation and counter wrap;
- mismatch with counter `<`, `==`, and `>` EBX;
- both latch successors after equal and reset paths;
- nonzero DS, SS, and CS bases;
- page-crossing reads and page-crossing `[EBP+8]` write;
- read-only, nonresident, COW-not-materialized, and remapped write pages;
- every ordered read fault with complete no-commit comparison;
- effective-address/scaled-index wrap side exits;
- write/latch-read exact and partial aliases;
- signature mutation in A, B, C, E, latch, and excluded call anchor.

Compare all GPRs, materialized flags and raw lazy state, EIP/`nextOp`, segments,
x87/SIMD/MXCSR, and all touched/sentinel memory against the interpreter.

## Evidence

- (로그 원본은 공개본에서 뺐다) — acknex_next_aot_candidates_ghidra_20260721
- `docs/research/219_GATE2C_MULTI_ENTRY_BROWSER_HOTNESS_GATE_20260721.md`
- `docs/research/220_GATE2C_8E0A0_STATIC_HOT_AOT_CONTRACT_20260721.md`
- `docs/research/223_GATE2C_MATERIAL_LATCH_FAST_GUARD_AND_NATIVE_MICROBENCH_20260721.md`
- direct PE `.text` extraction from the hash-fixed repository `acknex.dll`

## NOT VERIFIED

- Exact time share of `0x8E05E`; document 219's count is not a time percentage
  and document 218's 4.113% is only a function-family ceiling.
- A production guest-write tier or fused helper.
- Native differential behavior, browser equivalence, or FPS gain.
