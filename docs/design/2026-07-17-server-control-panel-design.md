# Azrok Server Control Panel — Design

**Date:** 2026-07-17
**Status:** approved, implementing

## Problem

Every open task (P0–P5 in `HANDOFF_2026-07-17_DYNAMIC_ANALYSIS.md`) is currently a loop of:

> edit `azrok_server.py` → restart → launch game → wait for PatHouse → observe a `print()` → guess → repeat

Server state lives in a `proto_state` dict mutated across ~15 sites inside `_handle_client`, visible only as terminal spew. Client state is readable (`collect_runtime_state` already exists) but is only dumped as one long unreadable line. There is no way to send a packet without editing code.

Two concrete costs already paid:
- `azrok_server.py:1789` opens `packets_log.txt` with mode `'w'` — **every run destroys the previous capture**. This is how the 2026-04-01 `C→S 0x000C` evidence (referenced by docs at lines 382/410/438) was permanently lost.
- The Hansol recipe (7 steps, fully decoded, never run) would take a code edit + full relaunch per attempt.

## Goal

Collapse that loop to a click — or a CLI call an agent can make.

## Non-goals

- Session replay / timeline scrubbing UI. Capture retention is in scope; a retrospective analysis UI is not. Log files suffice.
- A memory browser. That is x32dbg's job.
- Writing client memory. Conflicts with protocol-first; x32dbg covers the rare need.

## Approach: in-process HTTP/JSON API, three consumers

`azrok_server` already runs **inside** `azrok_launcher`'s process (`import azrok_server` → `AzrokServer(port)`). `proto_state` and `hProcess` are directly reachable — no IPC needed.

```
                              ┌─ web page      (browser, polls /api/state @250ms)
azrok_control.ControlServer ──┼─ azrok_ctl.py  (CLI, subcommands like tools/auto_azrok_ui.py)
   stdlib ThreadingHTTPServer └─ agent         (calls the CLI, or HTTP directly)
```

API-first. The CLI is a thin client over the same endpoints, so the agent path costs nothing extra.

**Stdlib only.** The project is pure ctypes + stdlib; adding Flask for a debug tool is not worth breaking that. Polling at 250ms is ample — WebSocket from stdlib is painful and buys nothing here.

Rejected: separate GUI process + IPC (throws away direct state access, needs a second CLI); terminal TUI (awkward for "click to send", not API-first).

## The one load-bearing refactor: a single send chokepoint

Today there are **two** send sites — `azrok_server.py:1907` (main response path) and `:1926` (login packet). Pause/step and injection are impossible without funnelling both:

```python
def _emit(self, conn, data, origin='auto', note=''):
    if self.paused and origin == 'auto':
        item = {'data': data, 'origin': origin, 'note': note,
                'ev': threading.Event(), 'action': None}
        with self.ctl_lock:
            self.pending_out.append(item)
        item['ev'].wait()               # blocks the handler thread — this IS the breakpoint
        if item['action'] == 'drop':
            return False
    conn.sendall(data)
    return True
```

Blocking the client handler while paused is intentional: it is a protocol breakpoint. Heartbeats stall; that is the point. Manual injection (`origin='manual'`) bypasses the gate — it is already a deliberate act.

## Components

| file | role |
|---|---|
| `azrok_control.py` (new) | `ControlServer` — HTTP API + embedded single-page UI |
| `azrok_ctl.py` (new) | CLI client over the same API |
| `azrok_server.py` (modify) | `_emit` chokepoint; `paused` / `pending_out` / `ctl_lock`; `inject()`; `run_macro()`; timestamped capture |
| `azrok_launcher.py` (modify) | start `ControlServer` alongside the game server |

## API

| method | path | body | effect |
|---|---|---|---|
| GET | `/` | — | the HTML page |
| GET | `/api/state` | — | full snapshot (below) |
| POST | `/api/send` | `{opcode, payload}` | inject S→C, hex payload |
| POST | `/api/macro` | `{name}` | run a named recipe |
| POST | `/api/pause` | `{enabled}` | toggle the gate |
| POST | `/api/step` | — | release one pending packet |
| POST | `/api/drop` | — | drop one pending packet |
| POST | `/api/protostate` | `{key, value}` | edit a `proto_state` key |

