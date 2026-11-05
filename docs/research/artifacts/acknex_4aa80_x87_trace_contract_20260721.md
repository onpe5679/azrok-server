# Acknex `0x1004AA80` x87 outer-loop trace contract

This is a test/implementation contract for a future call-free trace AOT.  It
does not claim that the AOT exists.  All addresses below refer to the original
image base `0x10000000`.

## Evidence identity

- **VERIFIED:** all three project copies of `acknex.dll` have SHA-256
  `876f6870f6858c3829c0830415bf30cf7dd375590810eef231a7e6b1a68eedc6`.
- **VERIFIED:** the Ghidra range CSV assigns
  `0x4AA80..0x4AC29` to `FUN_1004a6d0`; the preceding range is
  `0x4A8D0..0x4AA7D` (exclusive end).
- **VERIFIED:** bytes `[0x4AA77,0x4ABE7)` are 368 bytes / 111 instructions,
  SHA-256 `3bfba3334febf57ea860227a45e18380d5bfd599f6940ff70411e63d540d9fc8`.
  They contain 85 memory instructions and 29 x87 instructions, with no
  `call`, `ret`, indirect branch, privileged instruction, or SIMD instruction.
- **VERIFIED:** bytes `[0x4AA80,0x4ABE7)` are 359 bytes / 108 instructions,
  SHA-256 `78211205d574cf0d5aea8302fd91d5cf049106ae619953a3229db591ec367615`.
- **VERIFIED:** document 201's profiler keys are 16-byte buckets.  They are
  evidence that this region is hot, not evidence for an exact entry EIP.

## Exact entries and exits

- **VERIFIED first-iteration entry:** `0x1004AA80`.  The preheader at
  `0x1004AA72` sets `ESI = EDI + 0x10`, then `0x1004AA75` jumps exactly to
  `0x1004AA80`.
- **VERIFIED later-iteration entry/backedge:** `0x1004AA77`.  The conditional
  backedge at `0x1004ABE1` targets it.  It reloads
  `EDI = [SS:ESP+0x24]` and jumps to `0x1004AA80`.
- **VERIFIED normal trace exit:** `EIP = 0x1004ABE7`, before executing the
  `mov ecx,[esp+0x1c]` at that address.  The final `jl` is not taken.
- Consequently, an implementation entered only at `0x1004AA77` misses the
  first outer iteration.  The useful whole-loop dispatcher entry is
  `0x1004AA80`; it must represent the internal backedge through
  `0x1004AA77`, rather than returning to the interpreter on every iteration.

## Exact disassembly of `[0x1004AA77,0x1004ABE7)`

