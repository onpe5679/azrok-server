# Azrok Plaza — Handoff: Dynamic Analysis Phase (2026-07-17)

> **LATEST OPERATIONAL HANDOFF (23:45 KST):** 먼저
> [`HANDOFF_2026-07-17_2345_CONTINUE.md`](HANDOFF_2026-07-17_2345_CONTINUE.md)를
> 읽고 그 문서의 시작 절차를 실행할 것. 아래 장문은 역사 기록이며 일부
> 중간 결론은 `docs/research/INDEX.md`와 최신 handoff에 의해 교정됐다.

**Mission:** restore full game functionality using Ghidra MCP (static) + x32dbg (dynamic) together.

**Hard constraint (unchanged):** run the game via launcher + server emulation with **zero binary patches**. Never re-add a patch to "fix" a crash — a crash means the server sent wrong data. Fix the data.

**Supersedes:** `HANDOFF_2026-03-31_*.md` (all three).

---

## Latest operations proof (2026-07-17 15:44) — monitoring dashboard

The existing `http://127.0.0.1:9300` control surface has been rebuilt as a
Korean multiplayer/content operations dashboard without changing its URL or
automatically opening a new browser tab. A clean server restart exposed the
new `/api/state` `multiplayer`, `content`, and `events` objects with one live
client, and an Edge `1920x1080` render completed normally. Evidence:
`artifacts/control_dashboard_20260717_1544.png`.

The page now makes the current restoration state observable in one place:
room-grouped rosters; per-client RX/TX/relay/unknown counts; scene, phase,
dispatch mode, self actor and position; join/leave/room/content events;
direction-specific opcode meanings and decoded fields; unknown/risk markers;
and persistent growth state including Gym stat `0x20` and the evolution-1
PatHouse outside gate. Packet following is near-bottom aware: scrolling up
holds the reading position, returning to the bottom resumes automatic follow.

Safety wording is deliberately narrow. `S->C 0x0065` is verified to reset the
fixed self/full actor state plus the remote list and is forbidden after self
creation in the current route. An original pre-self roster-resync role is an
unconfirmed hypothesis and must not be promoted to protocol fact. Current
multiplayer uses peer `0x0066`/`0x0068` upserts and targeted `0x0067` leave.

---

## Latest live proof (2026-07-17 14:30) — two-client Plaza multiplayer

The supported zero-patch, native `Nexus=40`, `0064-only` route now has live
two-client proof.  Two real clients reached outdoor Plaza on the same server,
both held `scene=110`, `phase=4`, `dispatch_mode=1`, and both remained
responsive.  The server sent only peer S2C `0x0066` actor upserts and S2C
`0x0068` positions; it sent no S2C `0x0065`.

After a manual click in the second client, every observed C2S `0x0066`
movement report was translated into a peer S2C `0x0068` position record.  Both
game windows visibly rendered the named actors `Azrok1` and `Guest` at distinct
positions.  This proves remote actor spawn, rendering, and movement relay, not
only socket connectivity.

The unsafe roster flush is now resolved rather than merely avoided.  A
programmatic x32dbg trace plus Ghidra analysis proves that active-Plaza S2C
`0x0065` tears down the fixed self actor and the remote container; the next
minimap frame faults at `0x005F3AF4`.  `azrok_server.py` no longer emits it
automatically.  See
`docs/research/51_state1_mode_and_0065_self_teardown_crash_20260717.md` and
`captures/packets_20260717_140843.txt`.

The targeted leave contract is also live-verified. Closing real entity 3
caused exactly one S2C `0x0067`, payload `03 00 00 00`, to the surviving
Plaza client. The remote `Azrok1` model disappeared, the `Guest` self model
remained, and heartbeats continued. See
`docs/research/52_state1_0067_departure_lifecycle_20260717.md` and
`captures/packets_20260717_143355.txt`.

---

## Latest live proof (2026-07-17 07:59:30-07:59:33)

The clean zero-patch session `Azrok.exe` PID `113980` now proves the complete
packet-faithful Hansol transition under elevated x32dbg observation. The trace
passed `0x00568770` transition entry, scene write `0x6E`, all four cleanup
call/returns, `gm+0x31C72` write, calibration reset, and transition return
without an exception. The observer resumed the debuggee after the final return;
it did not leave the game suspended.

After `S->C 0x000D [00]`, the client emitted five natural `C->S 0x0016 [01]`
requests. The corrected server answered each with exactly one `S->C 0x0004
[01+timestamp]`, then the client naturally emitted `C->S 0x0064 [01]` 455 ms
after sample five. The server replied with authoritative `S->C 0x0064`
(`entry_kind=0x0A`) plus `S->C 0x006E [0000]`. Final state was `scene=111`,
`phase=5`, `self_actor_id=1`, `Responding=true`, and continuing heartbeats.

Evidence: `captures/packets_20260717_075744.txt`,
`artifacts/dynamic-analysis/x32dbg_000d_trace_20260717_075744.jsonl`, and
`artifacts/dynamic-analysis/X32DBG_000D_CALIBRATION_0064_SUCCESS_20260717_075744.md`.

The prior apparent stall was two separate issues: the server did not reset its
bootstrap calibration counter on a manual `0x000D` inject, and an early trace
observer detached while the debuggee was still paused at `transition_return`.
Both are corrected. The server now arms request-driven calibration on `0x000D`
and the trace resumes before remaining attached.

---

## 2026-07-17 live correction: `0x0064 entry_kind=0x0A` is OX, not Plaza

After the `S->C 0x0064` date block was fixed, a clean zero-patch run stayed
alive and rendered a valid state-1 scene. The scene is the OX quiz space, with
`scene_opcode=111`, not the target Plaza/hansol space. The capture is
`captures/packets_20260717_053540.txt`; details are in
`docs/research/24_0064_datefix_and_ox_entry_2026-07-17.md`.

