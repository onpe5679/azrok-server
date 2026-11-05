# State-1 dispatch gate `+0x163D8` and the remote-roster prerequisite (2026-07-17)

> **Superseded address correction (2026-07-17):** the dispatcher `this` is the
> embedded `CLogicManager`, not the CGameManager base. `find_real_gm()` returns
> the CGameManager at `gm`; derive `logic = gm+0xE4A+0x17756 = gm+0x185A0`, then
> read `logic+0x163D8/+0x163E4` (absolute `gm+0x2E978/+0x2E984`). The older
> direct-`gm` offsets in this historical note are retained only to explain the
> original trace and must not drive a new runtime probe. See research note 46.

## Scope

This note records a read-only Ghidra MCP re-check prompted by the two-client
roster experiment in `docs/research/40_two_client_roster_wire_vs_client_state_20260717.md`.
The server emitted direction-correct `S->C 0x0065/0x0066/0x0068` records,
but the PatHouse primary produced zero hits at the state-1 roster handlers.
No client-memory write, packet replay, or live input was used for this pass.

## Direct dispatch evidence

`DispatchInbound_ByClientMode @ 0x00594310` has two independent fields on its
GameManager `this` object:

| Field | Meaning supported by the function | Evidence |
|---|---|---|
| `this+0x163E4` | dispatch mode (`0`, `1`, or `2`) | mode switch at `0x00594310` |
| `this+0x163D8` | non-null dispatch/logic owner gate | branch `CMP [this+0x163D8],0` at `0x00594447` |

The function first runs the mode-specific pre-handler. It then executes the
normal common/state handler only when `*(this+0x163D8) != 0`:

```text
if (dispatch_gate != 0) {
    switch (dispatch_mode) {
      case 0: DispatchState0Common_S2C(...);
      case 1: State1PreDispatch(...); DispatchState1_S2C(...);
      case 2: virtual_dispatch(...);
    }
}
```

For mode `1`, `DispatchState1_S2C @ 0x00613740` is a direct opcode switch:

```text
0x0064 -> 0x00615650
0x0065 -> 0x00615B20
0x0066 -> 0x00615B50
0x0068 -> 0x00615D50
0x0069 -> 0x00615E70
...
```

It has no additional roster-specific ready-state test. Therefore a zero-hit at
all of `0x00615B20/0x00615B50/0x00615D50` is explained by the outer gate (or by
the client not reaching this dispatch function), not by an incorrect `0x0066`
record field map.

## `0x0064` changes mode, but does not create the gate

The top of `DispatchInbound_ByClientMode` has a special case for opcode
`100` (`0x0064`) that calls `FUN_00594100(1)`. The function body is only:

```c
*(this + 0x163E4) = 1;
```

This is a mode transition, not a write to `+0x163D8`. The later state-1
dispatch block still requires the separate non-zero gate. Consequently,
"we sent `0x0064`" and "the state-1 dispatcher is active" are not equivalent
claims.

`HandleS2C_0064_ApplyAuthoritativeSelf @ 0x00615650` is itself reached through
the same gated block. It creates/updates the authoritative self actor and
stores the actor id via `FUN_00615AF0`, but it cannot justify sending more
`0x0064` packets while the gate is unproven.

## Authoritative gate writer

Ghidra scalar-reference search found one real writer body for the field:
`FUN_00594130 @ 0x00594130`. Its startup caller sets ECX to the embedded
CLogic owner and pushes the outer GameManager as the first explicit stack
argument (`param_2`); the IP-string buffer (`gm+0x31822`) is the following
argument. The gate is therefore expected to contain `gm`, not the IP-buffer
address.

Instruction-level evidence:

```text
00594139  MOV [EBP-0x4],ECX             ; logic/dispatch object (this)
0059413C  MOV EAX,[EBP-0x4]
0059413F  MOV ECX,[EBP+0x8]              ; GameManager argument
00594142  MOV [EAX+0x163D8],ECX          ; gate = outer GameManager pointer (gm)
00594148  ...                            ; auth/setup work
0059419B  RET 0x14                       ; five stack arguments
```

The decompiler displayed one phantom sixth parameter; the disassembly's
`RET 0x14` is the authoritative calling-convention evidence. The first write
occurs before the later validation/notification calls, so a breakpoint at
`0x00594142` is a clean initialization boundary.

The normal construction path is visible in `FUN_00508B30`:

