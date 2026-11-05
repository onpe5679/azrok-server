> **ARCHIVED (2026-07-17).** 이 문서는 대체됨 — 현재 확정 사실은 ../INDEX.md 참조.

# Read-only dispatch-gate observer (`+0x163D8` / `+0x163E4`) (2026-07-17)

> **Address correction (2026-07-17):** the historical labels below use
> `gm+0x163D8/+0x163E4` as shorthand. The live dispatcher is the embedded
> `CLogicManager` at `logic = gm+0xE4A+0x17756 = gm+0x185A0`; its fields are
> `gm+0x2E978/+0x2E984`. The startup gate value is the outer `gm` pointer;
> `gm+0x31822` is the separate IP-buffer argument. Use research note 46 for
> the corrected owner derivation and argument order.

## Purpose

This is a clean-run preflight for the state-1 inbound dispatcher. It measures
the owner gate (`logic+0x163D8`) separately from the dispatcher mode
(`logic+0x163E4`) and records the exact startup writer and outer branch.
It intentionally does not attempt to make the roster path work.

The observer is implemented as the `gate` profile of
`tools/x32dbg_plaza_interaction_trace.py`.

## Checkpoints

| Address | Label | Read-only evidence |
|---:|---|---|
| `0x00508B30` | `client_peer_startup_initializer` | startup `this` and both fields |
| `0x00594142` | `dispatch_gate_write_pre` | exact `MOV [EAX+0x163D8],ECX` before write; logic and GameManager pointers |
| `0x00594148` | `dispatch_gate_write_post` | first instruction after the write; gate value after write |
| `0x00594310` | `dispatch_inbound_entry` | dispatcher `this`, gate, and mode at entry |
| `0x00594447` | `dispatch_gate_cmp` | operand of `CMP [this+0x163D8],0` |
| `0x00594454` | `dispatch_gate_nonzero_path` | fall-through after `JE 0x005944E0`; proves non-zero branch |
| `0x00594457` | `dispatch_mode_load` | direct read of `+0x163E4` before load |
| `0x0059445D` | `dispatch_mode_latched` | mode copied into `ECX` after the load |

The profile excludes packet senders, `0x0064/0x0066/0x000D` handlers, UI hit
tests, transition resolver polling, and all input/memory-write helpers.  It
does not issue a server request or inject any client input.  x32dbg software
breakpoints are used only to observe execution and are removed on detach.

The runner now fails closed before `attach_session` when the elevated x32dbg
process has no `%TEMP%\xauto_session.<pid>.lock`.  This prevents the known
`attach_session` IPC hang from being mistaken for a game failure or from
destabilizing the target process.

## Safe command

Attach the elevated x32dbg session to a fresh, responding primary PID, then
run:

```powershell
python tools\x32dbg_plaza_interaction_trace.py `
  --session-pid <elevated-x32dbg-pid> `
  --profile gate `
  --log artifacts\dynamic-analysis\x32dbg_gate_<pid>_<timestamp>.jsonl `
  --ready-file artifacts\dynamic-analysis\x32dbg_gate_<pid>_<timestamp>.ready `
  --timeout 180
```

Wait for JSONL events `breakpoints_ready` (`profile=gate`) and `running` before
resuming ordinary startup.  Do not send a macro, packet, click, or keyboard
event in this observation window.  Let the observer time out/detach, then
inspect the target process normally.

## Interpretation

The expected clean-start sequence is:

1. `0x00594142`/`0x00594148` pair with `gate_after` equal to the outer
   CGameManager pointer (`gm`), or at minimum a non-null readable pointer.
2. `0x00594310` and `0x00594447` showing the same non-null gate.
3. `0x00594454` showing the non-zero gate fall-through when inbound traffic
   arrives naturally.
4. `0x00594457`/`0x0059445D` reporting mode `0` during initial state; mode `1`
   is expected only after a real client transition, not from this observer.

If the writer is absent, the startup/controller construction path is broken.
If the writer occurs but a later `dispatch_gate_cmp` reads zero, investigate a
destructor/clobber path.  If the gate is non-zero but mode remains `0`, that is
an independent mode-transition finding.  A zero handler count without this
preflight is not evidence that the roster record layout is wrong.

## Evidence contract

This observer is a measurement boundary only.  It must not be used to justify
sending speculative `S->C 0x0064` or `S->C 0x0066` packets.  Repeat the roster
wire/handler test only after this clean run records a non-zero gate and the
actual mode transition has been observed through a natural client action.