Fresh controlled sessions have now covered every accepted
`state_0064_entry_kind` / `AZROK_0064_ENTRY_KIND` value (`0x00`, `0x0A`,
`0x0B`, and `0x14`); all four reach OX. Do not encode that OX route into the
`C->S 0x0019` door handler as if it were the Plaza solution.

---

## 0. READ THIS FIRST — corrections that will waste your day if you miss them

Prior docs and prior sessions contain four confirmed mislabelings. All four were verified wrong on 2026-07-17 against the binary.

### 0.1 There is NO anti-debug. x32dbg attaches freely.

Earlier notes called VA `0x00650D6E` "anti-debug via SetUnhandledExceptionFilter + 0xC000000D". **False.** That address is inside `__invoke_watson` — the stock MSVC CRT invalid-parameter handler, which Ghidra auto-named. Full import scan of the original:

| API | call sites | verdict |
|---|---|---|
| `IsDebuggerPresent` | `__invoke_watson`, `___report_gsfailure` | CRT only |
| `TerminateProcess` / `UnhandledExceptionFilter` / `SetUnhandledExceptionFilter` | same + `_abort` | CRT only |
| `CheckRemoteDebuggerPresent`, `NtQueryInformationProcess`, `NtSetInformationThread`, `OutputDebugString`, `CreateToolhelp32Snapshot`, `Process32*`, `GetThreadContext` | **not imported** | — |
| raw PEB `fs:[0x30]` | **0 hits** | — |

**No ScyllaHide needed.** Just attach.

The old patch at `0x00650D6E` NOPed exactly 18 bytes: `PUSH 0xC000000D` + `CALL GetCurrentProcess` + `PUSH EAX` + `CALL TerminateProcess`. It deleted *the code that kills the process* so the game would survive a CRT invalid-parameter. A crash-suppressor masking bad server data. The pristine original reaches PatHouse with it intact — `__invoke_watson` never fires anymore. **Do not re-add it.**

### 0.2 `0x006C` in packets_log.txt is **C→S**, not S→C

`HandleS2C_006C_UpdateActorStateFields336_33A @ 0x00615410` is the **inbound** handler. It is NOT what the log shows. The log shows the *client sending*:

```
[C->S] #24 opcode=0x006C payload=4B total=8B
  0000: 04 00 6C 00 00 00 00 00
        └len┘ └op─┘ └─payload─┘
```

**`C→S 0x006C` is undocumented in every doc.** It is not in the consolidated doc's C→S contract list (`0x0000/0x0001/0x0004/0x0007/0x0008/0x0016/0x000C/0x0017/0x0064/0x0019`). Do not "solve" it by reading the S→C handler — that was already tried and it was wrong.

**Trap:** `0x6C` is *also* the lobby local scene code (`lobby.wmb` = `0x6c`, `FUN_0050b400(0x6c)`). The docs warn about this exact confusion for the neighbouring value (`04_runtime_patches_and_telemetry.md:87-88`: "`FUN_0050B400(0x6E)` is the internal local scene bootstrap dispatcher / it is not the same as sending network packet `0x006E`"). Find the actual C→S sender before theorizing.

### 0.3 `C→S 0x000C` does NOT block Hansol/Plaza — they are independent tracks

`protocol_consolidated_2026-04-01/03_*.md:§5-6` claims the `0x000C` byte map is "the main remaining server-contract blocker" and that Hansol comes after. **Not supported by the newer research docs.**

- `C→S 0x000C` fires **only from the equipment screen** — callers are `FUN_005BA900` (close equipment screen) and `FUN_005BC970` (equip confirm, menu codes `0x104`–`0x107`), gated by a dirty-check. It is not on the login → PatHouse → Hansol path at all.
- The decoded Hansol recipe (`23_recovered_opcode_details.md:288-303`) never touches `0x000C`.
- `00_current_status.md` — the newest research doc — never mentions `0x000C` anywhere.

### 0.4 `docs/research/04` and `docs/research/05` are historical, not current

`04_runtime_patches_and_telemetry.md` lists ~10 "active" patches. **All were retired.** It describes the abandoned `azrok_server.py` IAT-hook world. Reading it as current will actively mislead you. `05_crash_timeline_and_failure_modes.md` documents 12 crashes from that same abandoned stack.

---

## 1. Verified current state (2026-07-17)

### 1.1 Patch count — better than older docs claim

| target | count | detail |
|---|---|---|
| **Disk** | **0** | `Azrok.exe` = pristine 2008 original, SHA256 `39680DA744DF27CF13EAE03F675D91C301B3CA9332F6979CA4447FBA9908CABA` |
| **`Azrok.exe` code, runtime** | **0** | no instruction is rewritten |
| `Azrok.exe` **data**, runtime | **0 by default** | the two legacy `gm+0x31c71/72` writes are diagnostic opt-in only; see 1.1a |
| `ACKNEX.DLL` engine, runtime | **0 by default** | native `Nexus=40`; the four old Nexus=200 writes are diagnostic opt-in only; see 1.2 |

#### 1.1a The `0x0019` memory shortcut — sealed legacy diagnostic

Inbound `C→S 0x0019` is recorded, but the old writes to `gm+0x31c71` and
`gm+0x31c72` plus the proactive bundle are **disabled by default**. They can be
restored only for an explicit diagnostic comparison with
`AZROK_LEGACY_0019_MEMORY_SHORTCUT=1`. This opt-in writes game data rather than
code, but it is still non-packet-faithful and must never be treated as the
normal Plaza route.

**The dispatch flag bypass (`0x591DC7`) is NOT applied in the real flow.** The
`apply_runtime_patches` call belongs to the abandoned standalone IAT-hook path;
`azrok_launcher.py` does not call it. With WDL injection, `OnConnect` fires
naturally and sets the flag itself.

### 1.2 Native `Nexus=40` zero-patch baseline — repeatedly reproduced

The current default launcher performs no ACKNEX writes and leaves the engine at
its original `Nexus=40`. Repeated clean launches reproduce PatHouse and the
controlled OX transition without the four historical Nexus=200 writes. The
project therefore has a literal zero binary/runtime-patch baseline.