1. It initializes the GameManager UI/root objects and controller chain.
2. At `0x00508DC3..0x00508DD3`, it obtains the embedded logic owner
   `logic = gm+0x185A0` and calls the `FUN_00594130` thunk with that `this`;
   the gate is written at `logic+0x163D8` (absolute `gm+0x2E978`) with value
   `gm`.
3. The call is reached through `FUN_004EDB10` and its thunk, which passes
   startup values from engine-global bootstrap records.

The direct implication is fail-closed: a fresh client that never executes the
`FUN_00594130` write has no evidence that state-1 inbound dispatch can run.
If the write executes but `logic+0x163D8` later becomes zero, the next target is
the clobber/destructor path, not a new packet layout.

## Remote actor path after the gate

Once `DispatchState1_S2C` is actually reached, the actor path is deterministic:

- `0x0065` -> `FUN_00615B20` -> `FUN_0050D5D0` (flush/finalize list).
- `0x0066` -> `FUN_00615B50`, which loops over `payload_len / 0x1A` and calls
  `FUN_0050D790(record, 1)`.
- `FUN_0050D790` first compares the record actor id (`record+1`) with the
  authoritative self id (`FUN_0050D8E0`). Equal ids return `0` and are ignored.
  A non-self id allocates a free slot (`FUN_0050D690`), initializes it through
  `FUN_005243E0`, appends it (`FUN_0050C700`), and finalizes visual state.
- `0x0068` -> `FUN_00615D50`; it ignores self ids and updates only an existing
  non-self actor found by `FUN_0050E560`.

This confirms why the already-proven server roster record should not be
rewritten first. A correctly serialized non-self record is inert if the
recipient never enters the gated state-1 dispatch path.

## Interpretation of the 40-trace state sample

`FUN_00508B30` is called during the normal `FUN_004ECAB0` WinMain startup and
its `FUN_00594130` call writes the CLogicManager `logic+0x163D8` owner pointer.
Therefore a normally initialized client is expected to have this pointer
non-zero. The `logic state=0` value recorded in the roster trace must not be
silently relabeled as that pointer gate: it may instead be the separate mode
field `+0x163E4 == 0` (still on the state-0 dispatcher). Existing runtime notes
also use `gm+0x31946` for a different room/readiness latch. A fresh dynamic
sample must record all three fields separately before choosing a repair path:

```text
logic = GameManager +0x185A0
logic +0x163D8               (dispatch owner pointer; absolute gm+0x2E978)
logic +0x163E4               (dispatcher mode; absolute gm+0x2E984)
GameManager       +0x31946   (room/readiness latch)
```

## Safe next dynamic observation (read-only)

On a fresh clean client, with no injected packets or UI input:

1. Arm x32dbg breakpoints at `0x00508B30` (startup path) and
   `0x00594142` (the exact gate write).
2. At `0x00594142`, record `ECX` (logic/dispatch object) and `[EBP+8]`
   (GameManager argument). Resume normally.
3. After startup, derive `logic = gm+0x185A0` and read (without writing)
    `logic+0x163D8` and `logic+0x163E4`. The normal writer passes the outer `gm`
    pointer as the gate value; only after a real `0x0064` transition
   should `logic+0x163E4 == 1`.
4. If needed, break at `0x00594447` and record the gate value used by the
   outer branch, then at `0x00594457` record the mode selected for that
   inbound packet. This distinguishes a missing writer, a later clobber, and
   a packet arriving before mode/gate initialization.
5. Only after a non-zero gate and mode `1` are observed should the existing
   two-client roster wire test be repeated. Success requires both a handler hit
   and a remote-actor lifecycle hit, not merely TCP emission or a control-panel
   roster card.

**Do not fire speculative `S->C 0x0064` or `S->C 0x0066` packets to make the
gate/state.** The static contract says `0x0064` changes `+0x163E4` only, and
`0x0066` is consumed only after the state-1 gate is live. More packets before
the read-only preflight would contaminate the exact boundary we need to
measure.

## Evidence files

- Server/wire and zero-handler result:
  `docs/research/40_two_client_roster_wire_vs_client_state_20260717.md`
- Raw observer:
  `artifacts/dynamic-analysis/x32dbg_roster_pid134448_20260717_104151.jsonl`
- Ghidra MCP script used for scalar references:
  `<home>\ghidra_scripts\FindDispatchGateWriters.java`
- Ghidra MCP script used for function callers:
  `<home>\ghidra_scripts\XrefsToAddrIter.java`
