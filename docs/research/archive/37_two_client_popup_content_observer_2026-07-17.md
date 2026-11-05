> **ARCHIVED (2026-07-17).** 이 문서는 대체됨 — 현재 확정 사실은 ../INDEX.md 참조.

# Two-client popup/content observer boundary (2026-07-17)

## Scope

Two local clients were observed without patching process memory or generating
packets:

| Server/control | Client PID | Capture |
|---|---:|---|
| `9207 / 9300` | `110580` | `captures/packets_20260717_084944.txt` |
| `9208 / 9301` | `137596` | `captures/packets_20260717_091723.txt` |

Both control snapshots reported the same stable local state:

```text
scene_opcode = 100 (PatHouse)
phase_31792 = 2
phase_31796 = 100
self_actor_id = 0
room_kind = null
char_created = true
zone_request_count = 2
calib_0004_count = 5
full_0064_sent = false
```

The captures also have the same functional prefix. Each contains C2S `0x0007`
once, S2C `0x0003/0x0005/0x0007/0x000A/0x000B` once, five S2C `0x0004`
samples, and then only C2S/S2C `0x0016` heartbeats. Neither contains C2S
`0x0017`, `0x0064`, `0x0065`, `0x0066`, or `0x0067`.

Therefore neither client had entered a content room or established a self
actor/room membership during this comparison. This run can test input and UI
boundaries, but cannot establish a Gym/Magic/Cook/etc. content protocol.

## Observer extensions from docs 34/35

`tools/x32dbg_plaza_interaction_trace.py` now includes the following default
event-driven checkpoints in addition to its room/packet set:

- six room five-stage initializers;
- six room initial local-event builders;
- Playroom, Gym, Magic, Cook, Shop, and Library content builders;
- shared content descriptor insertion `0x00547BF0`;
- popup-ring producer `0x005E6960`;
- generic click producers `0x00542B90` and `0x005E7130`;
- local event wrapper `0x005305D0`;
- Shop world/NPC setup `0x0055A650`.

The observer decodes popup `(content_key, screen_x, screen_y)`, local queue
event ID/mode, descriptor index/name/value, room post-load code, C2S `0x0065`
room report fields, and generic opcode/payload data. Python bytecode compilation
passes. The final default set contains 52 breakpoints.

## Hot probes removed from the default set

Two doc-34 validation addresses are useful only as tightly bounded temporary
probes:

- `FUN_005A49B0 @ 0x005A49B0` produced 228 stat lookups in the short first
  observation and is continuously called outside one-time room initialization.
- `FUN_0051B1F0 @ 0x0051B1F0` produced 107 hit-test calls in about 23 seconds
  once the pointer state was active.

Leaving either enabled materially perturbs frame timing. Both are excluded
from the default observer. Use them only for a one-click or one-room-init
window, with an immediate hit limit/clear operation.

## First client: post-initialization observation

Raw trace:
`artifacts/dynamic-analysis/x32dbg_popup_content_first_session_20260717_0924.jsonl`

The existing x32dbg session was resumed with the expanded observer. It proved
that normal stat lookups were active, but no room initializer, content builder,
popup producer, local content queue, or C2S content/room sender fired. The hot
stat breakpoint was removed, the debugger detached normally, and both clients
returned to `Responding=True`.

This is expected for a client already idle in PatHouse after its initialization
window; it is not proof that the room builders are broken.

## Second client: SendInput boundary

Raw trace:
`artifacts/dynamic-analysis/x32dbg_popup_content_second_session_20260717_0927.jsonl`

Direct `start_session_attach(137596)` failed while another x32dbg instance was
present. Reusing the existing elevated x32dbg instance and issuing its native
`attach(137596)` command succeeded. This is the reliable sequential-debugger
path for the next run.

After the approved door/floor SendInput actions, `FUN_0051B1F0` was reached
with:

```text
return address = 0x00518E30
screen X       = 0x13A (314)
screen Y       = 0x0D3 (211)
```

The function then repeated against multiple button objects while pointer state
remained active. This proves all of the following:

1. the foreground window belonged to PID `137596`;
2. SendInput crossed the OS/application boundary;
3. the client sampled the injected coordinates and ran its UI button hit-test.

No `ButtonQueue_Push`, local event wrapper, popup-ring producer, room
transition, movement builder, or C2S `0x0065/0x0066/0x0067` followed. The
server capture added only `0x0016` heartbeats.

The negative result must therefore not be labeled an OS input-injection
failure. At these coordinates and in this PatHouse state, no selectable button
or world/content continuation was returned. The remaining split is:

- coordinates landed on non-action UI/world space;
- the relevant object/button was disabled or not constructed;
- self-actor/content readiness was absent (`self_actor_id == 0`);
- the world-ray path is separate from this UI-button path and was not reached.

## Next clean-run plan without play manipulation

### Initialization capture

1. Start one clean server/client only.
2. As soon as the Azrok PID exists, attach x32dbg before S2C `0x0007` completes.
3. Install the default 52 event-driven breakpoints.
4. Capture through PatHouse `GameManager_ExecuteRoomInit(100)` and the stable
   phase-2 baseline.
5. Require explicit observer `detached` and target-liveness records at exit.

This run will prove whether the local PatHouse initializer and descriptor path
are executed before any content interaction.

### Content-room capture

For each room, begin tracing before the room transition and require this chain:

```text
transition resolver / queue
  -> room initializer(post-load code)
  -> room five-stage initializer
  -> room final content builder
  -> content descriptor insert(s)
  -> C2S 0x0065 room report and sender return
```

Only after that chain is present should a popup/content action be tested. The
first new popup key, local event, and C2S opcode must be correlated to one
visible action before implementing a server response.

### Two-client use

Attach sequentially through the single elevated x32dbg instance:

1. observe client A, clear only observer-owned breakpoints, resume, detach;
2. issue x32dbg native `attach(pid_B)`;
3. observe client B with a distinct JSONL file;
4. compare room initializer, descriptor names, C2S room kind, and packet tail.

The two current clients use separate servers (`9207` and `9208`), so they are
comparison replicas, not a same-room multiplayer authority test. A true roster
and peer-movement test requires both clients connected to one server instance.