`--nexus-patches` retains the four old ACKNEX writes only for regression
comparison. It is diagnostic opt-in, not a requirement and not the supported
launch path.

### 1.3 Historical pristine capture — 2026-05-14

Reached PatHouse, 33 heartbeats, clean until user closed. `packets_log.txt` (256 lines) — complete opcode inventory:

```
C->S 0x0000 x1    C->S 0x0007 x1    C->S 0x0016 x31   C->S 0x006C x1
S->C 0x0000 x1    S->C 0x0003 x1    S->C 0x0004 x5    S->C 0x0005 x1
S->C 0x0007 x1    S->C 0x000A x1    S->C 0x000B x1    S->C 0x0016 x31
```

Notes:
- `S->C 0x0004` was sent **5 times**, matching the doc's packet-faithful requirement — but with `payload[0]=0x00`, not the binary-proven `0x01` (`azrok_server.py:2476` still builds `struct.pack('<BI', 0x00, ts)`). Both reportedly work; `0x01` is the proven dispatch path.
- **`packets_log.txt` line references in old docs are dead.** `23_recovered_opcode_details.md:186-190` and `02_packet_contracts_and_server_workflow.md:248-250` cite lines **382/410/438** for `C→S 0x000C` captures. The file is now 256 lines — the 2026-04-01 capture was overwritten by this pristine run. **That evidence must be re-captured.**
- `C→S 0x000C` never appeared in this run because the player idled in PatHouse. It needs equipment-screen interaction.

---

## 2. The big finding — the launcher chain

**We are not emulating the launcher. We are bypassing it with memory writes.** Confirmed by decompilation on 2026-07-17.

### 2.1 How the game is *supposed* to get its config

```
Original launcher: ShellExecuteA(Azrok.exe, "IP:PORT user auth")
    ↓
CRT: lpCmdLine = "IP:PORT user auth"
    ↓
WinMain(hInstance, hPrevInstance, lpCmdLine, nShowCmd)      @ FUN_004ecab0
    ↓
engine_open(lpCmdLine, 0)          ← Acknex parses the command line
    ↓
engine+0x998 / +0x9a0 / +0x9ac populated with STRING objects
    ↓
FUN_004edb10()  reads them
    ↓
FUN_00508b30()  parses → gm struct
```

Proof — the `WinMain` call site at `0x00657358` inside `___tmainCRTStartup`:

```
00657353: PUSH 0x400000       ; hInstance
00657351: PUSH 0x0            ; hPrevInstance
00657350: PUSH EAX            ; lpCmdLine      ← the command line
0065734f: PUSH ECX            ; nShowCmd
00657358: CALL 0x004e1447     ; → FUN_004ecab0
```

(Ghidra mis-typed `FUN_004ecab0` as 3-param; it is really 4-param `WinMain`. So its `param_3` = `lpCmdLine`.)

And inside `FUN_004ecab0`:
```c
DAT_006e8430 = engine_open(param_3, 0);   // param_3 == lpCmdLine
...
thunk_FUN_004edb10(...);                  // reads engine+0x9a0 / +0x998 / +0x9ac
```

`FUN_004edb10` decompiled:
```c
void FUN_004edb10(void) {
  thunk_FUN_00508b30(*(undefined4 *)(*(int *)(DAT_006e8430 + 0x9a0) + 0xc),
                     *(undefined4 *)(*(int *)(DAT_006e8430 + 0x998) + 0xc),
                     *(undefined4 *)(*(int *)(DAT_006e8430 + 0x9ac) + 0xc), 0);
}
```

### 2.2 What we do instead

`azrok_launcher.py:249-257`:
```python
# [2] Launch Azrok.exe (no command line args - Acknex misparses them)
ok = kernel32.CreateProcessW(
    exe_path, None, None, None, False,          # ← lpCommandLine = None
    CREATE_SUSPENDED, None, exe_dir, ...)
```
then `azrok_launcher.py:303-313` writes `engine+0x9a0/0x998/0x9ac` directly via `inject_wdl_string`.

### 2.3 "Acknex misparses them" — partly explained, still open

Two mechanisms are in play. The first is a classic Windows gotcha: **`lpCommandLine`'s first token is always consumed as `argv[0]`, even when `lpApplicationName` is supplied**, and `WinMain`'s `lpCmdLine` excludes it. So `lpCommandLine = "127.0.0.1:9200 player localauth"` reaches `WinMain` as `"player localauth"` — the IP silently vanishes. The correct form needs an `argv[0]` placeholder: `"Azrok.exe 127.0.0.1:9200 player localauth"`.

The second is Acknex's own parser, and it is the harder one. `azrok_launcher.py` now carries a probe mode for exactly this:

```
--native-cli          pass IP/user/auth on the command line instead of injecting
--argv0 {fullpath|Azrok.exe}
```

and its own comment records the outcome:

> *"With no command line Acknex starts its embedded game script. Passing the three values directly makes Acknex treat the auth token as LOCALAUTH.WDL."*

So even with `argv[0]` handled, **Acknex treats a bare argument as a WDL script filename** (`localauth` → `LOCALAUTH.WDL`). Getting the argv[0] byte right is necessary but not sufficient.

**Still open:** what form does the real launcher's `"IP:PORT user auth"` actually take such that Acknex populates `engine+0x998/0x9a0/0x9ac` instead of trying to load a script? Options worth checking, in order:
1. Decompile the launcher chain in Ghidra — `/New Traces/starmaru/autoLauncher.dll`, the `"run"` command's `ShellExecuteA` call. Read the **actual** `lpParameters` it builds rather than trusting doc 22's prose.
2. Look at how `engine_open` parses its cmdline inside `acknex.dll` (already imported in the project) — find what distinguishes an engine string arg from a script name. A prefix, a switch, a quoting rule.
3. If Acknex needs a switch form, the same mechanism may set nexus and kill the last 4 writes too.

Verify with `--native-cli`, watching the control panel (§3.3) to see whether the game connects to `127.0.0.1:9200` on its own.

---

