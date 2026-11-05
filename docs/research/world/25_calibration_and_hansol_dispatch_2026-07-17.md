# Calibration and Hansol dispatch correction (2026-07-17)

This note records a read-only static re-analysis of the current Ghidra project
snapshot (`/New Traces/Azrok_original.exe`). No executable, runtime patch, or
shared Ghidra project was modified.

## 1. S->C 0x0004 must be five `0x01` samples

`HandleS2C_0004_CalibrationSample @ 0x0059DE50` behaves as follows:

1. A null payload resets the sample count at `this+0x9DB`, the last tick, and
   both five-entry measurement arrays.
2. A non-null payload records the timestamp/delta in the slot selected by the
   current count and then increments the count.
3. Counts 1 through 4 cause C->S `0x0016 [01]` to be sent.
4. On the fifth valid sample, the handler captures the final values and writes
   `0xFF` into byte 0 of the same inbound packet buffer.

`DispatchState0Specific_S2C @ 0x0059DD20` calls that handler for opcode
`0x0004` only when the byte arriving from the server is `0x01`.
`DispatchInbound_ByClientMode @ 0x00594310` then passes the same, now-mutated
buffer to `DispatchState0Common_S2C @ 0x0050CBC0`. Its opcode `0x0004` branch
sees `0xFF` and sets the readiness latch `gm+0x31C71=1`.

Therefore the packet-faithful server sequence is:

```
S->C 0x0004 [01 + timestamp] x 5
                         |
                         +-- fifth packet is changed to FF by the client
                             before common dispatch
```

| Candidate | Result |
|---|---|
| five server-sent `0x01` samples | Correct: records all five samples and sets the latch through the client's internal mutation |
| four `0x01` samples plus server-sent `0xFF` | Shortcut only: common dispatch can set the latch, but the specific handler rejects `0xFF`, leaving the calibration count/final sample at four |
| five `0x01` samples plus an explicit `0xFF` | Redundant and not packet-faithful |

This resolves the explicit contradiction in
`HANDOFF_2026-07-17_DYNAMIC_ANALYSIS.md:371-379` and
`docs/research/23_recovered_opcode_details.md:293-302`. The older recipe's
four-plus-FF sequence is superseded by five `0x01` samples. The statement in
`docs/debug/2026-03-31_session3_discoveries.md:44-46` was already correct.

The automatic bootstrap heartbeat path remains intentionally separate from
the Hansol calibration and must not be treated as protocol truth:

- it sends `sample_kind=0x00`, while its comment says
  six samples and the loop actually sends at most five. A `0x00` packet cannot
  enter the state-0-specific calibration handler described above.
- As of this correction, `MACROS['hansol']` and `MACROS['calib_faithful']` both
  use the correct five `0x01` samples; the Hansol macro is also rejected until
  the initial PatHouse bootstrap is stable, preventing interleaving with those
  automatic `0x00` packets.

## 2. What `scene_opcode=110` actually means

The earlier shorthand that treated `Plaza_TransitionFromRoom @ 0x00568770` as
directly placing room code `0x6E` in the ButtonQueue is incorrect.

The function passes `0x6E` to `GameManager_EnqueueRoomCode @ 0x0050A7F0`, whose
actual behavior is broader than its current label:

```c
gm->scene_opcode_31AAD = 0x6E;
engine_scene_request(0x6E);
post_load_request(0x6E);
```

It then performs transition cleanup, sets `gm+0x31C72=1`, and resets the
calibration handler with a null payload.

Only later does `FUN_0050A880` read `gm+0x31AAD`. Its case `0x6E` pushes
ButtonQueue code `0x0B`. `GameManager_DispatchRoomCode @ 0x0050A0F0` then
handles that code:

- while `gm+0x31C71==0`, it requeues `0x0B`;
- once the calibration latch is set, it loads `hansol.wmb`, pushes `0x6E`, and
  clears the latch;
- the later queue code `0x6E` calls `GameManager_ExecuteRoomInit(0x6E)` and
  sets the active room state at `gm+0x31792` to 4.

The corrected chain is therefore:

```
Plaza_TransitionFromRoom
  -> scene request 0x6E stored at gm+0x31AAD
  -> post-load bridge FUN_0050A880
  -> ButtonQueue 0x0B
  -> wait for calibration latch
  -> load hansol.wmb
  -> ButtonQueue 0x6E
  -> GameManager_ExecuteRoomInit(0x6E)
  -> Hansol_SceneStageHandler
```

Consequently, the control panel showing `scene_opcode=110` proves only that
the scene request was stored. It does **not** prove that the post-load bridge,
ButtonQueue code `0x0B`, the readiness-latch branch, queue code `0x6E`, or the
Hansol initializer has run. The additional per-frame dispatch gate at
`gm+0x31946` can also prevent queued room work from being consumed.