Snapshot shape:

```json
{
  "server":  {"port":9200,"running":true,"clients":1,"uptime":123.4,"capture":"captures/packets_20260717_035512.txt"},
  "paused":  false,
  "pending": [{"origin":"auto","opcode":"0x0016","len":5,"hex":"..."}],
  "proto_state": {"char_created":true,"calib_0004_count":5,"...":"..."},
  "packets": [{"seq":24,"t":"14:03:21.412","dir":"C->S","opcode":"0x006C","len":4,"hex":"00000000"}],
  "watches": {"gm":"0x00A1B2C0","flag_31c71":1,"flag_31c72":0,"scene_ready_latch":1,"nexus":200}
}
```

## Watches — deliberately tiny

Reuse what exists: `find_real_gm(hProc)` (cached + self-verifying) and `collect_runtime_state(hProcess, gm, 0, 0)`. Surface only the fields that matter for current work, read-only, polled at 500ms (slower than packets — `collect_runtime_state` issues ~30 `ReadProcessMemory` calls):

`gm`, `flag_31c71` (readiness latch), `flag_31c72` (Hansol flag), `flag_31c73`, `scene_ready_latch` (`gm+0x31946` gate), `scene_opcode`, `self_actor_id`, `logic_state`, plus `nexus` (`0x102FC540`).

The point is not memory inspection — it is **causality in one view**:

```
14:03:21.412  S→C 0x0004 [FF ...]
14:03:21.6xx  flag_31c71: 0 → 1        ← did our packet actually set the latch?
```

x32dbg answers that only by freezing the game at a breakpoint. This answers it while the game runs.

`hook_base_global` is 0 in the launcher path, so `scene_stage`/`scene_stage_hits` degrade to 0. Expected — those are IAT-hook-era fields.

## Macros

Named packet sequences, defined as data, runnable in one call. Seeded with the two that matter now:

- `hansol` — the 7-step recipe from `23_recovered_opcode_details.md:288-303` (`0x000D` → calibration → `0x0064` → `0x006E`). Never yet run; this is P2's test harness.
- `bootstrap` — the known-good PatHouse bundle (`0x0000/0x0003/0x0007/0x0005/0x000A/0x000B`), for re-reaching a state quickly.

A macro is a list of `(opcode, payload_hex, delay_ms)`. Steps go through `_emit(origin='macro')`, so they bypass the pause gate.

## Capture retention (fixes the log-overwrite bug)

Write to `captures/packets_<YYYYmmdd_HHMMSS>.txt`. Keep writing `packets_log.txt` as well so existing docs and tooling that reference it still work — but history now survives.

## Error handling

- No client connected → `/api/send` returns 409 with a clear message; the UI disables the send button.
- Game process gone → watches return `{"gm": null}`; the UI greys the watch panel rather than showing stale values.
- Bad hex / unknown opcode → 400 with the parse error.
- Control server port busy → warn and continue; the game server must never fail to start because the debug UI could not bind.
- A macro step that fails mid-sequence aborts the rest and reports which step failed.

## Testing

The tool is a debug harness for a system that needs a running game, so the meaningful test is end-to-end, not unit:

1. Launch, confirm the page serves and `/api/state` returns valid JSON with no client connected.
2. Connect the game, confirm packets stream and `proto_state` tracks the terminal output.
3. Pause, confirm a heartbeat stalls in `pending`; step, confirm it flows; drop, confirm it does not.
4. Inject `S→C 0x0016` manually, confirm it appears in the capture.
5. Confirm `captures/` accumulates across two runs (the bug this fixes).
6. `azrok_ctl.py state` returns the same data as the page.

Steps 1 and 6 run without the game; the rest need a live client.