## 3. Tooling

### 3.1 Ghidra MCP — use this, NOT headless

Headless costs **40–60s per query** (full JVM + project boot each time). MCP costs **1–2s**. This was learned the hard way.

```
1. Launch Ghidra GUI, open project `azrok.`  (note the trailing dot — files are literally azrok..gpr / azrok..rep)
2. Open /New Traces/Azrok_original.exe
3. mcp__ghidra-mcp__connect_instance(project="azrok")
   → {"connected": true, "transport": "tcp", "url": "http://127.0.0.1:8089"}
```

Tool groups load on demand: `function`, `listing`, `program` are default; also `analysis`, `comment`, `datatype`, `documentation`, `malware`, `symbol`, `xref` (150 tools total). `load_tool_group("xref")` etc.

Gotchas:
- `list_instances()` returns empty (it probes Unix domain sockets; this plugin is TCP). Go straight to `connect_instance`.
- MCP cannot query the `EXTERNAL:` address space. To xref an import, find its IAT slot in `ram` instead, or use `get_function_callers(name)`.
- **Two MCP extensions are installed** — `GhidraMCP` and `GhydraMCP` — both emit Module.manifest errors at startup and both stand up HTTP servers. This is the prime suspect for the Swing deadlock (`Timed-out waiting to run a Swing task`) that killed GUI auto-analysis twice. Recommend deleting `%APPDATA%\ghidra\ghidra_12.0.4_PUBLIC\Extensions\GhydraMCP`.
- Cosmetic error on open: `Archive file not found: azrok.gdt`. Harmless — the 66 data types were resolved *into* the program; this is just a dangling source-archive link from the migration. Remove the association or ignore.

### 3.2 Ghidra project layout

| program | role |
|---|---|
| `/New Traces/Azrok_original.exe` | **the baseline.** Pristine original, headless-analyzed 2026-07-17, all analysis assets migrated in. Use this. |
| `/Azrok_analyzed.exe` | old patched build. Superseded, keep as fallback. **Its internal program name is `Azrok.exe`** — project filename ≠ program name; this has caused confusion repeatedly. |
| `/acknex.dll` | engine, analyzed |
| `/New Traces/starmaru/{starmaru.exe, open.exe, autoLauncher.dll}` | the **original launcher chain**, analyzed. Relevant to §2. |

Version Tracking was never needed: both binaries are the same size with in-place-only patches, so **zero address drift** — all 14,358 original functions sit at byte-identical addresses. Migration was a plain address-for-address copy. The 4 "extra" functions in the patched build (`004de553`, `004df999`, `004e0bcd`, `006518e1`) are analysis artifacts.

Migrated: 268 function names, 67 comments, 66 data types, **218 `Note` bookmarks**.

**The 218 Note bookmarks are the most valuable asset in the project** — hand-written packet-structure documentation in categories `PROTO`, `PROTO_V5`, `PROTO_DATA_V5`, `PROTO_DATA`, `FuncDoc`. Read them via `list_bookmarks`. Example content:

> `0x0007 compact row import layout: ids @ +0x00, types @ +0x14, values @ +0x28 across 10 entries; expiry = packed_now + 200`
> `0x0000 lobby cache blob: record count at +0x56, key halfwords at +0x57, 32-bit sparse values at +0xBB`

Reusable Java GhidraScripts at `<home>\ghidra_scripts\`: `AzrokStats`, `AzrokPatchSites`, `AzrokDumpFunc`, `AzrokAntiDebugScan`, `AzrokXrefScan`, `AzrokDumpSymbols`, `AzrokApplySymbols`, `AzrokDataTypes`, `AzrokNoteTransfer`. **`.py` scripts do not work** — Ghidra 12 requires PyGhidra for those.

### 3.3 Server operations dashboard — observe and drive without restarting

Built 2026-07-17. Design: `docs/superpowers/specs/2026-07-17-server-control-panel-design.md`.

The launcher now serves a control API in-process. **Web page, CLI, and agents share one API** — no separate agent path to maintain.

```
python azrok_launcher.py                    # panel at http://127.0.0.1:9300
python azrok_launcher.py --control-port 0   # disabled
```

The scheduled launcher does not pass `--open-control`, so it never creates a
new browser tab. Keep the existing `http://127.0.0.1:9300` page open. The page
shows client-memory watches and `proto_state`, plus room-grouped multiplayer,
per-client RX/TX/relay counters, semantic events, content/growth persistence,
and a direction-aware packet stream. The CLI mirrors the same API (exit 0/1 so
scripts can branch):

```
python azrok_ctl.py state --watches         # gm, flag_31c71/72/73, latch, nexus
python azrok_ctl.py packets --opcode 0x000C # filter the ring
python azrok_ctl.py send 0x0004 01a5804c25  # inject S->C
python azrok_ctl.py macro hansol            # run the P2 recipe, no code edit
python azrok_ctl.py pause | step | drop     # protocol breakpoint
python azrok_ctl.py set calib_0004_count 0  # force a branch
```

What it buys, concretely:
- **`pause` is a protocol breakpoint.** Outbound `auto` traffic is held at a single chokepoint (`AzrokServer._emit`) and the handler thread blocks until you `step` or `drop`. Pair it with an x32dbg breakpoint to control both sides' timing. Manual/macro sends bypass the gate deliberately.
- **Macros** run decoded recipes as data. `hansol` is the 7-step P2 recipe; `calib_faithful` A/Bs the `0x0004` `0x00`-vs-`0x01` doc contradiction (§1.3) without editing code.
- **Watches** give packet↔state causality live (`S→C 0x0004 [FF]` … did `flag_31c71` flip?) — the thing x32dbg can only show with the game frozen. Read-only, tiny, on purpose. Memory browsing is x32dbg's job.
- **Multiplayer and content telemetry** groups clients by decoded room, shows
  scene/phase/dispatch/self/position and RX/TX/relay/peer counters, and records
  join/leave/room/roster/content-save events. Growth state includes the
  persisted 196-byte `C→S 0x0007` snapshot and Gym stat `0x20`.
