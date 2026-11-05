# Acknex native `-NX`, E1201 allocator boundary, and natural Plaza exit

Date: 2026-07-17

This note is the current authority for the Acknex Nexus configuration used by
the restoration launcher, the meaning of `Error E1201`, and the first fully
natural PatHouse-growth-to-Plaza run. The executable and `ACKNEX.DLL` were not
modified. Frida was used only as an input/observation harness for the natural
sleep action; it did not write the evolution field or alter game logic.

## 1. E1201 detail and allocator contract (VERIFIED)

`Nexus too small! (3)` does **not** mean that the configured Nexus is 3 MiB.
The parenthesized number is the failed allocation request rounded up to KiB.

| Path | Entry | Failure branch | Request | Caller | Remaining |
|---|---:|---:|---|---|---|
| bottom-up | `ACKNEX.DLL+0x3F230` | `+0x3F25C` | `[ESP+8]` | `[ESP+4]` | `ESI` |
| top-down | `ACKNEX.DLL+0x3F390` | `+0x3F3D2` | `[ESP+8]` | `[ESP+4]` | `ECX` |

The common reporter is `ACKNEX.DLL+0x34700`; error id `0x4B1` is E1201.
The live arena counters are:

- bottom used: `0x102FE9B0`;
- total bytes: `0x102FE9BC`;
- top used: `0x102FE9C0`;
- base pointer: `0x102FE9C8`;
- free bytes: `total - bottom - top`.

The earlier explanation that `(3)` was a Nexus selector, or that the failure
was caused only by setting bootstrap evolution before stat import, is
superseded. A clean post-load natural evolution at Nexus 40 reproduced E1201.

## 2. Native engine configuration (VERIFIED)

Acknex 6.40 parses its own Nexus option in `ACKNEX.DLL+0x17EE0`:

- `-NX200` is accepted;
- `-NX 200` is accepted;
- `-NX=200` is not accepted;
- the built-in default is 40 MiB (`ACKNEX.DLL+0x17EF0`).

`Azrok_original.exe` forwards `WinMain.lpCmdLine` to `engine_open` without
rewriting it. The supported restoration launcher therefore starts the engine
with `"Azrok.exe" -NX200` while continuing to inject IP/user/auth through the
verified WDL variables. Bare IP/user/auth command-line tokens remain invalid
because the engine treats the last token as a WDL filename.

The old addresses `0x10018414` and `0x1001843D` are the two native parser
assignment sites. They are not WDL override sites and must never be NOPed.

## 3. Nexus 40 failure and Nexus 200 success (VERIFIED)

The A/B used the same shipped content profile, bootstrap evolution zero,
kind-3 runtime row, EXP/stat state, and natural sleep action.

### Nexus 40

- PatHouse was stable before the action;
- only about `5,289,552` arena bytes remained;
- the client visibly changed BlueRon to RedRon and saved evolution 1;
- Acknex then opened `Error E1201: Nexus too small! (3)`;
- screenshot: `artifacts/dynamic-analysis/E1201_NEXUS3_NATURAL_EVOLUTION_20260717.png`.

### Native `-NX200`

- arena total: `209,715,200` bytes;
- pre-evolution free: `165,866,768` bytes;
- the real sleep button executed `careAction -> evolutionCheck(kind 3) -> evolutionCommit`;
- `ProtocolState+0x130` changed naturally from 0 to 1;
- post-evolution free: `150,048,928` bytes;
- `nexusBottomFail=0`, `nexusTopFail=0`, `e1201Report=0`;
- the client remained responsive and persisted the 196-byte snapshot with
  evolution byte 1, stat 55/56 authority 1/2, and matching progress sum.

Primary trace:
`artifacts/dynamic-analysis/FRIDA_ELEVATED_20260717_212202_758.txt`.

This proves that the current shipped restoration profile needs a larger arena
than the native 40 MiB baseline for this natural content path. It does not prove
that the original 2008 service used exactly 200 MiB.

## 4. Natural PatHouse exit to Plaza (VERIFIED)

After the natural RedRon evolution, the user manually clicked the visible
outside door. The client, without memory writes or transition injection,
produced the following sequence at 21:26:10:

```text
C2S 0x0019 [00]
S2C 0x000D [00]
S2C 0x0004 [01 + timestamp] x5
C2S 0x0064 [01]
S2C 0x0064 [27 bytes]
```

No `S2C 0x006E` was sent. The rendered result was the outdoor Plaza, not OX:

- `scene=110`, `phase=4`, `dispatch_mode=1`, `self_actor_id=1`;
- heartbeats continued and the user generated Plaza `C2S 0x0066/0x0067`
  movement traffic;
- the engine error window remained absent;
- capture: `captures/packets_20260717_211306.txt`;
- visual proof:
  `artifacts/dynamic-analysis/plaza_natural_exit_20260717_2126.bmp`.

This is the first end-to-end proof of:

```text
bootstrap evolution 0
  -> natural care evolution (+0x130 = 1)
  -> user outside-door click
  -> natural C2S 0x0019
  -> packet-only 0064-only Plaza admission
```

> **CORRECTED by note 73 (supersedes 63):** `mirror_01` is the visibly tested
> wardrobe/mirror record. `dm_door_0003_057` is the bathroom/internal door.
> The strongest far-left outside candidate is `gate_mun_MDL_048` plus `doorframe_01`.
> The older descriptor/action provenance remains separate and not fully resolved.

## 5. Clean-restart natural evolution reproduction (VERIFIED)

A new server/client run launched the unmodified executable with native
`-NX200`, entered PatHouse with bootstrap evolution 0, and repeated the same
natural BlueRon-to-RedRon growth path. The original cursor estimate missed the
radial button, so the input harness was narrowed to the verified internal
button contract instead of retrying guessed coordinates:

- `ButtonQueue_Pop` thunk: `0x004E031C`;
- PatHouse radial dispatcher: `FUN_005E3EE0`;
- its button-reader return address: `0x005E3F14`;
- natural Sleep button: `0x21` (33), observed parameters `1, -1`.

Ghidra shows `FUN_005E3EE0` explicitly handles `case 0x1F/0x20/0x21` and
consults the natural evolution gate. Frida replaced the read buffer only for
the exact `(caller=0x005E3F14, button=0x21)` pair, once. It did not write
`+0x130`, stats, scene state, or network state.

The client displayed the real `레드론으로 성장!` result. Packet evidence in
`captures/packets_20260717_214547.txt` then showed:

- `C2S #156 0x0007`: evolution byte `+0x05 = 0`;
- `C2S #162 0x0007`: evolution byte `+0x05 = 1`;
- follow-up natural `C2S 0x0010/0x0011` content state;
- the exact 196-byte snapshot persisted as
  `server_state/506c61796572_c2s0007.bin`.

At the post-growth checkpoint the client remained at `scene=100 / phase=2`,
Nexus was 200 MiB, free arena space was `150,057,856` bytes, heartbeats
continued, and no engine error window was active. Visual proof:
`artifacts/dynamic-analysis/restart2_redron_growth_20260717_221222.bmp`.

Primary injection trace:
`artifacts/dynamic-analysis/FRIDA_ELEVATED_20260717_221051_161.txt`.
The trace proves the exact button-reader injection; the later packet and visual
state prove the resulting client-owned growth because the 10-second trace
ended before the presentation completed.

## 6. Operational decision

The restoration launcher now defaults to native `-NX200` with zero binary or
runtime code patches. `--nexus 40` and one-shot `REQUEST_NEXUS.txt=40` remain
available for the low-arena negative control. Bootstrap evolution remains 0;
the client owns post-load evolution.

## 7. Remaining uncertainty

### INFERRED

- The original service could have supplied a larger Nexus through its remote
  JavaScript/launcher parameters because that path forwards arbitrary engine
  arguments.

### NOT VERIFIED

- the exact Nexus argument used by the 2008 service;
- the minimum sufficient Nexus for every shipped content path;
- the evolution-0 negative outside-door control;
- the exact relationship, if any, between the older `mirror_01` descriptor
  action trace and the now-verified `dm_door_0003_057` visible exit mesh.

The second full clean-restart natural outside-door exit is VERIFIED in note 63.