```asm
1004AA77 mov  edi,[esp+24h]
1004AA7B jmp  1004AA80
1004AA7D lea  ecx,[ecx]
1004AA80 mov  edx,[eax+20h]
1004AA83 mov  ecx,[esp+28h]
1004AA87 mov  eax,[edi]
1004AA89 add  ecx,ebx
1004AA8B add  edx,[esp+20h]
1004AA8F mov  [ecx],eax
1004AA91 mov  eax,[esi-8]
1004AA94 mov  [ecx+4],eax
1004AA97 mov  eax,[esi-0Ch]
1004AA9A mov  [ecx+8],eax
1004AA9D mov  eax,[esi-4]
1004AAA0 mov  [ecx+0Ch],eax
1004AAA3 mov  eax,[esi+4]
1004AAA6 mov  [ecx+10h],eax
1004AAA9 mov  eax,[esi]
1004AAAB mov  [ecx+14h],eax
1004AAAE mov  edi,edi
1004AAB0 mov  edi,[esp+1Ch]
1004AAB4 fld  dword ptr [esp+14h]
1004AAB8 cmp  dword ptr [edi+54h],0
1004AABC fadd dword ptr [edx+18h]
1004AABF je   1004AAEC
1004AAC1 fmul dword ptr [edi+158h]
1004AAC7 fstp dword ptr [esp+30h]
1004AACB mov  eax,[esp+30h]
1004AACF fld  dword ptr [esp+10h]
1004AAD3 mov  [ecx+18h],eax
1004AAD6 mov  [ecx+20h],eax
1004AAD9 fadd dword ptr [edx+1Ch]
1004AADC fmul dword ptr [edi+158h]
1004AAE2 fstp dword ptr [esp+30h]
1004AAE6 mov  eax,[esp+30h]
1004AAEA jmp  1004AB09
1004AAEC fstp dword ptr [esp+30h]
1004AAF0 mov  eax,[esp+30h]
1004AAF4 fld  dword ptr [esp+10h]
1004AAF8 mov  [ecx+18h],eax
1004AAFB mov  [ecx+20h],eax
1004AAFE fadd dword ptr [edx+1Ch]
1004AB01 fstp dword ptr [esp+30h]
1004AB05 mov  eax,[esp+30h]
1004AB09 fld  dword ptr [101F5EC8h]
1004AB0F mov  [ecx+1Ch],eax
1004AB12 fld  dword ptr [esp+18h]
1004AB16 mov  [ecx+24h],eax
1004AB19 fucompp
1004AB1B fnstsw ax
1004AB1D test ah,44h
1004AB20 jnp  1004AB35
1004AB22 fld  dword ptr [esp+18h]
1004AB26 fmul dword ptr [ecx+18h]
1004AB29 fstp dword ptr [ecx+20h]
1004AB2C fld  dword ptr [esp+18h]
1004AB30 fmul dword ptr [ecx+1Ch]
1004AB33 jmp  1004AB58
1004AB35 cmp  dword ptr [edi+58h],0
1004AB39 je   1004AB5B
1004AB3B fld  dword ptr [esp+14h]
1004AB3F fadd dword ptr [edx+18h]
1004AB42 fmul dword ptr [edi+15Ch]
1004AB48 fstp dword ptr [ecx+20h]
1004AB4B fld  dword ptr [esp+10h]
1004AB4F fadd dword ptr [edx+1Ch]
1004AB52 fmul dword ptr [edi+15Ch]
1004AB58 fstp dword ptr [ecx+24h]
1004AB5B cmp  dword ptr [edx+28h],0
1004AB5F jl   1004ABBC
1004AB61 mov  edx,[edx+28h]
1004AB64 mov  edi,[esp+28h]
1004AB68 mov  eax,ecx
1004AB6A mov  ebp,[eax]
1004AB6C lea  ecx,[edx*8]
1004AB73 sub  ecx,edx
1004AB75 add  ecx,ecx
1004AB77 sub  ecx,edx
1004AB79 lea  ecx,[edi+ecx*4]
1004AB7C lea  edi,[edx+edx*2]
1004AB7F add  edi,edi
1004AB81 add  edi,edi
1004AB83 sub  edi,edx
1004AB85 mov  edx,[102FF4CCh]
1004AB8B mov  edx,[edx+20h]
1004AB8E lea  edx,[edx+edi*4]
1004AB91 mov  edi,ecx
1004AB93 mov  [edi],ebp
1004AB95 mov  ebp,[eax+4]
1004AB98 mov  [edi+4],ebp
1004AB9B mov  ebp,[eax+8]
1004AB9E mov  [edi+8],ebp
1004ABA1 mov  ebp,[eax+0Ch]
1004ABA4 mov  [edi+0Ch],ebp
1004ABA7 mov  ebp,[eax+10h]
1004ABAA mov  [edi+10h],ebp
1004ABAD mov  eax,[eax+14h]
1004ABB0 mov  ebp,[esp+34h]
1004ABB4 mov  [edi+14h],eax
1004ABB7 jmp  1004AAB0
1004ABBC mov  ecx,[esp+2Ch]
1004ABC0 mov  eax,2Ch
1004ABC5 add  [esp+20h],eax
1004ABC9 add  [esp+24h],eax
1004ABCD add  esi,eax
1004ABCF mov  eax,[102FF4CCh]
1004ABD4 add  ecx,1
1004ABD7 add  ebx,34h
1004ABDA cmp  ecx,[eax+28h]
1004ABDD mov  [esp+2Ch],ecx
1004ABE1 jl   1004AA77
```

