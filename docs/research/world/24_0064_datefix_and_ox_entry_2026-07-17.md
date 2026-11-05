# S->C 0x0064 date crash fix and OX entry finding (2026-07-17)

This note supersedes older shorthand that labeled `0x0064 entry_kind=0x0A`
as Plaza. The 2026-07-17 live run proved that label is wrong for the current
packet recipe.

## Verified crash root cause

ProcDump captured the first exception from the failing startup sequence:

- dump: `artifacts/dynamic-analysis/procdump_20260717_0530/Azrok.dmp`
- report: `artifacts/dynamic-analysis/procdump_20260717_0530/ROOT_CAUSE_0064_DATE.md`
- root exception: C++ EH `0xE06D7363`, `PAVCOleException@@`, HRESULT `0x80004005`
- failing path: `HandleS2C_0064 -> FUN_0050EEC0/FUN_0050F42E` date validation

The server's old `S->C 0x0064` builder had the date block shifted left. The
handler reads a seven-byte clock block at payload `+0x14..+0x1A`; when year/day
were zero the client reached the invalid-date abort path. `S->C 0x006E 0000`
was not the crash cause.

## Current S->C 0x0064 layout

`STATE_0064_SIZE = 0x1B`.

| Offset | Type | Meaning |
|---|---:|---|
| `+0x00` | u8 | `entry_kind`, accepted values seen statically: `0x00`, `0x0A`, `0x0B`, `0x14` |
| `+0x01` | u32 | authoritative self actor id |
| `+0x05` | u8 | reserved/unknown |
| `+0x06` | u32 | raw X |
| `+0x0A` | u32 | raw Y |
| `+0x0E..+0x11` | bytes | reserved/unknown |
| `+0x12` | u8 | selector / appearance A |
| `+0x13` | u8 | selector / appearance B |
| `+0x14` | u16 | year |
| `+0x16` | u8 | zero-based month |
| `+0x17` | u8 | day |
| `+0x18` | u8 | hour |
| `+0x19` | u8 | minute |
| `+0x1A` | u8 | second |

The successful payload in the clean run was:

```text
0a01000000007b0f0000c3000000000000000202ea070611052525
```

Decoded: `entry_kind=0x0A`, actor id `1`, X `0x0F7B`, Y `0x00C3`,
selectors `0x02/0x02`, and a valid 2026-07-17 clock block.

## Live result: OX, not Plaza

Run state:

- capture: `captures/packets_20260717_053540.txt`
- no Nexus/runtime guard patches enabled
- WDL variable injection path restored
- game window was held at screen origin `(0, 0)`
- process stayed alive after `C->S 0x0064` and `S->C 0x0064 + 0x006E`

Visual result:

- rendered OX quiz space
- Korean welcome text: `[OX] [ OX game welcome text ]`
- scene watch settled at `scene_opcode=111`
- `flag_31c72=1`, `flag_31c71=0`

Conclusion: the packet sequence is a real no-patch state-1 transition, but it
is the OX quiz space, not the target Plaza/hansol space.

## Server knobs for the next A/B tests

`azrok_server.py` now exposes the 0064 entry byte:

- process default: `AZROK_0064_ENTRY_KIND`, parsed with `int(value, 0)`
- live control state key: `state_0064_entry_kind`
- CLI example before running the macro in a fresh session:

```powershell
python azrok_ctl.py set state_0064_entry_kind 0x0B
python azrok_ctl.py macro hansol
```

Use a fresh process per candidate because the current run is already in the OX
state after the first `S->C 0x0064`.

## Controlled selector matrix conclusion

All four accepted values have now been exercised under the same controlled
conditions: a corrected five-`0x01` calibration prelude followed by a real
`C->S 0x0064 [01]`. Every value remained stable and rendered OX. Therefore
`entry_kind` is not the missing Plaza selector in the current packet recipe.

| Candidate | Controlled result |
|---|---|
| `0x00` | Stable OX; `captures/packets_20260717_062837.txt` |
| `0x0A` | Stable OX control; `captures/packets_20260717_061822.txt` |
| `0x0B` | Stable OX; `captures/packets_20260717_062333.txt` |
| `0x14` | Stable OX; `captures/packets_20260717_063259.txt` |

