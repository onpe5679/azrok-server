# Dispatch vtable and state-1 owner constructor (2026-07-17)

This note records a fresh read-only Ghidra headless re-check of the inbound
dispatcher.  No executable bytes or process memory were changed.

Follow-up correction: the embedded object's pre-promotion vtable is
`0x006A6154` (`CLogicJSDB`).  A later instruction-level argument audit fixes
the gate value: the call to `FUN_00594130` sets ECX to the embedded CLogic
owner, then pushes the outer `gm` as the first stack argument.  Therefore the
gate write is `logic+0x163D8 = gm`; `gm+0x31822` is the IP-string argument,
not the gate value.  The live observer tracks both vtables and compares the
CLogic gate against `gm`.

Evidence files:

- `ghidra_temp/dispatch_vtable_inspect_20260717.log`
- `ghidra_temp/dispatch_owner_constructor_decompile_20260717.log`
- `ghidra_temp/dispatch_owner_constructor_disasm_20260717.log`
- `ghidra_temp/dispatch_owner_helpers_20260717.log`
- `ghidra_temp/dispatch_gm_ctor_disasm_20260717.log`
- `ghidra_temp/dispatch_startup_disasm_20260717.log`
- `ghidra_temp/dispatch_call_thunks_20260717.log`

## 1. `0x006A6198` is a vtable slot, not the vtable address

The `.rdata` symbols and raw table at `0x006A6188` are:

```text
0x006A6188  vftable_meta_ptr = 0x006C1BB0
0x006A618C  CLogicManager::vftable (table base)
  +0x00    0x004E0E02
  +0x04    0x004D8EDC
  +0x08    0x004E190B
  +0x0C    0x004D8720  -> thunk to DispatchInbound_ByClientMode
  +0x10    0x00000000
  +0x14    0x006C1C10
  +0x18    0x004D7FB4
  ...
```

Ghidra reports a data xref from `0x00593F6D` to the table base
`0x006A618C`.  It reports a data xref from `0x006A6198` to the function
thunk `0x004D8720`.  Therefore the previous runtime constant
`DISPATCH_OWNER_VTABLE = 0x006A6198` was off by one vtable slot.  A live scan
that searches for object vptr `0x006A6198` is expected to return zero hits;
the object vptr to validate is `0x006A618C`.

The nearby table at `0x006A61A4` is a different `CJSCommand::vftable` (its
constructor xrefs are `0x0059488D` and `0x00594BEF`) and is not the dispatch
owner.

## 2. Constructor and subobject offset

`FUN_00507DF0` is the `CGameManager` constructor and creates `CGame` at
`gm + 0xE4A`.  `FUN_0052F900` is the `CGame` constructor.  Its decompile
writes `CGame::vftable` to that embedded object, then initializes child
objects.  The instruction-level call to the logic-manager constructor is:

```text
0x0052F9A9  MOV ECX,[EBP-0x10]
0x0052F9AC  ADD ECX,0x17756
0x0052F9B2  CALL 0x004DF90D       ; thunk_FUN_00593F30
```

`FUN_00593F30` is the `CLogicManager` constructor.  Its first operation is:

```c
*param_1 = CLogicManager::vftable;  // 0x006A618C
```

It then initializes the logic-manager child systems and calls
`FUN_0059D050`, `FUN_005AB650`, and `FUN_005ABD00` before returning.  Thus the
object whose vtable contains `DispatchInbound_ByClientMode` is the
`CLogicManager` subobject at `CGame + 0x17756` (absolute
`CGameManager + 0x185A0`), not the `CGame` base itself.

The helper decompilation shows `FUN_0059CE80` constructing a nested
`CJSLogic` child and zeroing its local state.  Neither the constructor body nor
the examined child helpers writes `+0x163D8` or `+0x163E4`; those fields are
written later by the connection/mode routines below.

For a stack-scanned `CGameManager` candidate `gm`, the dispatcher fields are
therefore at these absolute offsets from the outer object:

```text
logic = gm + 0xE4A + 0x17756 = gm + 0x185A0
logic + 0x163D8 (gate) = gm + 0x2E978
logic + 0x163E4 (mode) = gm + 0x2E984
```

These packed, unaligned offsets are a consequence of the original object
layout; they are not evidence of a second independent GameManager.

## 3. Dispatcher field writers and call contract

`DispatchInbound_ByClientMode @ 0x00594310` is the method at vtable slot
`+0x0C` and reads both fields from its `this` pointer:

```c
mode = *(int *)(this + 0x163E4);
if (*(int *)(this + 0x163D8) != 0) {
    // state-specific common dispatch, including state 1
}
```

The two direct writers remain:

```c
FUN_00594100(this, mode)  -> *(u32 *)(this + 0x163E4) = mode;
FUN_00594130(this, gate)  -> *(u32 *)(this + 0x163D8) = gate;
```

`0x0064` invokes `FUN_00594100(1)` and changes the mode only.  It does not
construct the logic-manager object and it does not write the gate.  The
constructor path above runs during ordinary `CGameManager`/`CGame`
construction before room transitions; any later gate value must come from the
connection/setup path that calls `FUN_00594130` on this same `CLogicManager`
subobject.

The startup call contract is explicit in the disassembly. `FUN_004ECAB0`
passes its large stack `CGameManager` object to `FUN_004EDB10`; the latter
loads that value into `ECX` and calls `FUN_00508B30`. Inside
`FUN_00508B30`, the IP string is copied to `gm + 0x31822`.  Before calling
`FUN_00594130`, the function sets `ECX = gm + 0xE4A`, calls
`FUN_00508F40` (which adds `0x17756`), moves that result into ECX as the
embedded CLogic `this`, and pushes `gm` as the first explicit stack argument.
`FUN_00594130` then stores `[EBP+0x08]` into `[this+0x163D8]`, so the gate
value is `gm`, while `gm+0x31822` remains the startup IP-buffer argument used
by the later connection/auth checks.

`FUN_00591CD0` (`OnConnect`) writes a separate `+0x4076` flag and must not be
mistaken for the `+0x163D8` dispatcher gate.

## 4. Dynamic probe correction

The next read-only runtime probe should:

1. keep the existing `CGameManager` candidate scan;
2. derive `logic = gm + 0xE4A + 0x17756 = gm + 0x185A0`;
3. read either `0x006A6154` (`CLogicJSDB`, pre-promotion) or `0x006A618C`
   (`CLogicManager`, state-1 dispatcher) before classifying the child;
4. read `logic+0x163D8` and `logic+0x163E4` and scan for the exact gate writer
   target `gm` (the IP-buffer address `gm+0x31822` is a separate diagnostic).

Until that vptr check is present in a live capture, the old direct `gm` reads
and the `0x006A6198` vptr scan are not valid evidence about state-1 readiness.
