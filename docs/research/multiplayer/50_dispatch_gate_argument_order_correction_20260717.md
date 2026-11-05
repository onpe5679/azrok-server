# Dispatch gate argument-order correction (2026-07-17)

This note supersedes the earlier interpretation that the state-1 dispatch
gate contains `gm+0x31822`.  The correction is based on the instruction-level
call sequence, not on a pointer pattern or a memory write.  No executable or
live process memory was modified.

## Exact call sequence

`FUN_00508B30` receives the outer GameManager as its implicit `this` and
copies the connection strings to:

```text
gm+0x31822  IP string buffer
gm+0x31842  port
gm+0x3179E  username
gm+0x317BE  auth key
```

Immediately before its call to the gate writer, the original instructions
are:

```text
00508DB5  LEA ECX,[gm+0x31822]
00508DBE  PUSH ECX                 ; following explicit argument: IP buffer
00508DBF  PUSH gm                  ; first explicit argument to 00594130
00508DC3  LEA ECX,[gm+0xE4A]
00508DCC  CALL 00508F40            ; returns gm+0x185A0 (embedded CLogic)
00508DD1  MOV ECX,EAX              ; FUN_00594130 this = CLogic
00508DD3  CALL 00594130
```

`FUN_00594130` stores its first explicit stack argument:

```text
00594139  MOV [EBP-0x4],ECX
0059413F  MOV ECX,[EBP+0x8]        ; first stack argument = gm
00594142  MOV [EAX+0x163D8],ECX    ; logic+0x163D8 = gm
```

The `RET 0x14` at `0x0059419B` confirms five explicit stack arguments.  The
IP buffer is the next argument (`[EBP+0x0C]`) used by the later auth/setup
checks; it is not the gate value.

## Runtime consequence

For a stack-scanned outer GameManager `gm`:

```text
logic = gm + 0x185A0
gate  = *(u32 *)(logic + 0x163D8) = gm
mode  = *(u32 *)(logic + 0x163E4)
```

The latest read-only PatHouse watch is consistent with this contract:

```text
gm            = 0x00163280
logic         = 0x0017B820
dispatch_gate = 0x00163280       (matches gm)
IP buffer     = 0x00194AA2       (gm+0x31822; separate diagnostic)
mode          = 0
```

The observer and `tools/read_dispatch_watches.py` now reverse-search the exact
`gm` value, expose `gate_matches_gm`, and retain the IP-buffer address only as
a non-authoritative diagnostic.  No code path writes either field.

## Files corrected

The active implementation and notes were aligned in:

* `azrok_server.py` (reverse-search target and runtime watch fields);
* `tools/read_dispatch_watches.py`;
* `docs/research/41_dispatch_gate_163d8_state1_prerequisite_20260717.md`;
* `docs/research/42_dispatch_gate_readonly_observer_20260717.md`;
* `docs/research/45_dispatch_pointer_semantics_recheck_20260717.md`;
* `docs/research/46_dispatch_vtable_owner_constructor_20260717.md`;
* `docs/research/47_cua_pthouse_input_probe_20260717.md`;
* `HANDOFF_2026-07-17_DYNAMIC_ANALYSIS.md` and its research README index.

Historical references to `gm+0x31822` as a *gate value* should be read as
superseded.  References that describe the connection IP string stored at that
offset remain valid.

