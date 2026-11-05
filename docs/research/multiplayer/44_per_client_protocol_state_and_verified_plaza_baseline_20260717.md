# Per-client protocol state and verified Plaza baseline (2026-07-17)

## Scope

This note records two corrections needed before a reused local server can be
used for multiplayer testing:

1. `AZROK_PLAZA_REPLY_MODE=0064` is the supported Plaza baseline. The older
   `both` recipe (`S->C 0x0064` plus `S->C 0x006E`) is a diagnostic OX path and
   is not a Plaza proof.
2. The server must not share login/calibration/room-transition flags between
   socket threads. A second client on the same server must start from a clean
   bootstrap state.

## Verified single-client baseline

Clean capture `captures/packets_20260717_114536.txt` records:

```text
C->S 0x0064 [01]
S->C 0x0064 (27 bytes)
no S->C 0x006E
```

The corresponding runtime observation was `scene=110`, `phase=4`,
`self_actor_id=1`, and a visible outdoor Plaza. Screenshot:
`artifacts/screens/clean_primary_plaza_0064only.bmp`.

This supersedes the historical `both`-mode OX result. No new room-selector
search is required for the supported Plaza path.

## Server isolation change

`azrok_server.py` now creates a fresh `proto_state` dictionary for each
accepted connection. The packet handler enters `_client_protocol_context()`
under `proto_lock`, temporarily binds the recovered response builders to that
connection's state, and restores the previous reference afterward. This keeps
the existing packet contracts unchanged while isolating:

- character-created/name/type metadata;
- 0x0005/0x0007 bootstrap counters;
- calibration and Hansol transition flags;
- natural C->S 0x0064 handling and Plaza reply counters.

`azrok_launcher.py` also keeps the primary server/control host alive after the
primary game exits whenever a reused-server client is still connected. Without
this owner-lifetime rule, the primary launcher's `finally` block closed the
shared listener and killed the secondary's test halfway through its transition.

The control-panel active target uses the selected connection's state for
manual macros and state display. The per-client dictionary is excluded from
the JSON roster so raw bytes are never exposed as invalid JSON.

## Dispatch-owner observation correction

Historical note (superseded by research note 46): this earlier separate-owner
interpretation was wrong. The authoritative dispatch object is now proven to
be the embedded CLogicManager at `logic = gm+0x185A0` (`gm+0xE4A+0x17756`);
its gate/mode fields are `logic+0x163D8` and `logic+0x163E4` (absolute
`gm+0x2E978` and `gm+0x2E984`). The WDL network fields remain at the outer object's
`gm+0x3179e`, `gm+0x317BE`, `gm+0x31822`, and `gm+0x31842`.

```text
logic = gm + 0x185A0
dispatch_gate = read32(logic + 0x163D8)
dispatch_mode = read32(logic + 0x163E4)
```

No separate pointer scan or speculative packet is needed. The next clean Plaza
run must record these two values before attempting the roster.

## Next verification

1. Restart the server from the updated file.
2. Launch primary and reuse-server secondary independently.
3. Bring both clients through the already verified default `0064-only` Plaza
   path.
4. Confirm each capture has natural `C->S 0x0064` followed by exactly one
   authoritative `S->C 0x0064`, with no `0x006E`.
5. Confirm the server emits direction-correct `S->C 0x0065/0x0066/0x0068`
   roster records only after each client has completed its own bootstrap.
6. Confirm remote-actor handler hits or visible remote avatars; wire emission
   alone is not a completed multiplayer result.

## Direct GameManager watch result (latest clean run)

The historical direct-base probe (before note 46's owner derivation) reported
the following and is retained as a negative result only:

```text
gm                  = 0x00163280
gm+0x163D8 gate     = 0x00000000
gm+0x163E4 mode     = 0x90000000
```

The screen still reaches the verified Plaza state (`scene=110`, `phase=4`,
`self_actor_id=1`), but the two dispatch fields are not a valid state-1 pair:
the outer gate is closed and the mode word is not `0/1/2`. This is a useful
negative result, not a roster failure: it means the next dynamic/static pass
must determine whether `FUN_00594130` never executes for this startup or a
later lifecycle path clobbers these fields. No memory write or speculative
`0x0064/0x0066` packet is justified by this observation.

## Intermediate two-client evidence

`captures/packets_20260717_115737.txt` already proves the isolated bootstrap
boundary: two client hellos and two full C2S `0x0007` packets are present, and
the server emitted direction-correct `S->C 0x0065/0x0066/0x0068` records for the
local PatHouse group. Only the primary reached Plaza in that run. The
secondary remained at character selection because the elevated one-shot UI
request was overwritten by a second request before the scheduled task consumed
the first one. That was an orchestration race, not a protocol failure; the
next run waits for each request file/result to settle before issuing the next
click.

The elevated helper now also accepts one bounded `click_sequence` request
(1--16 ratio-validated clicks with optional delays). This removes the race
window between separate scheduled-task invocations while preserving the same
narrow, non-shell UI-action contract.

The server control API also accepts `entity_id` on `/api/send`, allowing a
real connected client to receive the packet without relying on
`connections[-1]`. This is required for overlapping two-client transitions:
each client can receive its own `S->C 0x000D[00]` while its per-client state is
kept isolated.

Run `r6` independently reproduced the secondary's natural Plaza path after
the primary had exited: five C2S `0x0016[01]` calibration requests, natural
C2S `0x0064[01]`, and one S2C `0x0064` with no `0x006E`. Screenshot:
`artifacts/screens/r6_secondary_plaza_0064.bmp`. This confirms the path is not
limited to the first client; only the overlapping roster timing remains.
