> **ARCHIVED (2026-07-17).** 이 문서는 대체됨 — 현재 확정 사실은 ../INDEX.md 참조.

# Dispatch pointer semantics recheck (2026-07-17)

> **Call-site correction (2026-07-17):** the initial decompiler rendering
> omitted the thunk's adjusted `this` *and* shifted the explicit arguments.
> `FUN_00508B30` is entered with the outer CGameManager as `this`; inside it,
> `ECX` is changed to `logic = gm+0x185A0` before the call to
> `FUN_00594130`, and the outer `gm` is pushed as that call's first explicit
> stack argument. Therefore the gate field is `logic+0x163D8` (absolute
> `gm+0x2E978`) and the stored gate value is `gm`. The IP buffer
> `gm+0x31822` is the following argument used by connection/auth checks, not
> the gate value. See research note 46 and the disassembly evidence listed
> there.

## Ghidra headless evidence

Fresh decompilation through the local Ghidra headless endpoint (`127.0.0.1:8193`)
was saved as `ghidra_temp/dispatch_owner_recheck_20260717.json`.

`FUN_00508B30` does use the CGameManager as its outer `this` (`param_1`), and its network
strings are stored at `gm+0x31822`, `gm+0x31842`, `gm+0x3179e`, and
`gm+0x317be`. However, the call arguments to `FUN_00594130` are decisive:

```c
// call-site thunk: ECX becomes logic = local_18 + 0xE4A + 0x17756
// stack order: first explicit arg is the outer gm, then the IP buffer
thunk_FUN_00594130(logic, local_18, local_18 + 0x31822,
                   uVar2, iVar6, iVar5);
```

`FUN_00594130` then performs:

```c
*(undefined4 *)(param_1 + 0x163d8) = param_2;
```

Therefore the field location is `logic+0x163D8` (absolute `gm+0x2E978`) and
its expected value is the outer GameManager pointer `gm`. The IP-buffer pointer
(`gm+0x31822`) is a separate startup string argument. The earlier note that
the gate should equal the IP buffer was an incorrect argument-order
interpretation.

`DispatchInbound_ByClientMode @ 0x00594310` reads both fields from the same
embedded CLogicManager `param_1` object:

```c
mode = *(int *)(param_1 + 0x163E4);
if (*(int *)(param_1 + 0x163D8) != 0) {
    ... state-1 common + roster dispatch ...
}
```

This explains why the dispatcher-owner read must derive `logic = gm+0x185A0`
from the outer GameManager, while preserving the distinction between field
address and expected gate value.

## Call-chain qualification

Fresh Ghidra decompilation of `FUN_004EDB10` shows the startup call as:

```c
thunk_FUN_00508b30(
  *(undefined4 *)(*(int *)(DAT_006e8430 + 0x9a0) + 0xc),
  *(undefined4 *)(*(int *)(DAT_006e8430 + 0x998) + 0xc),
  *(undefined4 *)(*(int *)(DAT_006e8430 + 0x9ac) + 0xc),
  0);
```

`DAT_006e8430` is a global pointer value in that expression, not the literal
image address of an inline structure.  The runtime chain is therefore
`engine_root = *(u32 *)0x006E8430`, then
`owner_9A0 = *(u32 *)(engine_root + 0x9A0)`, and finally
`ip_string = *(u32 *)(owner_9A0 + 0x0C)` (with the analogous `0x998`
and `0x9AC` string branches for the other startup arguments).  Reading
`0x006E8430+0x9A0` directly can yield a plausible heap pointer whose `+0x0C`
is only a small scalar.  The three resulting pointers are explicit string
arguments; the GameManager `this` for `FUN_00508B30` is implicit in the
__thiscall and must not be inferred from these strings.

The control panel exposes this corrected chain as a read-only
`dispatch_owner_chain` diagnostic so a live run can record the WDL string
pointer/value alongside the separately stack-scanned `gm`.  The dispatch
owner remains unproven until a direct object/vtable and gate/mode observation
matches the static writer.

### Live chain caveat

The first post-restart probe returned `ip_string=0x3ED00010` and first DWORD
`0x2E373231`.  In little-endian byte order this is `31 32 37 2E`, i.e. the
ASCII prefix `127.`.  This confirms that the current `+0x0C` slot is an
IP-string buffer, not an object vtable.  The chain is useful as a
startup/configuration pointer probe; it must not be labelled as the live
state-1 owner.

The decompilation was saved as
`ghidra_temp/dispatch_callchain_recheck_20260717.json`.

## Live pointer qualification and reverse search

The corrected WDL-pointer walk produced this live sample in the
PatHouse/bootstrap state:

```text
engine_root          = 0x102749E8
engine_root+0x9A0    = 0x0DB091A0
(...+0x0C)             = 0x3ED00010
first DWORD there    = 0x2E373231  (bytes "127.")
```

The final value is therefore an IP-string buffer (or a containing network
record whose first bytes are the IP), not a C++ dispatch vtable.  Its
`+0x163D8/+0x163E4` reads are retained as diagnostics only and are not being
called the owner.  The direct startup chain is still useful for identifying
the connection record, but the dispatch owner must be proven separately.

The control panel now performs two read-only searches (the constructor/vtable
correction is superseded by research note 46):

1. It scans committed readable pages for the exact writer target
   `gm` against the CLogic owner (where `logic = gm + 0xE4A +
   0x17756 = gm + 0x185A0`)
   and, for each hit, validates
   `candidate_base + 0x163E4` (mode 0/1/2) and the dispatch vtable.
2. It independently scans for the inbound-dispatch vtable `0x006A618C` and
   reports each object's current gate and mode, even when the gate is zero.

The first live scan found no hits for the prior owner assumptions; the
corrected probe derives the owner from `logic = gm+0x185A0` (`gm+0xE4A+0x17756`), compares its gate
against `gm`, and accepts both pre- and post-promotion
vtable values.  No memory write,
binary patch, or inferred owner promotion is used by these probes.

## Live implication

The latest clean runtime read was:

```text
gm                  = 0x00163280
logic = gm+0x185A0
logic+0x163D8 gate  = (not captured in this historical sample)
logic+0x163E4 mode  = (not captured in this historical sample)
```

The old direct-base values were not a valid state-1 pair and are not evidence
about the embedded dispatch owner. The Plaza screen is real; the next dynamic
question is whether the startup call to `FUN_00594130` is skipped or a later
path clears the embedded IP-pointer gate. No gate/mode memory write is
authorized by this evidence.
