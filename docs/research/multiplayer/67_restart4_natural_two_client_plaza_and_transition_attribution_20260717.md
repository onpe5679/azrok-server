# Restart-4 natural two-client Plaza and transition attribution (2026-07-17)

This note records the first restart-4 run in which two clients independently
completed the natural growth/outside-door route on one reused server and then
rendered and relayed each other in Plaza. It also records a multi-client
dashboard attribution bug and the source-level correction.

## 1. Both clients completed the natural Plaza route (VERIFIED)

The clients shared the existing server on `127.0.0.1:9207`:

| role | PID | entity | route |
|---|---:|---:|---|
| primary | `138892` | `2` | restart-4 natural growth and user outside-door click |
| secondary | `60884` | `3` | reused server, exact Frida Sleep button, user outside-door click |

The secondary used the verified internal event contract
`ButtonId=33 / caller=0x005E3F14 / params=1,-1`, naturally grew to RedRon,
and then emitted the outside request when the user clicked the real door.
`captures/packets_20260717_230719.txt` records its transition as:

```text
C2S #94  0x0019[00]
S2C #94  0x000D[00]
S2C #95..#99 0x0004[01] x5
C2S #100 0x0064[01]
S2C #100 0x0064, 27B, no 0x006E
```

Both connections then remained in room kind `27`, `plaza (0064-only)`, with
recent bidirectional heartbeats.

## 2. Reciprocal roster rendering (VERIFIED)

Immediately after the secondary committed its self actor, the server emitted a
targeted roster/position pair in each direction:

```text
to entity 2: S2C 0x0066(entity 3, name Player) + S2C 0x0068(entity 3)
to entity 3: S2C 0x0066(entity 2, name Azrok1) + S2C 0x0068(entity 2)
```

The live per-client counters converged to:

| entity | S2C 0066 | initial S2C 0068 | peer_count | visible_remote_actor_count |
|---:|---:|---:|---:|---:|
| 2 | 1 | 1 | 1 | 1 |
| 3 | 1 | 1 | 1 | 1 |

Visual evidence independently proves actual renderer consumption rather than
server-side accounting only:

- `artifacts/dynamic-analysis/restart4_multiplayer_primary.bmp`
- `artifacts/dynamic-analysis/restart4_multiplayer_secondary.bmp`

Both screenshots show two actor labels/models (`Guest` and `Player`) at the
same time. The self label remains a client-local identity concern described in
note 56; these screenshots prove reciprocal actor visibility, not a new self
name wire contract.

## 3. Movement report and peer relay (VERIFIED wire path; CONTAMINATED input attribution)

Before the observed movement report, saved state
`artifacts/dynamic-analysis/restart4_two_client_state.json` recorded entity 2
at `(4268,-10)` with `C2S 0x0066=16`. The subsequent action produced:

```text
C2S #186 0x0066, entity 2 movement report
S2C #186 0x0068, relayed to entity 3
C2S #187 0x0067, entity 2 stop/direction report
```

The `0x0066` report encoded a route from `(4268,-10)` to `(5079,-640)`, and
the `0x0068` relay carried that same destination for actor 2. After the
following stop/direction report, the server's current position for entity 2
was `(4275,-16)`. The counters changed as follows:

```text
entity 2 C2S 0x0066: 16 -> 17
entity 3 S2C 0x0068:  1 -> 2
server current position: (4268,-10) -> (4275,-16)
```

This is direct packet evidence that restart 4 retained the previously proven
state-1 movement relay contract after both clients used the full natural
growth/door path.

The user subsequently clarified that the click was aimed at the **other game
window**, yet the entity-2 Azrok moved. Therefore the causal statement
"entity 2 moved because its own window was clicked" is contaminated by a
possible cross-window input leak. It is **NOT VERIFIED** which client window
actually consumed that physical input, and this run cannot prove correct input
focus isolation.

The contamination does not weaken the wire result: entity 2 really emitted
`C2S 0x0066`, and the server really delivered the paired `S2C 0x0068` to
entity 3. Only the initiating UI/window attribution is withdrawn.