## 3. Meaning of a missing C->S 0x0064

`GameManager_ExecuteRoomInit(0x6E)` calls
`Hansol_SceneStageHandler @ 0x00614370`. In its stage 0 there is no conditional
branch before the call to `SendC2S_0064_LocalBootstrapStatus @ 0x006130B0`.
That routine eventually calls `FUN_005AB710`, which unconditionally invokes
the generic sender as:

```c
send(opcode=0x64, payload=&one_byte_status, length=1);
```

The first conditional early return in the stage handler is in stage 1, after
the stage-0 send attempt.

Thus, with a live connected transport, `scene_opcode=110` combined with no
C->S `0x0064` strongly localizes the stall before
`Hansol_SceneStageHandler`: post-load bridge completion, queue insertion,
`gm+0x31946`, latch/room-load completion, or queue-code `0x6E` dispatch. A
lower-level socket failure could still hide a send attempt, so a dynamic test
should break at `0x00614370`, `0x006143EC`, and `0x005AB738` to distinguish
"handler not entered" from "generic send attempted but transport failed."

`self_actor_id` (`player+0x2F8`) must **not** be a Hansol admission condition.
`HandleS2C_0064 @ 0x00615650` reads the authoritative ID at payload `+1` and
`0x00615AF0` writes it to that field. In other words, it is the result of the
stage-0 `C->S 0x0064` / `S->C 0x0064` handshake, not a prerequisite for it.

## 4. Recommended runtime watch set

For the next x32dbg pass, watch/break on:

- `0x0050A7F0`: scene request stored (`gm+0x31AAD`)
- `0x0050A880`: post-load scene-to-ButtonQueue bridge
- `0x0050A0F0`: ButtonQueue pop/dispatch
- `gm+0x31946`: per-frame room-dispatch gate
- `gm+0x31C71`: calibration readiness latch
- `gm+0x31792`: active room state
- `0x0050B400`: room initializer
- `0x00614370`, `0x006143EC`, `0x005AB738`: Hansol stage entry,
  stage-0 sender call, and concrete `send(0x64, ..., 1)` setup

## 5. Server implementation separation

The server's initial automatic `S->C 0x0004[00 + timestamp]` traffic and the
Hansol `S->C 0x0004[01 + timestamp]` sequence have different meanings:

- `0x00` is legacy PatHouse bootstrap/pacing traffic. State-0-specific dispatch
  rejects it, so it does not increment the calibration accumulator at
  `gm+0x9DB` and cannot create the fifth-sample readiness latch.
- `0x01` after `S->C 0x000D` is the real Hansol calibration sequence. The
  transition function first resets the accumulator, after which exactly five
  `0x01` packets are required.

The current `proto_state['calib_0004_count']` name is therefore historical: it
counts how many automatic `0x0004[00]` packets the **server emitted**, not how
many calibration samples the client accepted. It may safely be used as a
quiescence marker to ensure the automatic traffic has stopped, but it must not
be interpreted as client readiness or as the `gm+0x9DB` sample count.

The Hansol macro guard was reviewed against the binary flow. A stable PatHouse
baseline is represented by:

- character and inbound zone-request flow observed by the server;
- automatic `0x0004[00]` emission finished and at least two quiet heartbeats;
- current `gm+0x31792 == 2` (PatHouse room phase);
- current `gm+0x31946 != 0` (room queue dispatch enabled);
- current `gm+0x31AAD == 100`.

`gm+0x2E984`, exposed as `logic_state`, is **not** the field that the room
dispatcher sets to 2 after PatHouse initialization. Using it as the guard would
incorrectly defer a valid baseline. Likewise, `auto_create_sent` is a launcher
implementation detail rather than a protocol prerequisite; manual character
creation can reach the same valid baseline.

`player+0x2F8` (`self_actor_id`) must **not** be a pre-transition guard.
`HandleS2C_0064_ApplyAuthoritativeSelf @ 0x00615650` reads the authoritative
ID from inbound payload `+1` and calls `FUN_00615AF0`; that setter writes the
value to `player+0x2F8`. There is no such requirement in the preceding
`0x00568770 -> 0x0050A880 -> room 0x0B/0x6E -> 0x00614370` path. Hansol stage
0 first sends C->S `0x0064`, and the server's S->C `0x0064` response supplies
the ID before the stage-1 actor lookup. Requiring a nonzero ID before stage 0
would therefore create a circular dependency and reject a clean baseline.

Once this guard passes, the automatic `0x0004[00]` loop has ended. The four
C->S `0x0016[01]` requests generated by the first four Hansol samples can still
receive normal `S->C 0x0016[00]` responses, but they no longer cause extra
`0x0004[00]` packets. Thus the five Hansol samples remain contiguous in the
calibration state machine even though heartbeat packets can appear between
them on the wire.