- **Packet translation is directional.** Meaning/category/risk/decoded fields
  come from `azrok_server.py`; the GUI filters by direction, client, opcode,
  and text, and marks unknown packets. Auto-follow only scrolls while the log
  viewport is already near the bottom.
- **Dangerous manual sends stay conspicuous.** In particular, `S→C 0x0065`
  requires confirmation because its verified handler resets self/full actor
  state and the remote list. The GUI warning does not claim an unproven
  original resync placement.

**It also fixes the capture-overwrite bug.** Runs now write `captures/packets_<timestamp>.txt` and keep `packets_log.txt` as "latest" for existing tooling. History survives — no repeat of the lost 2026-04-01 `0x000C` evidence.

### 3.4 x32dbg

Registered and connected but **never once used** in this project. This phase changes that.

```
MCP server: x64dbg-automate-mcp   (X64DBG_PATH=D:\x64dbg\x32\x32dbg.exe)
Binary:     32-bit → use x32dbg, not x64dbg
Anti-debug: none (see §0.1). Attach freely.
```

Module bases at runtime: `Azrok.exe` @ `0x00400000`, `ACKNEX.DLL` @ `0x10000000`.

Workflow: `list_sessions` / `start_session` → `connect_to_session` → `set_breakpoint` → `go` → `get_all_registers` / `read_memory`.

**Suggested pairing:** Ghidra MCP to find the address and read the surrounding logic → x32dbg to break there and watch real values → feed findings back as Ghidra names/comments/Note bookmarks so they survive the session.

---

## 4. Key addresses

### 4.1 Launcher / connection chain
| VA | what |
|---|---|
| `0x006E8430` | `DAT_006e8430` — the engine pointer (`ENGINE_VARS*`) |
| `0x004ECAB0` | real `WinMain` — calls `engine_open(lpCmdLine, 0)` |
| `0x00657358` | `___tmainCRTStartup`'s WinMain call site |
| `0x004EDB10` | reads the three WDL STRINGs |
| `0x00508B30` | parses them into `gm` |
| `engine+0x998` | username STRING (`+0x0c` = char buffer) |
| `engine+0x9A0` | `"IP:PORT"` STRING |
| `engine+0x9AC` | authkey STRING |
| `engine+0x1E8` | graphics-capability var; `FUN_004ED540` errors out if `(*it >> 10) < 3` → *"지원하지 않는 그래픽카드 입니다"*. Not a command-line gate. dgVoodoo2 satisfies it. |
| `0x0061E340` | `CConnection::Connect` |
| `0x00591CD0` | `CClientPeer::OnConnect` — sets dispatch flag `this+0x4076 = 1` |

### 4.2 Protocol dispatch
| VA | what |
|---|---|
| `0x00594310` | `DispatchInbound_ByClientMode` — top dispatcher |
| `0x0059DD20` | `DispatchState0Specific_S2C` |
| `0x0050CBC0` | `DispatchState0Common_S2C` |
| `0x00613740` | `DispatchState1_S2C` |
| `0x00591DC7` | dispatch flag check (`74 16`). **NOT patched in the launcher flow.** |

### 4.3 `C→S 0x000C` — equipment/selection subsystem (unnamed, prime x32dbg target)
| VA | role | current name |
|---|---|---|
| `0x0059B0B0` | sender — `(**(code **)(*this + 8))(0x0c, local_70, 0x0b)`, 11 bytes | `FUN_0059b0b0` |
| `0x0059C790` | **payload builder** — walks a 9-byte stride table, writes `entry_value - base_value` | `FUN_0059c790` |
| `0x0059CCE0` | dirty-check gate — nonzero only when state changed | `FUN_0059cce0` |
| `0x005BA900` | caller: close equipment screen | `FUN_005ba900` |
| `0x005BC970` | caller: equip confirm, menu codes `0x104`–`0x107` | `FUN_005bc970` |
| `0x006165B0` | inbound consumer (different struct!) | `HandleS2C_000C_ApplyActorSlotValue` |

Inbound `S→C 0x000C` layout: `u32 actor_id, u8 clear_flag, u8 slot_index, u8 slot_value` (7B). Outbound is an 11-byte bulk snapshot. **Not symmetric — never raw-echo.**

### 4.4 Hansol/Plaza
| VA | what |
|---|---|
| `0x00568770` | `Plaza_TransitionFromRoom` |
| `0x00614370` | `Hansol_SceneStageHandler` — stage 0 emits `C→S 0x0064` |
| `0x006130B0` | `SendC2S_0064_LocalBootstrapStatus` (wire form: exactly 1 byte) |
| `0x00528B30` | per-stage gate liveness check on `gm+0x31946` |
| `gm+0x31C71` | readiness latch — set by calibration completion |
| `gm+0x31C72` | Hansol flag — set by the **client**, via the `0x000D` handler |

---

## 5. Prioritized next steps

### P0 — Make the command line actually work (§2.3)
**The probe already exists** — `azrok_launcher.py --native-cli [--argv0 fullpath|Azrok.exe]`. It does not yet succeed: Acknex reads the auth token as a script name (`LOCALAUTH.WDL`). So the remaining work is not plumbing, it is **finding the argument form Acknex accepts** — read `autoLauncher.dll`'s real `ShellExecuteA` parameters, and `engine_open`'s cmdline parser in `acknex.dll`. Both are already in the Ghidra project.

Payoff: `inject_wdl_string` and the engine-pointer polling both disappear; the launcher becomes a true emulator. Verify with the control panel — does the game connect to `127.0.0.1:9200` and reach PatHouse on its own?

### P1 — COMPLETE: native Nexus=40 baseline

Repeated default launches reach PatHouse and the controlled OX route with
literal zero runtime writes. `--nexus-patches` is retained only for diagnostic
regression comparison.

### P2 — COMPLETE: packet-only Hansol/Plaza transition proof

