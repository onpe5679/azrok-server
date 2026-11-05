> **STALE — 2026-07-18 스냅샷.** 이 문서는 네이티브 클라이언트 시절의 현황이며 현재 상태가 아니다.
> 현재 확정 상태는 [`INDEX.md`](INDEX.md) §1, 전체 문서 목록은 [`REGISTRY.md`](REGISTRY.md).
> (배너 추가 2026-07-29. 본문은 손대지 않았다.)

# Current Status

Date: 2026-07-18
Target: `Azrok.exe`
Goal: make the client finish loading against the local Python server and reach
confirmed playable in-world control

## 2026-07-18 Playroom direct transition and full triad

The allowlisted generic portal helper successfully queued selector 1 and the
native client loaded `playroom.wmb` as `scene=0x65 / phase=2`. Its natural
C2S `0x0065` was `06074ef1ffffb0f0ffff`, decoded as wire kind 6,
direction 7, x -3762, y -3920. This exposed two server display bugs: kind 6
was mislabeled Library and signed coordinates were shown as large unsigned
integers. The server now uses the exact eight-room wire map and signed
decoders for C2S 0065/0066/0067; 23 tests pass, but live activation awaits a
server restart.

The original Playroom overlay was rendered and all three activities completed.
Juggling stored stat34=5, tumbling stat36=5, and yoyo stat35=4; every result
sent one 196-byte C2S `0x0007`, raising save_count from 3 to 6 with valid
checksums while preserving Gym 7/21/5. The exact exit event `0x1A9` then
queued scene request 0x6E, and the verified S2C 0x000D calibration returned
the client to healthy Plaza. See note 85.

## 2026-07-18 verified portal allowlist and Gym exit recovery

The corrected portal helper now detaches Frida immediately after the native
selector commit. A second Plaza→Gym run completed with no helper residue and
again reached `room_kind=8 / scene=0x66 / phase=2` through a new natural C2S
`0x0065`. Static enumeration limits the generic Plaza room allowlist to
selectors `{0,1,2,3,4,5,6,10}`; OX selector 12 remains a separate workflow,
and uninitialized or descriptorless selectors are hard-rejected.

The original Gym exit event is `0x1AA` and queues Plaza scene request `0x6E`.
The live client stalled before the loading callback, consistent with the
`gm+0x31946` per-frame gate being zero. Direct S2C `0x000D[00]` from that
stalled state restarted calibration and produced the full five-sample → C2S
`0x0064` → S2C `0x0064` sequence, returning to healthy Plaza. The narrower
one-shot restoration of `gm+0x31946=0xFFFFFFFF` remains dynamically unverified.
See note 81.

## 2026-07-18 Plaza→Gym direct portal event and full Gym triad

The original Plaza Gym door's final commit is now reproducible without more
movement/camera trials.  The narrow Frida action calls
`FUN_006142C0(PortalMgr,2)`, which only stores the verified pending selector.
The next native main tick performed the original
`FUN_00611CD0→FUN_006122C0` path, loaded `gym.wmb`, and emitted exact C2S
`0x0065=08151502000085050000`.  Live state became
`room_kind=8 / scene=0x66 / phase=2`, and the original Gym intro rendered.

The user-sampled avatar position at the actual Gym front was `(521,1741)`.
The packet coordinates `(533,1413)` are the portal descriptor's entry/report
point, not that live front position.  This corrects the earlier conflation.