Do not remove the `C->S 0x0019` memory shortcut until the actual Plaza entry
variant is identified. Otherwise the door handler may accidentally encode the
OX route as the production Plaza route.

## Fresh-session candidate observations (same day)

The `entry_kind` selector is read only after the client has emitted `C->S
0x0064`. Therefore a run which never emits that request is **not** an A/B
result for the selector; it is evidence about the earlier `0x000D` / `0x0004`
transition timing.

| Requested selector | Fresh-run observation | Interpretation |
|---|---|---|
| `0x0B` | The early run (`055512`) crashed, but it used a different client bootstrap mode and the old four-plus-FF calibration. A controlled same-mode re-test in `captures/packets_20260717_062333.txt` used `C->S 0x0064 [01]` and the corrected five-`0x01` prelude. | Not a crash cause by itself: it matched the `0x0A` control and reached stable OX (`scene_opcode=111`, phase 5). |
| `0x00` | An early run stopped at `scene_opcode=110` without emitting `C->S 0x0064`. The controlled re-test in `captures/packets_20260717_062837.txt` did emit `[01]` after the five-`0x01` prelude. | The early observation is superseded as a selector result. Controlled result: stable OX. |
| `0x14` | An early run likewise stopped before `C->S 0x0064`. The controlled re-test in `captures/packets_20260717_063259.txt` reached the real request/reply point. | The early observation is superseded as a selector result. Controlled result: stable OX. |

To keep each run isolated without repeatedly accepting UAC, the workspace now
contains two fixed, on-demand elevated scheduled tasks:

- `Azrok-Plaza-Launch` runs `tools/run_azrok_elevated.ps1`.
- `Azrok-Plaza-Stop` runs `tools/stop_azrok_elevated.ps1` and is limited to
  this workspace's `Azrok.exe` plus its `azrok_launcher.py` process.

The launch task keeps the known OX control selector `0x0A`; set
`state_0064_entry_kind` through the local control API before a confirmed
`C->S 0x0064` reply point. The launcher retains the `(0, 0)` window watchdog.

## Calibration correction

The older Hansol macro used four `S->C 0x0004 [0x01]` samples followed by a
server-sent `0xFF`. Read-only Ghidra re-analysis proved that the client must
receive **five** `0x01` samples; its fifth receive handler mutates the shared
buffer to `0xFF` before common dispatch latches readiness. The server macro
now follows this packet-faithful five-sample sequence and rejects execution
until the PatHouse baseline is stable. See
`25_calibration_and_hansol_dispatch_2026-07-17.md` for the control flow and
the meaning of `scene_opcode=110`.

## Reproducible OX control after the calibration correction

The corrected Hansol prelude was re-run from a clean PatHouse baseline in
`captures/packets_20260717_061355.txt` without any executable or runtime code
patches. The launcher retained its window-origin watchdog at `(0, 0)`.

Admission observation before `S->C 0x000D`:

- PatHouse phase `gm+0x31792=2`, scene request `100`, dispatch gate non-zero
- initial zone handshake completed (`zone_request_count=2`)
- bootstrap `S->C 0x0004[00]` traffic had stopped

At `06:20:17`, the server sent `0x000D [00]` followed by five timestamped
`S->C 0x0004 [01]` packets at approximately 250 ms intervals. The client
emitted `C->S 0x0064 [01]` at `06:20:18.748`; the server then sent:

```text
S->C 0x0064  0a01000000007b0f0000c3000000000000000202ea070611061412
S->C 0x006E  0000
```

The process remained live and settled at `scene_opcode=111`,
`phase_31792=5`, `flag_31c72=1`, `self_actor_id=1`. This is a repeatable OX
control, still **not** the target Plaza scene. It also proves that the prior
`scene_opcode=110` stalls were caused by early/interleaved calibration, not by
the repaired S->C `0x0064` date layout.

The parallel dynamic observation record is
`artifacts/dynamic-analysis/READY_GUARD_FIVE_01_20260717.md`. It confirms no
new crash event and continued heartbeat after the transition. Its earlier
`entry_kind=0x0B` crash comparison is retained only as a historical,
confounded observation: the bootstrap/calibration conditions differed. The
later identical-condition matrix proves that `0x0B` itself is not the crash
cause.