The legacy `C→S 0x0019` process-memory shortcut is now sealed by default
(§1.1a), and the packet harness has been run repeatedly. `S→C 0x000D` enqueues
room code `0x6E`; the downstream room dispatcher/loader chain determines the
space. The later `S→C 0x0064 entry_kind` only applies the self actor to the
space already loaded, so it is not a destination selector.

Current harness: `S→C 0x000D [00]` only. The client naturally emits five
`C→S 0x0016 [01]` requests; the server answers them with five
`S→C 0x0004 [01+timestamp]` samples, then the client emits natural
`C→S 0x0064 [01]`. The authoritative `S→C 0x0064` and `S→C 0x006E` response
is sent by the normal handler. Do not pre-send 0x0004, send server-side 0xFF,
or replay a fresh zone bundle in this door transition.

The four expected vtable values are only a necessary header precondition for
entering `0x000D`; green 4/4 does **not** prove the call will survive. Child
panel/object integrity below those headers remains under active inspection.

**2026-07-17 correction:** read-only static re-analysis resolved the old
contradiction: the server must send `S→C 0x0004 [0x01]` five times; the client
mutates the fifth buffer to `0xFF` before common dispatch latches readiness.
`scene_opcode=110` only proves a stored post-load scene request, not actual
Hansol stage entry. See `docs/research/25_calibration_and_hansol_dispatch_2026-07-17.md`.

**2026-07-17 dynamic proof:** x32dbg observed the complete core and the
request-driven five-sample chain through natural `C→S 0x0064`; final state was
`scene=111`, `phase=5`, `self_actor_id=1`, with no exception. See
`artifacts/dynamic-analysis/X32DBG_000D_CALIBRATION_0064_SUCCESS_20260717_075744.md`.

This closes the transition/calibration contract but not the end-space target:
the rendered result is still the OX quiz space, not Plaza. The next trace adds
breakpoints at `0x0050A7F0`, `0x0050A880`, `0x0050A0F0`, `0x0050B400`,
`0x00614370`, `0x006143EC`, and `0x005AB738` to locate where the OX branch
diverges from the Plaza/Hansol room-loader path.

**A/B resolved (2026-07-17 08:06):** the static path showed that the extra
`S→C 0x006E[00,00]` reply commits the Hansol ready flag and deterministically
queues `0x6F`/`OXQuiz.wmb`. A fresh process with `AZROK_PLAZA_REPLY_MODE=0064`
sent only authoritative `S→C 0x0064`; it remained at `scene=110`, `phase=4`,
and the live window visibly showed the outdoor Plaza. The supported launcher
default is now `0064`; `both` is retained only as an explicit OX diagnostic.
Evidence: `captures/packets_20260717_080648.txt` and
`docs/research/30_006e_ready_commit_forces_ox_2026-07-17.md`.

Final clean default launch (no one-shot override) loaded
`plaza_reply_mode="0064"` and reproduced `scene=110`, `phase=4`,
`self_actor_id=1`, `hansol_calibration_samples_sent=5`, with no `S→C 0x006E`.
Capture: `captures/packets_20260717_081659.txt`.

### P3 — Decode `C→S 0x006C` (§0.2)
Genuinely undocumented. Find the sender first — do **not** reason from `HandleS2C_006C`. Suggested: breakpoint on the generic send helper and catch opcode `0x6C`, or search for `0x6C` immediates feeding a send thunk. Only fired once, payload all zeros, so low urgency — but it is a real unknown in an otherwise mapped protocol.

### P4 — `C→S 0x000C` byte map
Needs live capture (old evidence is gone, §1.3). Open the equipment screen in-game, break on the payload builder `0x0059C790`, and correlate each emitted byte with the item actually equipped.

Doc 23 claims a "Complete Byte Map (VERIFIED)" at `23:252-266`:
| Slot | Base | Range |
|---|---|---|
| Head | 10000 | 10000–10009 |
| Face | 20000 | 20000–20006 |
| Back | 30000 | 30000–30003 |
| Pet | 40000 | 40000–40007 |

with `byte = (absolute_item_id - base_item_id) & 0xFF`.

**Treat as unproven.** The same file says at `23:308` that the map "is not fully named. This is the highest-priority remaining blocker", and `23:318` rates semantics only Medium. It maps 4 slots but the wire is 11 bytes — the 11 positions are never assigned. The Back/Pet ranges also conflict with the decompilation in `12_state1_flow_analysis.md:405-413` (`FUN_00521E90`: `case 2: value += 30000; if (value < 30000 || value > 29987) return;`, `case 3: … value > 39975`), which doc 12 itself flags as needing verification.

Captured payload examples (from the lost run, kept here for reference):
```
0c0f12181ee14e00140000
0c0f12191ee14e00140000
030c0f141a1e4e00140000
```

### P5 — Gameplay testing
`00_current_status.md:189` calls this its #1 open item: *"Can the player interact with objects? Does the game respond to clicks?"* Nobody has confirmed the PatHouse room is actually interactive vs merely rendered. Worth 10 minutes before deep protocol work — it changes what "restore full functionality" even means.

---

## 6. Document trust map

| doc | date | trust |
|---|---|---|
| **this file** | 2026-07-17 | current |
| `docs/research/00_current_status.md` | 04-01 17:00 | mostly current; but §46 says dispatch bypass removed (true for launcher path), and its flow (`C→S 0x0001`, `0x0008`) does not match the pristine run |
| `docs/research/23_recovered_opcode_details.md` | 04-01 17:00 | best opcode reference; self-contradicts on `0x000C` completeness (see P4) |
| `docs/protocol_consolidated_2026-04-01/` | 04-01 | good packet contracts; **wrong on `0x000C`-blocks-Hansol sequencing** (§0.3); dead packets_log line refs |
| `docs/research/21_ghidra_analyzed_reference.md` | 03-31 | addresses valid (imagebase matches); its "Source: Azrok_analyzed.exe" line is now stale |
| `docs/research/12_state1_flow_analysis.md` | 03-31 | useful; its own header retracts its `S→C opcode 100` claim |
| `docs/research/04_runtime_patches_and_telemetry.md` | 03-31 | **HISTORICAL — do not follow** (§0.4) |
| `docs/research/05_crash_timeline_and_failure_modes.md` | 03-31 | **HISTORICAL** — crashes from the abandoned stack |
| `HANDOFF_2026-03-31_*.md` | 03-31 | superseded by this file |