The same live client completed the remaining Gym choices through the visible
UI. Pushup saved stat31 `0→7`; rope skipping saved stat33 `0→5`; dumbbell
stat32 remained `16`. Each action immediately sent a 196-byte C2S `0x0007`.
The final common stats `(3,41,50,100,0,30)` and Gym skills `(7,16,5)` exactly
matched the parallel static prediction. See note 81 and capture
`captures/packets_20260718_052925.txt` (#246, #286, #293).

## 2026-07-18 Gym natural action and reconnect persistence

The real-player path now reaches Plaza and enters Gym through a natural door
click (`C2S 0x0065 = 08 15 15 02 00 00 85 05 00 00`).  The original Gym
selection ring was operated through the visible UI and the dumbbell choice
completed twice.

x32dbg and packet capture corrected the earlier `+3` hypothesis: the natural
Gym path uses `FUN_005a1b90(domain 2)`, not the sys.tmp executor.  With the
current hunger/energy tiers it applied `stat32 +8` twice (`0→8→16`) and called
`FUN_005a4770(0,1,7)` for an immediate 196-byte C2S `0x0007` save each time.
After a full server/client restart, the new bootstrap restored
`S2C 0x0007 +0x4B=16` while retaining evolution 1.  See note 79 and captures
`packets_20260718_041857.txt` / `packets_20260718_052925.txt`.

## 2026-07-18 playable-v2 persisted evolution reconnect fix

The isolated `profile_playable_v2` store already held the Player snapshot with
`C2S 0x0007 +0x05=1`, but capture
`captures/packets_20260718_032715.txt` proved that the reconnect bootstrap sent
`S2C 0x0007 +0x02=0`.  The live client consequently read
`ProtocolState+0x130=0` even while the control API reported
`persisted_evolution=1`.

Ghidra directly verified the directional mapping:

```text
C2S 0007 +0x05 -> S2C 0007 +0x02 -> ProtocolState+0x130
```

`_apply_saved_character_state()` now copies that one byte before restoring the
already-proven stat and tuple ranges.  A clean restart reused the unchanged
Player save and capture `captures/packets_20260718_033343.txt` emitted payload
prefix `00 02 01 ...`.  Read-only Frida observation then repeatedly measured
`evolutionGateRead value=1`; evidence is
`artifacts/dynamic-analysis/playable_v2_reconnect_field130_20260718_0335.txt`.
Python compilation and all 13 content-builder tests pass.  See note 70.

The same session remains in PatHouse while the far-left
`gate_mun_MDL_048` / `doorframe_01` outside-gate candidate is being reproduced.
`dm_door_0003_057` is the bathroom/internal door. Plaza and Gym completion are
therefore still in progress, not claimed by this update.

## 2026-07-17 23:45 operational handoff and clean shutdown

At the user's request the current client and local server were stopped for a
fresh Codex session.  The shutdown was directly verified: no `Azrok.exe`, no
listeners on 9207/9300, both scheduled tasks Ready, and no pending one-shot
`REQUEST_*` marker.  The authoritative startup/runbook for the next session is
`HANDOFF_2026-07-17_2345_CONTINUE.md` at the workspace root.

The final pre-shutdown run was capture
`captures/packets_20260717_233509.txt`: one live PID `65288`, PatHouse
scene 100/phase 2/mode 0, native Nexus 200, natural RedRon evolution saved at
`C2S 0x0007 +0x05=1`, save sum 5040, and heartbeat alive.  The user requested
handoff before clicking the real exit door.  Two final per-player transition
source fixes (primary scene/phase fallback and hex-string natural-evolution
parsing) will first become live on the next server start and must be verified
there.

## 2026-07-17 23:36 departure, input-attribution correction, GUI live activation

Closing secondary PID `60884` / entity 3 sent one
`S2C 0x0067[03 00 00 00]` to the primary. Connected clients changed 2→1,
the primary's `S2C 0x0067` count changed 0→1, and its peer/visible counts
changed 1/1→0/0. Screenshot
`artifacts/dynamic-analysis/restart4_multiplayer_after_leave.bmp` confirms that
the remote `Player` was removed while the `Guest` self actor remained.

The earlier 16→17 `C2S 0x0066` and peer 1→2 `S2C 0x0068` pair remains a
VERIFIED movement-relay wire result. However, the user clicked a different
game window when entity 2 moved. Which window consumed the physical input is
therefore CONTAMINATED/NOT VERIFIED due to possible cross-window input
leakage. Do not use this run as proof of correct mouse-focus isolation.

A subsequent full normal restart activated the per-player GUI attribution
fix. The live API returned a transition object on entity 2,
`server.memory_watch_entity_id=2`, `content.active_entity_id=2`, and
`memory_observed=true`; the served HTML contains the per-client transition,
memory-watch explanation, and active-entity panel. Live activation is now
VERIFIED. Only the new two-client aggregate badge remains to be re-exercised
after this restart. See note 67.

## 2026-07-17 23:31 restart-4 natural two-client Plaza

Secondary client PID `60884` (entity 3) reused the primary's port 9207 server,
used the exact Frida Sleep event, naturally grew to RedRon, and completed the
actual user-clicked outside-door path. Its capture sequence was
`C2S 0019[00] -> S2C 000D[00] -> 0004[01] x5 -> C2S 0064[01] -> S2C 0064`
with no `0x006E`. Both entity 2 and entity 3 then occupied Plaza room kind 27
with continuing heartbeats.

The server sent one targeted `S2C 0x0066` actor upsert and one initial
`S2C 0x0068` position to each client. Both reported `peer_count=1` and
`visible_remote_actor_count=1`. Screenshots
`artifacts/dynamic-analysis/restart4_multiplayer_primary.bmp` and
`artifacts/dynamic-analysis/restart4_multiplayer_secondary.bmp` show `Guest`
and `Player` simultaneously rendered in both views.

Entity 2 movement changed its `C2S 0x0066` count from 16 to 17 and the
secondary's `S2C 0x0068` count from 1 to 2. Capture #186 contains the direct
movement-report/relay pair; the server's current entity-2 position changed
from `(4268,-10)` to `(4275,-16)` after the following stop report. The wire
relay is verified, while the newer 23:36 section withdraws physical input
window attribution.

One client had already been moved and its camera altered by the user. These
screenshots prove reciprocal rendering and relay only; neither default spawn
nor default camera semantics may be inferred from them.

The dashboard's global transition state also had a multi-client attribution
bug: it could combine primary process-memory watches with another active
connection's protocol state. Source now derives a transition per player,
restricts memory watches to the primary, aggregates the global multi-client
summary, and exposes `content.active_entity_id`. Python compilation and
dashboard JavaScript syntax checks pass. The newer 23:36 restart verified that
the updated API/UI is live. See note 67.

## 2026-07-17 23:17 restart-4 end-to-end repetition and task safety

Clean restart 4 independently repeated the complete natural route on client
PID `138892`. The exact Frida button-reader contract
`ButtonId=33 / caller=0x005E3F14 / params=1,-1` caused natural RedRon growth;
the user then clicked the actual outside door. Capture
`captures/packets_20260717_230719.txt` recorded:

```text
C2S #38 0x0019[00] -> S2C #38 0x000D[00]
-> S2C 0x0004[01] x5
-> C2S #44 0x0064[01] -> S2C #44 0x0064 (27B, no 0x006E)
-> resumed bidirectional heartbeats
```

The API state progressed
`pathouse_stable -> pathouse_exit_ready -> plaza_healthy` and ended at
`scene=110 / phase=4 / dispatch_mode=1 / self_actor_id=1`, with state-1 ready,
recent heartbeat, and no engine error. Evidence:
`artifacts/dynamic-analysis/restart4_plaza_healthy_20260717_2317.bmp` and note
64.

One existing client had already been moved and its camera changed by the user.
That visual run proves Plaza rendering and continued play, but is excluded from
initial spawn-point and default-camera baselines. Those need a fresh untouched
client before positional interpretation.

An automation incident was also closed. A misspelled
`REQUEST_UI_ACTION.json` marker previously fell through the elevated scheduled
task's default stop-all path. The correct marker is
`REQUEST_AZROK_UI_ACTION.json`. `tools/stop_azrok_elevated.ps1` now refuses any
unknown `REQUEST_*` marker before destructive fallback. A live negative test
with `REQUEST_TYPO_GUARD_TEST` returned task failure while preserving PID
`138892` and the shared server.

## 2026-07-17 22:55 clean-retry Plaza reproduction

The clean-restart natural outside-door exit is now repeated and stable. The
user clicked the actual PatHouse exit after natural RedRon growth. Capture
`captures/packets_20260717_223625.txt` recorded the authoritative sequence:

```text
C2S #94 0x0019[00] -> S2C #94 0x000D[00]
-> five request-driven 0x0004[01] samples
-> C2S #100 0x0064[01] -> S2C #100 0x0064 (27B, no 0x006E)
-> resumed bidirectional heartbeats
```

The live result is `scene=110 / phase=4 / dispatch_mode=1 / self_actor_id=1`,
with `state1_dispatch_ready=true`, native Nexus 200, no engine error, and
continued heartbeats. Visual evidence:
`artifacts/dynamic-analysis/restart3_plaza_success_20260717_2253.bmp`.

The immediately preceding run reached the same wire boundary but stalled on
the Plaza loading frame after its 27-byte `S2C 0x0064`: mode stayed 0, self was
not committed, and heartbeats stopped although the Win32 message pump remained
responsive. The successful retry's semantic `0x0064` fields are identical;
only time bytes differ. This is therefore classified as an intermittent client
engine post-load race/deadlock, not a server-packet regression. See note 63 and
`artifacts/dynamic-analysis/x32dbg_hang_snapshot_137076_20260717_222446_385.json`.

The API/dashboard source now derives an explicit transition/game-loop health
state from scene, phase, dispatch mode, self actor, `full_0064_sent`, heartbeat
idle time, and engine error state. The subsequent restart 4 activated and
live-verified this path through `pathouse_stable`, `pathouse_exit_ready`, and
`plaza_healthy`; see the newer 23:17 section and note 64.

The strongest far-left exit candidate is `gate_mun_MDL_048` (`gate_mun.MDL`)
with colocated `doorframe_01`. `dm_door_0003_057` is the bathroom/internal door.
`mirror_01` is the wardrobe/mirror object; its static type-`0x20`, action-`0x6F`
binding to the visible gate remains unverified.

## 2026-07-17 22:12 clean-restart reproduction

Natural evolution now reproduces after a full clean server/client restart with
the unmodified executable and native `-NX200`. The coordinate click was
replaced by the exact verified button-reader contract:
`FUN_005E3EE0` return address `0x005E3F14`, Sleep button `0x21` (33), observed
parameters `1/-1`, injected once. The client displayed `레드론으로 성장!` and
sent two 196-byte snapshots whose evolution byte changed from 0 to 1
(`captures/packets_20260717_214547.txt`, C2S #156 and #162). The second was
persisted as `server_state/506c61796572_c2s0007.bin`.

The post-growth state remained `scene=100 / phase=2 / Nexus=200`, with
`150,057,856` arena bytes free, continuing heartbeats, and no E1201. Evidence:
`artifacts/dynamic-analysis/restart2_redron_growth_20260717_221222.bmp` and
note 62. The subsequent natural outside-door exit and stable Plaza result are
now repeated above and detailed in note 63.

## 2026-07-17 21:26 authoritative update

The full natural growth-to-Plaza path is now live-verified with zero
executable/runtime code patches. The supported restoration profile uses the
engine's legal native `-NX200` command-line option, bootstrap evolution 0, and
the shipped content state. A real sleep action changed the client-owned
`ProtocolState+0x130` from 0 to 1, rendered RedRon, persisted evolution 1, and
reported no allocator failure or E1201. The user then manually clicked the
visible outside door and produced:

```text
C2S 0x0019[00] -> S2C 0x000D[00] -> S2C 0x0004[01] x5
-> C2S 0x0064[01] -> S2C 0x0064 only -> outdoor Plaza
```

The result is `scene=110 / phase=4 / dispatch_mode=1`, with continued
heartbeats and Plaza movement. No `S2C 0x006E` or memory shortcut was used.
Evidence: `captures/packets_20260717_211306.txt`,
`artifacts/dynamic-analysis/FRIDA_ELEVATED_20260717_212202_758.txt`, and note
62. Nexus 40 remains a useful PatHouse/OX/multiplayer baseline, but this same
natural evolution exhausted that arena and raised E1201. The exact original
2008 Nexus argument and minimum sufficient value remain unverified.

2026-07-17 15:44 operations update: the existing control URL
`http://127.0.0.1:9300` now serves the reworked Korean monitoring dashboard;
scheduled launches still do not open a new browser tab. A clean restart
live-verified the additive `/api/state` `multiplayer`, `content`, and `events`
surfaces with one connected client, and Edge rendered the full `1920x1080`
page successfully. Evidence:
`artifacts/control_dashboard_20260717_1544.png`.

The dashboard now exposes room-grouped multiplayer rosters, per-client
RX/TX/relay/unknown counters, join/leave/room/content events, direction-specific
opcode meanings and decoded fields, filters, and risk/unknown markers. Growth
monitoring includes persistent 196-byte content saves, Gym stat `0x20`, and
the PatHouse outside gate (`evolution >= 1`). Log auto-follow advances only
when the operator is already near the bottom, so inspecting older packets no
longer gets pulled back to the newest row.

`S->C 0x0065` remains forbidden after self actor creation: its verified
handler resets the fixed self/full actor state as well as the remote list.
Describing it as an original pre-self roster resync is still only a hypothesis.
The live server instead uses `0x0066`/`0x0068` peer upserts and targeted
`0x0067` departure, while the GUI warns and confirms before a manual `0x0065`.

2026-07-17 14:30 update: the zero-patch/native-`Nexus=40` route now has live
two-client Plaza multiplayer proof.  Two clients entered the same outdoor
Plaza (`scene=110`, `phase=4`, `dispatch_mode=1`), rendered `Azrok1` and
`Guest` at distinct positions in both windows, and remained responsive.  A
manual click produced repeated C2S `0x0066` movement reports with corresponding
peer S2C `0x0068` position relays.  No S2C `0x0065` was sent.

Important safety correction: S2C `0x0065` is not a safe remote-roster flush.
x32dbg and Ghidra prove that it tears down the fixed self actor plus the remote
container; the next active-Plaza minimap frame faults at `0x005F3AF4`.  The
server now uses peer-only `0x0066`/`0x0068` upserts and targeted S2C `0x0067`
for departure handling. The departure path is now live-verified: closing real
entity 3 produced exactly one four-byte `0x0067[03 00 00 00]`, removed only
the remote model, and the surviving client continued heartbeats. See
`docs/research/multiplayer/51_state1_mode_and_0065_self_teardown_crash_20260717.md` and
`docs/research/multiplayer/52_state1_0067_departure_lifecycle_20260717.md`.

2026-07-17 update: the zero-patch launcher/server path now reaches a stable
state-1 OX quiz scene after the corrected `S->C 0x0064` date block. This is
real progress but it is NOT Plaza. Do not use the older `0x0A = Plaza` label.
See `docs/research/world/24_0064_datefix_and_ox_entry_2026-07-17.md`.

2026-07-17 reproducibility update: the no-binary-patch Hansol prelude now has
both a repeatable OX diagnostic and a live Plaza route. Wait for the PatHouse
baseline, send `S->C 0x000D`, answer the five natural `C->S 0x0016[01]` requests
with `S->C 0x0004[01]`, then answer natural `C->S 0x0064` with authoritative
`S->C 0x0064` only. Omitting `S->C 0x006E[00,00]` keeps `scene=110/phase=4`
and visibly enters outdoor Plaza; the extra 0x006E is retained only for OX
diagnostics. See `docs/research/world/29_000d_dynamic_core_and_request_driven_calibration_2026-07-17.md`
and `docs/research/world/30_006e_ready_commit_forces_ox_2026-07-17.md`.

### 2026-07-17 authoritative correction

- The current launcher runs with **zero executable/runtime code patches** and
  the engine's native `-NX200` restoration profile. Nexus 40 remains an
  explicit low-arena A/B baseline, not the full-content operational default.
- `azrok_launcher.py` supplies WDL variables and starts the live
  `AzrokServer`; `azrok_server.py` is not merely an archived IAT-hook launcher.
- Bootstrap `S->C 0x0004[00]` packets are a server-side quiescence marker.
  They do not enter the client Hansol calibration accumulator. The real
  transition uses exactly five paced `S->C 0x0004[01]` samples.
- The corrected authoritative `S->C 0x0064` layout is enabled. Controlled
  `entry_kind` values `0x00`, `0x0A`, `0x0B`, and `0x14` all reach stable OX;
  none is the missing Plaza selector.
- The packet-faithful Plaza harness is `0x0003 (space-root, when needed)
  -> 0x000D -> request-driven 0x0004[01] x5 -> natural C->S 0x0064 ->
  authoritative S->C 0x0064 only. Do not send S->C 0x006E in the supported
  route: its ready commit queues OXQuiz.wmb. Do not replay a fresh `0x0007`
  zone bundle in this door transition.
- Before `0x000D`, the four protocol-subobject vtable pointers used by its
  cleanup calls must pass preflight. Header 4/4 is necessary but not sufficient
  by itself. A second read-only, fail-closed preflight covers all 78 child PANEL
  handle fields touched by cleanup. Both `all_zero` (`78/78 null-safe`) and the
  known live `clean_pan_create_fingerprint` (`57 pan_create / 21 null`, readable
  PANEL/BMAP handles) pass. Other readable nonzero handles are `UNKNOWN`, not
  proven PANEL provenance; unreadable PANEL/bitmap targets are `INVALID`. Both
  states block `0x000D`.
  The old faults are not evidence that an entry byte was unsafe.
- `0x000D` enqueues room code `0x6E`; the room dispatcher/loader chain chooses
  the initial Hansol/Plaza space. Later `S->C 0x0064` applies the self actor to
  that space and is not a destination selector. A successful `S->C 0x006E`
  ready commit is a separate OX selector and is omitted from the Plaza route.
- The legacy `C->S 0x0019` process-memory shortcut is disabled by default. It
  is available only with `AZROK_LEGACY_0019_MEMORY_SHORTCUT=1` for diagnostic
  comparison and is not part of the supported packet path.

## CONFIRMED PLAYABLE (2026-04-01)

> **Historical baseline, narrowed by note 62**: zero-patch Nexus 40 proved the
> PatHouse/OX/multiplayer foundation and eliminated the old workaround cascade.
> The current full-content restoration launcher remains zero-patch but uses the
> engine's native `-NX200`, because natural evolution exhausted the 40 MiB
> arena.

The game reaches a fully playable state:
- 3D PatHouse room renders with floor, walls, windows, furniture
- Character (pink Azrok) stands in the room center
- Full HUD: top bar, bottom menu icons, left status panel
- Tutorial text displays ("대전하기 위 왼쪽 하단 B를 클릭할을 눌러봐!")
- Heartbeat continues stably, no crashes
- Memory: ~263MB (vs 189MB pre-load)

## Working Configuration

### Launchers

| File | Role | Status |
|------|------|--------|
| `azrok_launcher.py` | WDL variable injection — **current launcher** | Active |
| `azrok_server.py` | Live TCP server, packet protocol, control state | Active; started by `azrok_launcher.py` |

> **Note**: the supported bootstrap default is evolution 0. The client raises
> its runtime `+0x130` naturally after load through a care action. Starting
> with bootstrap evolution 1 is not the supported path.

### Binary Patches

**Current binary/runtime code patches: none.** The launcher uses Acknex's native
`-NX200` parser option. Nexus 40 is sufficient for the verified PatHouse, OX,
and earlier multiplayer baseline, but the shipped natural evolution exhausted
it. The legacy Nexus memory-write path remains diagnostic-only and is not part
of the working configuration.

### Removed Patches (previously required, now eliminated)

| Patch | VA | Reason Removed |
|-------|----|----------------|
| IAT hook on `connect()` | — | Replaced by WDL variable injection |
| Dispatch flag bypass (`JZ → NOP NOP`) | 0x591DC7 | OnConnect fires naturally with correct connection |
| Gate reset NOP | 0x0050CC07 | Server sends S->C 0x0007 proactively; 0x0002 not sent at login |

### The Domino Effect (Why IAT Hook Required 3 Extra Patches)

The IAT hook made `connect()` succeed synchronously, bypassing the async
WSAEventSelect path. This meant `CClientPeer::OnConnect` was never called,
which meant the dispatch flag never set, which required a NOP patch, which
required sending 0x0002, which reset the gate, which required a gate NOP.
WDL injection breaks the chain at the root.

```
IAT hook → OnConnect never called → dispatch flag stays 0 → needed NOP
  → needed 0x0002 → gate reset to 0 → needed gate NOP
```

### Server Protocol

```
C->S 0x0000 (login hello, 106B)
S->C 0x0016 + S->C 0x0004[00] x5 (heartbeat + bootstrap pacing/quiescence marker)
S->C 0x0000 (login response, 0x183B, payload[1]=0x01)
... heartbeats ...
S->C 0x0003 (PatHouse path) + S->C 0x0007 (472B bundle)  [PROACTIVE — no C->S 0x0007 needed, no 0x0002]
C->S 0x0001 (transition ack, 0B)
C->S 0x0008 (state sync, 41B zeros)
C->S 0x0007 (repeated, IGNORED by server)
... heartbeats continue, game is playable ...
```

**Key protocol change**: The server sends S->C 0x0003 + S->C 0x0007 proactively
without waiting for C->S 0x0007 and without sending S->C 0x0002. With WDL
injection, `CClientPeer::OnConnect` fires naturally and the dispatch flag is
already 1 when the bundle arrives.

### Critical Protocol Details

| Opcode | Direction | Size | Key Detail |
|--------|-----------|------|------------|
| 0x0000 | S->C | 0x183B | payload[1]=0x01 → state 0x6B. payload[1]=0x00 → state 0x6C (also loads but different path) |
| 0x0002 | S->C | 0B | Empty payload. Room transition trigger only. Do NOT send during initial login — gate (gm+0x31946) has no non-zero write path after construction, sending 0x0002 at login permanently zeros it |
| 0x0003 | S->C | variable | `\x01` + NUL-terminated space-root. It stages a resource root but does not choose the destination scene. `0x000D` enqueues room code `0x6E`, whose dispatcher/loader chain determines the space. |
| 0x000D | S->C | 1B | Payload `00` starts the room transition and enqueues room code `0x6E`. Admission requires four matching header vptrs plus a fail-closed scan where all 78 cleanup child-handle fields are zero. Readable nonzero is `UNKNOWN`, not PANEL provenance, and blocks alongside `INVALID`. |
| 0x0004 | S->C | 5B | Bootstrap `00 + timestamp` is only a server emission/quiescence marker. Hansol calibration is exactly five `01 + timestamp` samples; the client mutates the fifth buffer to `FF` internally. |
| 0x0007 | S->C | 472B | Zone setup. +0x125 must be 0xFF (not 0x00). +0x1D4 selectors must be 0xFF for clear |
| 0x0005 | S->C | 6B | Post-load state. +0x02 must match 0x0007 +0x07 |
| 0x000A | S->C | 150B | Keyed stat registry. Group0 = 11 current/max pairs (binary defaults 1000/2000) |
| 0x000B | S->C | 62B | XP curve. 31 x u16. Binary defaults confirmed working |
| 0x0007 | C->S repeated | - | Server MUST ignore. Responding causes infinite reload loop |
| 0x0001 | C->S | 0B | Transition ack. DO NOT echo back |
| 0x0064 | S->C | 27B | Enabled authoritative-self reply with corrected layout: entry_kind +0x00, self id +0x01, X +0x06, Y +0x0A, selectors +0x12/+0x13, valid clock +0x14..+0x1A. It applies the self actor to the space already loaded; it does not select that space. Accepted entry kinds `00/0A/0B/14` all reach controlled OX. |

### Removed Patches (non-binary, cleanup)

All rescue/guard patches removed — server protocol handles naturally:
- state1_opcode100_null_guard
- scene_sky/water_null_guard
- state1_tail_close_guard
- scene_postload_ready_force
- scene_stage6/wrapper_vcall_guards
- popup hard/UI bypasses
- scene_local_entity_guard, scene_self_visual_guard

## Key Discoveries

### 1. WDL Variable Injection

`azrok_launcher.py` writes the server address to the WDL engine variable at
`engine+0x9a0` before `FUN_004edb10` reads it. The pointer chain:

```
0x006e8430 → engine object → +0x9a0 → STRING struct → +0x0c → CString buffer
```

The STRING struct uses `CFixedStringT<char,64>` — 64-byte inline buffer.
For empty strings `alloc_len=0`, requiring a fallback write to the inline buffer.

### 2. CGameManager Is Stack-Allocated

`CGameManager` is stack-allocated in the main loop (`FUN_004ecab0`), NOT global.
Found at 0x00163280 via vtable scan. vtable = 0x0069D0A4.
`find_real_gm()` scans process memory for the vtable pointer, validates with
`gm+0x31792` (scene mode) and `gm+0x31946` (gate).

### 3. Session Gate Mechanism (gm+0x31946)

- CGameManager constructor sets gm+0x31946 = -1 (0xFFFFFFFF)
- FUN_00509200 checks `if (this+0x31946 != 0)` → calls FUN_0050a0f0
- FUN_0050a0f0 is the room code dispatcher (dequeues from button queue)
- S->C 0x0002 handler (DispatchState0Common_S2C case 2) resets gate to 0
- **6 locations** that write `mov [eax+0x31946], 0`:
  - 0x0050AFBF, **0x0050CC07**, 0x0050D395, 0x0050D3C2, 0x0050D4F8, 0x0060691F
- With WDL injection, 0x0002 is never sent at login, so gate stays -1 naturally

### 4. Launcher Architecture

```
starmaru.exe (patcher: regsvr32, version.dat, patch downloads)
  → open.exe  (web client — mooondal engine, NOT a launcher for Azrok.exe)
    → autoLauncher.dll (COM, "run" command → ShellExecuteA)
      → Azrok.exe "IP:PORT user auth"
```

`open.exe` is a separate mooondal-engine game client, not merely a launcher.
`starmaru.exe` is the patcher.

### 5. HandleS2C_0002 Connection to C->S 0x0007

`HandleS2C_0002_TransitionPrimary` sends C->S 0x0007 via
`FUN_005a4770(0,1,7)` — vtable+0x10. With WDL injection the server sends 0x0007
proactively so this path is never needed.

### 6. FUN_0050a880 — The Missing Link

`FUN_0050a880` bridges `gm+0x31aad` → ButtonQueue. This was the missing link
in the PatHouse bootstrap chain.

### 7. Reload Loop

- If server responds to repeated C->S 0x0007 with full bundle, client re-enters loading
- Memory grows continuously (189→292→309MB)
- Fix: ignore repeated 0x0007 (respond only to first)

### 8. Login Response State Split

- S->C 0x0000 payload[1] determines initial state path:
  - `payload[0]==0, payload[1]==0` → local state 0x6C
  - `payload[0]==0, payload[1]!=0` → local state 0x6B
- payload[1]=0x01 confirmed working for playable state

### 9. S->C 0x000A Group0 Structure

- 22 u16 values = 11 current/max pairs, NOT flat stat values
- Key space: (1,2),(4,5),(7,8),(10,11),(13,14),(16,17),(19,20),(22,23),(25,26),(28,29),(31,32)
- Binary defaults (1000/2000 alternating) confirmed working

## Game Manager Addresses

| Pointer | Value | Purpose |
|---------|-------|---------|
| 0x006e8430 | → engine object | Acknex engine object (NOT game manager) |
| 0x17b820 | static | Dispatch object (CClientPeer). +0x163E4 = dispatch_state |
| 0x163280 | observed via Frida | Real game manager (CLogicManager). Offsets like +0x31946 are relative to this |

## Open Questions / Next Steps

1. **Full content testing**: PatHouse movement, doors, dialogue, Plaza, and the
   Gym dumbbell chain have interaction evidence; enumerate and restore every
   remaining playroom/library/gym/magic/kitchen/shop content completion path.
2. **C->S 0x0017**: observed during natural content flow as stat/property delta
   reports; continue naming the remaining kind/stat contracts.
3. **Natural outside route**: completed. Repeat from a completely restarted
   client/server, run the evolution-0 negative control, and continue through
   Plaza local-room content.
4. **S->C 0x0000 content**: Still mostly zeros beyond payload[1]. Full structured cache needed for feature-complete server
5. **0x0007 stat bag wire order**: init.csv row order ≠ wire order. Current minimal stats work but are not accurate
6. **Multi-actor expansion**: two-client Plaza spawn/render/movement and
   targeted departure are proven. Continue chat/action/equipment relays and
   scale tests within the client's 100-remote-actor ceiling; never use
   post-self `S->C 0x0065` as a roster flush.
7. **0x000D child-panel provenance**: the fail-closed 78-field scan currently admits only `all_zero`. Determine valid PANEL provenance for any future nonzero child without weakening `UNKNOWN`/`INVALID` blocking.
8. **Evolution 3 double-bundle**: FIXED — set zone_request_count=1 after proactive S->C 0x0007 send so subsequent C->S 0x0007 arrivals are ignored.

## Protocol-Correct Target

With WDL injection the game is protocol-correct for the login→PatHouse flow.
The current minimal intended door transition is:

1. Wait for the client-owned natural `C->S 0x0019[00]` after its post-load
   evolution and user outside-door click. Respond with `S->C 0x000D[00]`;
   never substitute the legacy client-memory shortcut.
2. If the space root must change, send `S->C 0x0003 [01] +
   "Data\Space\Plaza\0"`. This changes a resource-root string; it is not by
   itself proof of the destination scene.
3. Verify the four protocol-subobject header vptrs match their expected values,
   then require the 78 cleanup child-handle fields to report `all_zero`
   (`78/78 null-safe`). Fail closed on `UNKNOWN` readable-nonzero values because
   readability is not PANEL provenance, and on every `INVALID` target. Then
   send `S->C 0x000D [00]` on a separate tick; it enqueues room code `0x6E`,
   and the downstream dispatcher/loader chain determines the space.
4. Send five paced `S->C 0x0004 [01 + timestamp]` samples. The client mutates
   the fifth packet buffer to `FF` internally and latches readiness.
5. Wait for the natural `C->S 0x0064 [01]` request.
6. Reply with the corrected authoritative `S->C 0x0064` only. Do not send
   `S->C 0x006E [00,00]` on the Plaza route; that packet commits the ready flag
   and queues the OX room.

Do **not** replay `S->C 0x0007` (or its `0x0005/0x000A/0x000B` companions)
inside this door transition. `0x000D` already enqueues the room request and a
fresh zone bundle can duplicate the request or re-enter broad initialization.

**S->C 0x0064 — authoritative self (corrected and enabled):**

| Field | Offset | Type |
|-------|--------|------|
| entry_kind | +0x00 | u8 |
| self_id | +0x01 | u32 |
| reserved | +0x05 | u8 |
| pos_x | +0x06 | u32 |
| pos_y | +0x0A | u32 |
| selectors | +0x12/+0x13 | 2 × u8 |
| clock | +0x14..+0x1A | year, zero-based month, day, hour, minute, second |

The builder uses this corrected 27-byte layout. Controlled `entry_kind`
`00/0A/0B/14` runs with the extra 0x006E diagnostic reply all produce stable
OX, so the entry byte is not the missing Plaza selector. It is an application
value for the self actor in the space that the room-code/loader chain already
loaded. The supported Plaza route sends the authoritative 0x0064 without 0x006E.

**S->C 0x0006 — ResetLocalClockAndSeed**: May be required for proper time
synchronization. Not yet sent; investigate as part of feature-complete server.
