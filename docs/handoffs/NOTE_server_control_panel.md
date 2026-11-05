# Note: server control panel (added 2026-07-17)

Short read for anyone working on `azrok_server.py`. Two things changed under you, one of them is a contract you can break by accident.

## 1. All outbound packets now go through `AzrokServer._emit()`

There used to be two `conn.sendall()` sites. They are now one chokepoint:

```python
def _emit(self, conn, data, origin='auto', pkt_num=0):
```

**If you add a new send, call `self._emit(conn, data)` — not `conn.sendall()`.** A direct `sendall` still works, but it becomes invisible: no logging, no capture, no packet ring, and it slips past the pause gate. That is the one way to silently break this.

`_emit` also does the logging that used to be inline at the call site, so don't re-log after calling it.

Origins: `auto` (normal server logic, gated by pause), `manual` (panel/CLI injection), `macro` (recipe step). Manual and macro bypass the pause gate on purpose.

## 2. Captures no longer overwrite

`packets_log.txt` was opened `'w'` every run — that is how the 2026-04-01 `C→S 0x000C` evidence (still referenced by docs at lines 382/410/438) was destroyed. Now each run also writes `captures/packets_<timestamp>.txt`. `packets_log.txt` still exists as "latest" so nothing that reads it breaks.

## 3. The panel — you can probably stop restarting

The launcher serves it in-process at `http://127.0.0.1:9300` (`--control-port 0` to disable). Same API behind the web page and the CLI, so scripts and agents drive the same surface. Exit code is 0/1, so you can branch on it. Browser opening is opt-in through `--open-control`; the fixed scheduled launch does not pass that flag and therefore does not open a browser automatically. Open `http://127.0.0.1:9300` manually when you want to watch the GUI.

```
python azrok_ctl.py state --watches         # gm, flag_31c71/72/73, latch, nexus — live, read-only
python azrok_ctl.py state --proto           # proto_state
python azrok_ctl.py packets --opcode 0x000C # filter the recent-packet ring
python azrok_ctl.py send 0x0004 01a5804c25  # inject S->C without touching code
python azrok_ctl.py macro hansol            # run the transition harness
python azrok_ctl.py macros                  # what recipes exist
python azrok_ctl.py set state_0064_entry_kind 0x0B  # select a controlled S->C 0x0064 entry byte
python azrok_ctl.py pause | step | drop     # hold outbound traffic at the gate
python azrok_ctl.py set calib_0004_count 0  # force a branch mid-run
```

`pause` blocks the client handler thread until you `step` or `drop` — it is a protocol breakpoint, so heartbeats stall while held. That is intended.

Macros live in `MACROS` at the top of `azrok_server.py`. A step is `(opcode, payload, delay_ms)` where payload is a hex string or a `lambda srv: bytes` for anything timestamped or state-derived. Adding one is a few lines; that is the cheap way to test a decoded recipe.

2026-07-17 correction: controlled packet-faithful runs with every accepted
`state_0064_entry_kind` (`0x00`, `0x0A`, `0x0B`, and `0x14`) reach the OX quiz
scene, not Plaza. The earlier `0x0B` crash was confounded by a different old
bootstrap/calibration route and is not evidence that the entry byte is unsafe.

## 4. Live operations dashboard (reworked and verified 2026-07-17 15:44)

The page at `http://127.0.0.1:9300` is now a Korean real-time operations
dashboard. The URL is unchanged and the scheduled launcher still does **not**
open a new browser tab; keep the already-open page and refresh it after a
server restart. This is presentation plus additive `/api/state` telemetry:
the existing HTTP control endpoints, `azrok_ctl.py`, pause gate, and `_emit()`
contract are unchanged.

The clean 15:44 restart was checked against the live API and an Edge
`1920x1080` render. `/api/state` contained `multiplayer`, `content`, and
`events`, reported one connected client, and the page rendered without a
layout failure. Visual evidence is
`artifacts/control_dashboard_20260717_1544.png`.