Known cross-doc conflicts, unresolved: port 9000 (`04:5`) vs 9200 (`22:154+`); function-name count 72 (`README:16`) vs 101 (`21:4`); `S→C 0x0004` payload `0x00` (`00:88`) vs `0x01` (`23:30`) — same timestamp, opposite claims; `C→S 0x0064` echo (`23:295`) vs never-echo (`23:231`, `15:99`).

---

## 7. Ground rules

1. **Protocol-first.** A crash is a symptom of wrong server data. Fix the data, not the client. Every patch in this project's history turned out to be masking a data bug.
2. **Two separate blockers, never mix them:** Blocker A (UI automation) and Blocker B (server protocol) are independent problems.
3. **Loading screen ≠ game screen.** `Data\Common\Loading*.wis` images have baked-in overlays. Changed text or a moving bar is **not** evidence of room entry. Success = real 3D room visible + loading panel gone + input attached.
4. **Verify before claiming.** This session alone overturned four "established" facts by actually reading the binary. Assume any inherited label may be wrong.
5. Record findings as Ghidra names / comments / `Note` bookmarks in `/New Traces/Azrok_original.exe`. They migrate cleanly and they are what future sessions will actually read.

## 8. Backups

- `_ghidra_backup_20260717\azrok..rep` — full project snapshot, 204 MB, taken before the migration
- `_ghidra_backup_20260717\post_analysis_0000000a.db` — `Azrok_original.exe` right after headless analysis, before symbol transfer
- `Azrok.exe.patched_backup` — the old working patched build (SHA256 `B7637944…`)
- `Azrok_patched.exe` — a third, distinct patched variant (SHA256 `83142D86…`), provenance unknown

---

## 9. 2026-07-17 local-room recovery continuation

The static and dynamic tracks were continued after the Plaza/OX correction.
`docs/research/32_popup_ring_gym_buttons_41_42_43_2026-07-17.md` records that
Gym popup IDs `0x41/0x42/0x43` are data-driven entries under content key
`0x73`; they are not native `switch(button_id)` cases.  The next local
continuation is `FUN_006122C0(2)` and the later C→S `0x0065` is only the room
report, not a dumbbell ACK.

`docs/research/33_local_room_content_recovery_matrix_2026-07-17.md` records the
loader matrix for playroom, library, gym, magic, kitchen, and shop.  The live
x32dbg run on the current Gym PID produced no popup/transition breakpoint
events: this is a real input/content boundary.  In particular, the global
`B` keyboard branch in `FUN_00535660` is guarded by room-code `100/0x6E`; in
the active Gym scene (`0x66`) it intentionally does nothing.  No synthetic
packet or binary patch is justified by that negative result.

The server implementation now keeps per-connection room metadata and exposes
it to the existing control dashboard without opening the browser
automatically. When a peer exists, C→S room reports and movement are translated
into direction-verified peer S→C `0x0066` actor upserts and `0x0068` positions;
targeted `0x0067` removes a departing actor. The older room-change
`S→C 0x0065` flush implementation is superseded and must not be restored:
static and dynamic proof shows that it resets self/full actor state as well as
the remote list after self creation. Its possible original pre-self placement
is not confirmed.

`docs/research/36_manual_playback_packet_correlation_2026-07-17.md` adds the
human-played Gym capture correction.  The single C→S `0x0065` in capture
`081659` is packet `#157`, the Gym entry membership report; the subsequent
manual movement is C→S `0x0066/0x0067`, and C→S `0x006C` is the E/community
toggle.  There is no second `0x0065` at the dumbbell boundary, so an ACK must
not be invented from the old timing label.  The next protocol work is a clean
single-action capture of a real content sender, plus a two-client relay run.
## 9b. Dispatch gate static result and observer tooling boundary (2026-07-17)

Ghidra revalidation places the two independent fields on the embedded
dispatcher `this` at `logic+0x163D8` (common dispatch owner gate) and
`logic+0x163E4` (dispatch mode). `find_real_gm()` returns the outer
`CGameManager` base; derive `logic = gm+0xE4A+0x17756 = gm+0x185A0` before
reading them. `0x0064` sets mode 1 via `FUN_00594100`, but does not create the
`+0x163D8` gate. The state-1 roster handlers are reached only when both fields
are valid. The single authoritative gate writer is `FUN_00594130` at
`0x00594142`, called during normal startup by `FUN_00508B30`, with gate value
`gm`. The IP buffer at `gm+0x31822` is a separate connection argument. See
the corrected owner derivation in
`docs/research/46_dispatch_vtable_owner_constructor_20260717.md`.

The read-only `gate` x32dbg profile is implemented and excludes all input,
packet, and memory-write paths. Its live attach attempts were not run because
the elevated x32dbg xAuto IPC session did not register (`list_sessions=[]`, no
`xauto_session.<pid>.lock`); an attach attempt then coincided with the target
exiting. This is a tooling failure, not game evidence, and is recorded in
`artifacts/dynamic-analysis/X32DBG_GATE_ATTACH_ATTEMPT_20260717_1117.md` and
`docs/research/42_dispatch_gate_readonly_observer_20260717.md`.
The observer runner now checks for the xAuto session lock before calling
`attach_session`, so a missing plugin session fails closed without touching the
game target.

## 9a. Two-client PatHouse roster wire/state split (2026-07-17)

**Historical unsafe experiment — do not reproduce.** This section records what
the older server emitted, not the current contract. Later x32dbg/Ghidra proof
showed that `S→C 0x0065` resets self/full actor state plus the remote list; the
current implementation does not use this sequence after self creation.