## Data-flow contract

The names below describe observed layout only; they are not recovered source
types.

At the verified first entry `0x1004AA80`:

- `EAX = mesh`, where `[mesh+0x20]` is a 0x2c-stride auxiliary-record base and
  `[mesh+0x28]` is the outer record count.
- `EBX = 0`; `EDI = sourceBase`; `ESI = sourceBase+0x10`.
- `[SS:ESP+0x20] = 0`, `[SS:ESP+0x24] = sourceBase`,
  `[SS:ESP+0x28] = outputBase`, `[SS:ESP+0x2c] = 0`.
- `[SS:ESP+0x10]` and `+0x14` are float inputs; `+0x18` is a float comparison/
  multiplier input; `+0x1c` is a configuration pointer; `+0x34` is the saved
  vertex-buffer object pointer restored after the duplicate chain.
- `EBP = [SS:ESP+0x34]` on the real first entry.  `ECX`, `EDX`, and incoming
  integer flags are overwritten before they can affect the first iteration.
- `SS` must be applied to every stack operand.  The live game uses a flat
  stack, but the test must not bake that assumption into the helper.

Each outer iteration:

1. computes `dst = outputBase + outerIndex*0x34` and
   `aux = mesh->base20 + outerIndex*0x2c`;
2. copies six dwords from the 0x2c source record to destination offsets
   `0,4,8,0xc,0x10,0x14` in source-offset order `0,8,4,0xc,0x14,0x10`;
3. writes float results to destination offsets `0x18,0x20,0x1c,0x24`;
4. follows signed link `[aux+0x28]` while it is nonnegative.  A linked index
   `j` selects `outputBase+j*0x34` and `mesh->base20+j*0x2c`, copies the first
   six dwords from the current destination, and repeats the float stage.

There is **no bounds check** on a nonnegative link.  An AOT must not silently
assume `link < count`.  Cyclic links also remain cyclic in the original.

On normal completion before `0x1004ABE7`:

- `EAX` is the value freshly read from absolute `[0x102FF4CC]` on the last
  outer iteration; `ECX` is the completed outer count; `EBX = count*0x34`;
- `ESI = originalSourceBase+0x10+count*0x2c`;
- `[ESP+0x20]` and `[ESP+0x24]` advanced by `count*0x2c`, and
  `[ESP+0x2c] = count`;
- `EBP = [ESP+0x34]`; `EDI = [ESP+0x1c]`; `EDX` points at the final auxiliary
  record whose link was negative;
- EFLAGS are exactly those produced by the final
  `cmp ecx,[eax+0x28]`.  The intervening `mov [esp+0x2c],ecx` and the not-taken
  `jl` do not alter them.

## x87 contract

- **VERIFIED:** every control-flow path from `0x1004AA80` to the outer-loop
  latch has balanced pushes/pops.  The net x87 TOP and pre-existing logical
  register stack are unchanged on normal completion.
- **VERIFIED:** balanced depth alone is insufficient.  `fucompp` updates x87
  C0/C2/C3; `fnstsw ax` exposes the complete status word to integer code; and
  `test ah,0x44` selects a branch.  NaN/unordered cases therefore belong in
  the oracle.
- **VERIFIED in current BoxedWine source:** `FUCOM` currently delegates to
  `FCOM`; the FPU may use cached host `double` when `KSystem::useF64` is true,
  otherwise SoftFloat ext80.  The cached-double `FST_F32` path uses a host
  `(float)` conversion, while the SoftFloat path explicitly selects
  `getSoftRounding()`.  The AOT oracle is current NormalCPU behavior in the
  selected mode, not an assumed JavaScript `double` formula and not a generic
  claim of hardware-x87 exactness.