## 4. Spawn and camera are not a baseline (VERIFIED contamination)

The user had already moved one existing client and changed its camera before
the final screenshots. The secondary screenshot visibly contains a severely
occluding close camera/object view. Therefore the screenshots and coordinates
in this note are valid for roster visibility and movement-relay evidence only.

They must **not** be used to claim:

- the default Plaza spawn position;
- the default camera position, distance, or yaw;
- correct equality of initial transforms between clients;
- correct isolation of mouse input to the clicked game window.

A clean untouched client captured before any input is still required for those
questions. Default spawn/camera semantics remain **NOT VERIFIED**.

## 5. Targeted departure after secondary close (VERIFIED)

Closing secondary PID `60884` / entity 3 produced exactly one targeted packet
to the surviving primary:

```text
S2C #0 0x0067 [03 00 00 00] [relay]
```

The live counters changed:

```text
connected clients: 2 -> 1
primary S2C 0x0067: 0 -> 1
primary peer_count: 1 -> 0
primary visible_remote_actor_count: 1 -> 0
```

`artifacts/dynamic-analysis/restart4_multiplayer_after_leave.bmp` shows the
surviving `Guest` self actor with the remote `Player` removed. This repeats the
targeted `0x0067` lifecycle from note 52 after both clients used the natural
growth/outside-door route.

## 6. Dashboard attribution bug (VERIFIED in code/observation)

The first transition-health implementation was single-client shaped. In a
multi-client run it could combine:

- process-memory watches belonging to the primary Azrok process; and
- `_active_proto_state()` belonging to whichever server connection was active.

That mixture could assign one client's door/evolution/`0x0064` protocol state
to another client's scene/phase/dispatch/self watches. The global transition
badge could consequently look coherent while its fields came from different
clients.

## 7. Per-client attribution correction (VERIFIED in source/static checks)

`azrok_server.py` now builds a transition summary for every player:

- each connection uses only its own protocol state and heartbeat age;
- primary-only process-memory watches are attached only to the primary card;
- a non-primary Plaza client is labelled protocol-healthy from its own
  `0x0064`, room, and heartbeat, with memory fields explicitly unobserved;
- the global badge becomes an aggregate summary with client, Plaza, PatHouse,
  stale, and error counts;
- `content.active_entity_id` identifies which connection owns the detailed
  top-level `proto_state`/growth panel.

`azrok_control_page.py` now renders each player's transition on its own card,
shows the active entity in the growth panel, and explains when memory watches
are unavailable instead of falling back to the primary values.

Static validation completed successfully:

```text
python -m py_compile azrok_server.py azrok_control_page.py
dashboard JavaScript: node --check
```

## 8. Live activation after full restart (VERIFIED)

After the multiplayer session and departure proof were captured, a full normal
restart activated the updated source. The new live API returned:

```text
server.players[0].entity_id = 2
server.players[0].transition.memory_observed = true
server.memory_watch_entity_id = 2
content.active_entity_id = 2
```

The per-player transition contained the same primary memory-derived
`scene/phase/dispatch_mode/self_actor_id` fields and its own connection
heartbeat/protocol fields. The served dashboard HTML also contained the
per-client transition rendering, memory-watch explanation, and
"현재 제어 대상 클라이언트" active-entity UI. Thus deployment and live API/UI
activation of the attribution fix are **VERIFIED**, not merely source-tested.

The post-restart session currently has one client. Re-exercising the new
two-client aggregate badge (`client_count/plaza_count/pathouse_count`) is still
**NOT VERIFIED** in the restarted process, but this is now a narrow aggregate
display check rather than an activation blocker.

## 9. Remaining controlled checks

- **NOT VERIFIED:** repeat with two freshly launched, untouched clients and
  click each window separately while recording the foreground HWND and
  per-entity `C2S 0x0066` counters. This distinguishes engine-wide input state
  from an automation/focus artifact.
- **NOT VERIFIED:** attach a second client to the restarted server and confirm
  the new aggregate badge reports two independently attributed player cards.