After a clean restart, two real clients completed the C2S `0x0005`/`0x0007`
bootstrap on the same server. The older server assigned an internal-only
`PatHouse (local)` grouping after the full `0x0007`, then emits the verified
S2C roster sequence (`0x0065` flush, `0x0066` real entity record, `0x0068`
position) to both recipients. Capture:
`captures/packets_20260717_103943.txt`; counts were `0x0065=3`,
`0x0066=2`, `0x0068=2`. No packet was synthesized on behalf of a client and
no client memory was written.

The primary did not render a second avatar. The low-temperature roster
observer recorded zero hits at the state-1 handlers/lifecycle boundaries, and
the contemporaneous watch was phase `2`, logic state `0`, self actor ID `0`,
scene `100` (PatHouse). This proves server wire emission separately from the
client's state-1 dispatch prerequisite; changing the 0x0066 field map is not
the next step. Full evidence is in
`docs/research/40_two_client_roster_wire_vs_client_state_20260717.md` and
`artifacts/dynamic-analysis/PID134448_TWO_CLIENT_ROSTER_TRACE_20260717.md`.

## 9. Same-server two-client bootstrap and OX boundary (2026-07-17)

`azrok_launcher.py --reuse-server --port 9207` now starts a second client
without a second listener. In a clean run, client A reached PatHouse and
client B emitted the observed C→S `0x0005` zero selector from the character
screen. The server now handles this direction-specific packet by replaying
the known-good `S→C 0x0003 + 0x0007 + 0x0005 + 0x000A + 0x000B` bootstrap. The
second client then reached PatHouse; the control panel showed two connected
players with `PatHouse (local)` while keeping `room_kind=null` until a real
server room report arrives. See `docs/research/38_two_client_reuse_server_and_0005_bootstrap_2026-07-17.md`.

The approved elevated UI path reproduced local dialogue, floor movement and
door approach without a UAC prompt. These auxiliary-room steps produced no
C→S `0x0065/0x0066/0x0067`, consistent with the client-local room loader.
The same run's `S→C 0x0003 Plaza` and repeated `0x0007` manual injection
caused a black/re-entry render and was stopped; this confirms the existing
warning against reinjecting the setup bundle mid-room.

With the existing low-temperature x32dbg room observer armed before the
secondary action, one readiness-gated `S→C 0x000D` macro was tested. It
produced the natural five `C→S 0x0016[01]` calibration requests, five
`S→C 0x0004[01]` samples, C→S `0x0064`, and S→C `0x0064` entry kind `0x0A`.
The visible result was the OX quiz scene, not Plaza. Treat this as a
validated alternate-space baseline; do not relabel it as Plaza. Details:
`docs/research/39_hansol_macro_ox_natural_entry_2026-07-17.md`.

## 10. Two-client 0064-only Plaza roster boundary (2026-07-17)

**Historical wire experiment, superseded by the 14:30 proof above.** The
captures below are valuable evidence that the old server sent the records, but
their `S→C 0x0065` step is unsafe and is no longer part of the supported
roster path. Visible spawn/movement was subsequently proven with peer-only
`0x0066`/`0x0068`, and departure with targeted `0x0067`.

The clean targeted run in `captures/packets_20260717_122202.txt` used one
server listener and two real clients.  The control path addressed each
connection by its internal entity id and sent only the already observed
`S->C 0x000D[00]` prelude.  Both clients then emitted the natural five
`C->S 0x0016[01]` calibration requests followed by `C->S 0x0064[01]`; the
server replied with authoritative `S->C 0x0064` and deliberately omitted
`S->C 0x006E`.

On each direction-verified `C->S 0x0064`, that older server recorded the Plaza
grouping (wire kind `0x1B`) and rebuilds the recipient roster.  The same
capture contains both directions of `S->C 0x0065` flush, `S->C 0x0066` actor
record, and `S->C 0x0068` position, with entity ids 2 and 3 corresponding to
the two connected clients.  This is direct multiplayer wire evidence; the
clients exited before a screenshot could be saved, so visible state-1 avatar
rendering remains a separate UI check.  Full details are in
`docs/research/45_two_client_plaza_targeted_roster_20260717.md`.

The follow-up simultaneous run in
`captures/packets_20260717_125019.txt` kept both PatHouse peers alive, issued
the two `0x000D[00]` requests back-to-back, and reproduced both natural
`C->S 0x0064` / authoritative `S->C 0x0064` boundaries plus bidirectional
`0x0065/0x0066/0x0068` roster traffic.  This distinguishes the earlier
single-peer 000D exit from a universal transition failure; it still did not
capture a visible-avatar screenshot before the clients closed.

## 11. Dispatch-owner reverse search and r13 transition crash (2026-07-17)

The earlier direct `gm+0x163D8/+0x163E4` watch is now explicitly treated as a
candidate only.  The startup chain resolves to `0x3ED00010`, whose first
DWORD is `0x2E373231` (`"127."` in little-endian bytes), so its `+0xC` result
is an IP-string/network record rather than a proven dispatcher vtable.  This
qualification is recorded in
`docs/research/45_dispatch_pointer_semantics_recheck_20260717.md`.

`azrok_server.py` now performs a read-only `VirtualQueryEx` scan for the
writer value `gm` against the embedded CLogic owner at
`logic = gm+0xE4A+0x17756 = gm+0x185A0`, and an independent scan for both the pre-promotion
`0x006A6154` (`CLogicJSDB`) and promoted `0x006A618C` (`CLogicManager`)
vtable.  `0x006A6198` is the latter vtable's +0x0C slot, not its base.  The
WDL string chain is exposed separately and is never treated as an owner
target.  The first live scans found no target hits and no validated owner,
which means the gate writer has not yet been observed in those runs; no field
was written.

The same r13 run is preserved as a negative transition result in
`captures/packets_20260717_123822.txt`: a manually sent `S->C 0x000D[00]`
followed the normal PatHouse bootstrap and natural calibration, but the
client exited before a Plaza scene was established.  This is a single
reproduction of the unsafe timing/path, not evidence against the already
reproduced clean two-client Plaza boundary in section 10.