- The server/client cards expose health, entity/name, decoded room,
  scene/phase/dispatch mode, self actor, position/idle time, per-client
  RX/TX/relay counters, peer count, unknown C→S count, and content-save state.
- `방별 멀티플레이 로스터` groups the current clients by decoded room and
  presents actor-slot, visible-player, receive-buffer, spawn/leave/movement,
  and roster-mode metrics without implying that a packet was rendered merely
  because it was sent.
- The event timeline separates join/leave, room change, roster, and content
  save milestones from the raw packet stream.
- Packet rows use **direction-specific** meanings and bounded decoded fields.
  Direction, client, opcode, and free-text filters can be combined; unknown
  opcodes and risky packets are highlighted rather than silently named.
- The growth card shows configured evolution, the PatHouse outside gate,
  persisted 196-byte content state, sum validation, and Gym growth stat
  `0x20`. Unnamed stats remain numbered until their meanings are verified.

- Packet rows follow the newest packet by default **only while the viewport is
  already near the bottom**. Scrolling upward keeps the operator's reading
  position; returning to the bottom resumes following. `자동 스크롤` can be
  turned off without pausing the server, and the choice persists in browser
  local storage.
- `패킷 일시정지/재개` is the existing protocol breakpoint. It pauses only
  outbound `origin=auto` traffic. `1개 통과` and `1개 폐기` operate on the held
  queue exactly as before.
- The scene card interprets `phase_31792`, `scene_opcode`, `logic_state`,
  `flag_31c71/72`, and `self_actor_id`. Confirmed labels are deliberately
  conservative: scene `100`/phase `2` is PatHouse, scene `110`/phase `4` on
  the verified `0064-only` route is outdoor Plaza, and scene `111`/phase `5`
  is OX. The card still displays dispatch mode separately because a scene
  number alone does not prove that its multiplayer handlers are active.
- The Hansol readiness card explains every missing admission condition. The
  browser still asks for confirmation on a premature click, but the server
  independently defers the Hansol macro until all ten conditions pass.

The readiness display expects a stable PatHouse baseline:

```text
client connected
char_created == true
zone_request_seen == true and zone_request_count >= 2
calib_0004_count >= 5 (bootstrap 0x00 samples)
stable_heartbeat_count >= 2 (timing heuristic)
phase_31792 == 2
scene_ready_latch != 0
scene_opcode == 100
transition_vptrs_ok == true
transition_cleanup_children_ok == true  # all_zero or clean_pan_create_fingerprint
```

The ninth condition is a read-only header preflight for the four subobjects
used by `S->C 0x000D`: `popup_status=0x006ADA34`,
`popup_azron_info=0x006AE3C4`, `popup_calendar=0x006A7D6C`, and
`popup_state_list=0x006AD970`. It only compares the current pointers with the
expected client-image values; it never synthesizes, repairs, or writes them.
Green 4/4 is necessary but not sufficient by itself. The tenth condition is a
separate, read-only fail-closed scan of all 78 child PANEL-handle fields touched
by the `0x000D` cleanup path. `state=all_zero` (`78/78 null-safe`) and the
known live `clean_pan_create_fingerprint` (`57 pan_create / 21 null`, readable
PANEL/BMAP handles) both pass.
An unreadable PANEL/bitmap is `INVALID`; a readable nonzero handle is still
`UNKNOWN`, not proven PANEL provenance, and therefore also blocks the macro.
The `hansol` macro sends only `S→C 0x000D [00]`; its five `S→C 0x0004 [01]`
samples are emitted only in response to natural client `C→S 0x0016 [01]`
requests.

`auto_create_sent`, `self_actor_id`, and `logic_state == 2` are useful display
signals but are deliberately not admission requirements. In particular, the
self actor is created only after the authoritative `S->C 0x0064`, so requiring
it before the macro would be circular. The same ten-condition readiness is
enforced by the server before it emits the Hansol macro; all checks are
observational and do not change client memory or protocol state.

## Elevated game launch without repeated UAC

`Azrok.exe` requires elevation (a normal launcher fails with Win32 error 740),
but the controller and packet panel do not. Two fixed on-demand tasks were
registered once for this workspace:

```powershell
schtasks /Run /TN 'Azrok-Plaza-Launch'
schtasks /Run /TN 'Azrok-Plaza-Stop'
```

The launch task starts the normal server/control panel on `9207/9300`, but it
does not open a browser automatically. Open `http://127.0.0.1:9300` manually and
use this file's CLI commands as usual. The stop task closes only this workspace's
game and `azrok_launcher.py`, so start each experiment with one clean session.

## Files

| file | what |
|---|---|
| `azrok_control.py` | HTTP/JSON API and dashboard host (stdlib only) |
| `azrok_control_page.py` | the Korean operations dashboard page |
| `azrok_ctl.py` | CLI client over the same API |
| `azrok_server.py` | `_emit`, pause gate, `inject()`, `run_macro()`, `snapshot()`, `read_watches()` |
| `docs/superpowers/specs/2026-07-17-server-control-panel-design.md` | why it is shaped this way |

## Transition corrections you may care about

`S→C 0x000D` enqueues room code `0x6E`; its downstream room dispatcher/loader
chain determines the space. The later `S→C 0x0064 entry_kind` only applies the
self actor to the space already loaded, so changing that byte is not a Plaza
selector.

The supported Plaza reply mode is `AZROK_PLAZA_REPLY_MODE=0064`: after natural
`C→S 0x0064`, send authoritative `S→C 0x0064` only. The optional `both` mode
also sends `S→C 0x006E[00,00]`, whose ready commit queues `0x6F/OXQuiz.wmb`
and is retained only for OX diagnostics. A one-shot A/B request can be placed
in `artifacts/dynamic-analysis/REQUEST_PLAZA_REPLY_MODE.txt` before the
elevated launch task runs.

The old inbound `C→S 0x0019` handler shortcut that writes `gm+0x31c71` and
`gm+0x31c72` is **disabled by default**. It can be restored only with
`AZROK_LEGACY_0019_MEMORY_SHORTCUT=1` for a controlled diagnostic comparison.
That opt-in remains non-packet-faithful and is not the supported transition
path.

Fuller context, including four mislabelings in the older docs, is in `HANDOFF_2026-07-17_DYNAMIC_ANALYSIS.md`.

## Current multiplayer, room, and content view

`azrok_server.py` tracks each connection after a client-originated
`C→S 0x0065 <kind,direction,x,y>` room report. With at least two clients in
the same state-1 room, `C→S 0x0066` movement is translated into peer
`S→C 0x0068` position records. Join/room membership uses peer-only
`S→C 0x0066` actor upserts plus `0x0068` positions, and departure uses the
live-verified targeted `S→C 0x0067 <entity_id>`. The server does not invent a
reply for content buttons and this relay remains inert when no peer exists.

Do **not** restore the older room-change `S→C 0x0065` flush. Static and dynamic
analysis prove that its handler resets the fixed self actor/full actor state as
well as the remote list; sending it after the authoritative self has been
created crashes the active Plaza path. Its placement in an original pre-self
resync sequence remains a hypothesis, not a confirmed protocol fact. The
dashboard therefore labels manual `0x0065` transmission as a timing hazard and
requires explicit confirmation.

The snapshot also exposes the verified client capacity boundaries so they are
visible during multiplayer tests: 100 remote-actor slots (self plus at most
100 visible peers), an 8192-byte receive reassembly buffer, 8188 bytes after
the packet header, and 314 26-byte actor records by buffer arithmetic. The
100-slot actor pool is the earlier practical ceiling.

Growth/content monitoring is derived from persisted client-originated
`C→S 0x0007` 196-byte state. The dashboard shows save count/time, state reload,
sum validation, and Gym stat `0x20`. The clean 15:44 process also reported
`configured_evolution=1` and `outside_gate_ready=true`: PatHouse object
`mirror_01` (descriptor type `0x20`, action `0x6F`) is eligible to produce the
natural outside request. These fields are observations; they do not write the
client's memory.
