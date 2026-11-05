# All-room clean observer plan and Gym negative result (2026-07-17)

## Goal and constraints

The goal is to restore practical local play across every bundled room while
first separating local hit-test/room-state failures from missing server
authority. This plan is observation-only:

- no executable or process-memory patch;
- no synthetic C2S or S2C packet;
- no byte-for-byte echo of directionally different opcodes;
- one clean client run per reproducible boundary when possible.

## Current live Gym negative result

Live observer:
`artifacts/dynamic-analysis/x32dbg_plaza_interaction_live_20260717_0845.jsonl`

The observer attached to live `Azrok.exe` PID `101928` through elevated x32dbg
PID `44456`. It installed the then-current 24 sparse breakpoints and resumed
the debuggee. The Gym remained visibly rendered.

Normal Windows UI input was tried against the upper/lower equipment, door,
and floor, including single, double, and short hold-style input. `Right`, `D`,
and `B` releases were also tested. The actor did not move and the trace
produced no checkpoint event. Therefore this session did not reach any of:

- `ButtonQueue_Push @ 0x0050FE80`;
- room transition resolver `0x00611CD0` or apply path `0x006122C0`;
- C2S movement/action builders `0x005AB7B0` / `0x005AB830`;
- C2S room report builder `0x005AB760`.

This is a negative boundary, not evidence that C2S `0x0065` needs an ACK. The
only observed C2S `0x0065` preceded the boundary and decoded as the already
completed Gym entry report `(kind=8, direction=0x15, x=0x215, y=0x585)`.

At the end of the 900-second observer window, its Python process and target
PID `101928` were no longer present, while x32dbg PID `44456` remained. The
JSONL file did not receive `timeout`, `detached`, `process_exit`, or `fatal`.
Therefore the termination cause is unknown and this run cannot prove graceful
detach. The next run must treat an explicit final observer record plus a live
target-process check as required completion evidence.

### `0x42` correction

The immediate `0x42` in `FUN_00535660` is `VK_B`, not a queue ID. It is passed
to `GetAsyncKeyState`. If the B-release branch is allowed, it pushes queue ID
`0xBB` or `0xBC`. A whole-program immediate search found no direct producer of
`ButtonQueue_Push(0x42, ...)`.

## Room load matrix

`GameManager_DispatchRoomCode` consumes a loader index and later a post-load
code. The post-load code calls `GameManager_ExecuteRoomInit @ 0x0050B400`.

| Loader | File | Post-load | Expected phase | Room |
|---:|---|---:|---:|---|
| `0` | `room.wmb` | `0x64` | `2` | PatHouse tutorial |
| `1` | `playroom.wmb` | `0x65` | `2` | Playroom |
| `2` | `gym.wmb` | `0x66` | `2` | Gym |
| `3` | `magic.wmb` | `0x67` | `2` | Magic room |
| `4` | `cook.wmb` | `0x68` | `2` | Kitchen |
| `5` | `shop.wmb` | `0x69` | `2` | Shop |
| `6` | `library_1.wmb` | `0x6A` | `2` | Library |
| `8` | `lobby.wmb` | `0x6C` | `1` | Lobby |
| `9` | `pet.wmb` | `0x6B` | `0` | Pet select |
| `10` | `ground.wmb` | `0x6D` | `2` | Ground |
| `0x0B` | `hansol.wmb` | `0x6E` | `4` | Plaza |
| `0x0C` | `OXQuiz.wmb` | `0x6F` | `5` | OX Quiz |

The table uses the dispatcher's actual switch values. The C2S `0x0065` first
byte is a separate wire kind and must not be assumed equal to either loader or
post-load code.

## Next clean-run breakpoint set

The updated observer is `tools/x32dbg_plaza_interaction_trace.py`. It contains
28 sparse checkpoints for the next process. The currently running observer is
unchanged; editing the source does not alter its loaded checkpoint set.

### Queue and room lifecycle

- `0x0050FE80` — queue push; records return address, ID, and both parameters.
- `0x0050B400` — room initializer; records the post-load room code.
- `0x0050A7F0` — loading/scene request enqueue.

Do not set default breakpoints on `0x0050FFD0` (queue pop), `0x0050A0F0`
(per-frame dispatcher), or `0x00518D80` (per-frame hit-test). They are hot and
can perturb the client.

### Door and direct-return paths

- `0x005ECFF0` — conditional room door to Plaza; depends on room data
  `slot+0x42 == 3`.
- `0x005EE600` — unconditional room door to Plaza.
- `0x005EE7B0` — room door to OX Quiz.
- `0x00568770` — direct room-to-Plaza transition.
- `0x00602830` — OX Quiz direct return to Plaza.

For the three door handlers the observer records `ECX` as the door context and
the dword at `context+0xBA` as the selected door slot.

### Local transition and packet boundary

- `0x00611CD0` — transition trigger resolver.
- `0x006121B0` — region transition probe.
- `0x006122C0` — local room apply + C2S `0x0065` producer.
- `0x005AB760` — C2S `0x0065` builder, decoded as `<kind,state,x,y>`.
- `0x0061264D` — return from the main `0x0065` send.
- `0x00614D70`, `0x00614EA0`, `0x00614F3A` — alternate Plaza/Hansol
  position-report path and return.

### Movement, content, and generic wire boundary

- `0x005AB7B0` — C2S `0x0066` movement builder.
- `0x005AB830` — C2S `0x0067` action/arrival builder.
- `0x005AB950` — C2S `0x006C` community target builder.
- `0x005CE8E0` — E/community local toggle and request path.
- `0x005AB6A0` — generic opcode/payload sender.
- `0x00614370`, `0x006143EC` — Plaza/Hansol stage boundary.

## Reproduction procedure

Use one append-only packet capture and one JSONL trace per run.

1. Start the server/control panel and a fresh client normally.
2. Attach the observer only after the client process exists and before the
   first target-room interaction.
3. Record the starting room/phase from the control panel without changing it.
4. For each accessible room, perform the same minimal sequence:
   - one empty-floor movement;
   - one non-content click;
   - one intended room-content interaction;
   - one door/exit interaction.
5. Stop after the first broken boundary. Preserve the screenshot, packet tail,
   and JSONL trace before retrying.
6. Repeat from a clean process for the next room so stale UI flags or room
   globals do not contaminate the comparison.

For every room, classify the result at the first missing checkpoint:

| Last proven checkpoint | Interpretation |
|---|---|
| no movement builder | local input/raycast/actor-state gate |
| movement works, no queue/transition resolver | object/door hit-test or content gate |
| resolver fires, no `0x0065` builder | local transition construction failure |
| `0x0065` builder + return fire, no room initializer | local queue/loader failure |
| room initializer fires, content absent | room-specific init data or server content gap |
| C2S request fires, no later local change | recover the direction-correct authoritative reply contract |

## Evidence bundle required per room

Each room result should contain:

- loader index, post-load code, and final phase;
- first and last queue IDs;
- decoded first/second C2S `0x0065`, if present;
- count of C2S `0x0066` and `0x0067` before and after content input;
- exact door handler/caller hit;
- first missing checkpoint;
- whether closing/reopening local UI changes the outcome;
- whether the same action succeeds in another phase-2 room.

This produces the evidence needed to implement only the missing server
contracts, while keeping local hit-test and room initialization defects out of
the protocol layer.