- Snapshot/compare `cw`, `sw` (after `SW()` materializes TOP), `top`, `round`,
  all tags, all `isRegCached` bits, all nine ext80 registers and cached-double
  bit patterns.  Also compare `isMMXInUse` and GPR EAX because of `fnstsw ax`.

## Memory, alias, and fault contract

- **VERIFIED:** reads and writes are interleaved.  In particular, the first six
  destination dwords are written before configuration and x87 reads, and each
  linked destination is partially copied before its float stage.
- **VERIFIED:** `[0x102FF4CC]`, `[ESP+0x1c]`, and stack locals are deliberately
  re-read inside loops.  Hoisting them changes fault/concurrent-observation and
  alias behavior.
- Therefore bulk input snapshots or prewalking the link chain are not exact.
  A fast path may use pointer-range no-alias and mapped-page guards, but any
  rejected case must continue in NormalCPU from the original EIP and original
  state.  The guard itself must not write guest state.
- If an access faults after partial writes, architectural state must identify
  the exact faulting x86 EIP and retain preceding writes/GPR/x87 effects.  A
  raw WebAssembly trap after an all-or-nothing helper is not equivalent.

## Differential fixture design (no production edit required yet)

Extend the pattern already used by `source/test/cpu/testHotAOT.cpp`:

1. Map hot and reference code pages, absolute-global pages
   `0x101F5000` and `0x102FF000`, a flat stack, source, output, mesh/aux and
   configuration pages.  Put identical 368-byte code at the hot entry and a
   non-special reference entry.  Relative internal branches remain valid in
   the relocated reference copy; absolute operands intentionally keep pointing
   to the mapped original-global pages.
2. Start both CPUs at the exact first entry (`AA80` equivalent), stop before
   the equivalent exclusive end (`ABE7`), and cap only the **test harness** to
   detect accidental link cycles.  A production helper may not invent a cap.
3. Compare all GPRs, materialized flags/lazy-flag state, EIP, complete x87 state,
   XMM/MMX state, stack scratch/locals, destination/source/mesh/config/global
   memory, and dispatch count separately.  XMM should be unchanged.
4. If a future helper rejects an alias, MXCSR/x87 mode, page, or link case,
   assert that rejection is side-effect-free, then run the interpreter and
   compare with the reference result.

Required cases:

- one and several outer records, all links `-1`;
- each `config+0x54` / `config+0x58` combination and both comparison branches;
- zero, negative zero, denormal, infinities, quiet/signalling NaNs, and values
  around the `[0x101F5EC8]` comparison constant;
- x87 rounding modes and initial logical depths 0, 1, 3, and 6 (maximum
  transient depth is +2), with nondefault TOP/tags;
- one-link and multi-link chains, repeated target, backward target, and a
  mapped nonnegative out-of-count target;
- destination/source overlap, destination/aux overlap, destination/config
  overlap, destination/stack-local overlap, and output records overlapping
  each other through chosen bases;
- segmented `SS` versus flat `SS`;
- guard-rejection tests for a cyclic link and invalid/missing pages;
- fault injection at representative first-copy load/store, config load, x87
  load/store, absolute-global reload, linked-copy load/store, and final count
  load, comparing exact EIP and partial state where the test framework can
  catch the guest fault.

## Status

- **VERIFIED:** binary identity, exact instruction boundaries, CFG, instruction
  counts, data-flow formulas, balanced x87 depth, and the visible
  `fucompp/fnstsw/test` dependency.
- **INFERRED:** semantic names such as `mesh`, `source`, `output`, and
  `configuration`; they are layout labels only.
- **NOT VERIFIED:** a trace-AOT implementation, its differential fixture, and
  any performance gain.  These remain gated on the tests above.
