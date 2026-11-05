# Plaza post-`0x0064` stall and clean-retry success (2026-07-17)

> **VISIBLE-EXIT IDENTITY SUPERSEDED by 73.** Section 6's
> `dm_door_0003_057 = outside exit` conclusion was a visual-correlation error.
> It is the bathroom/internal-door target. The strongest far-left outside
> candidate is `gate_mun_MDL_048` with colocated `doorframe_01`; exact hit
> binding remains pending. The transition/wire-health
> findings in the other sections remain valid.

This note is the current authority for the intermittent loading-screen stall
observed after a natural PatHouse exit. It compares one failed transition and
the immediately following clean restart using packet captures, runtime watches,
Frida observation, a read-only x32dbg snapshot, and visible screenshots.

## 1. Wire sequence was valid in both runs (VERIFIED)

The failed run used `captures/packets_20260717_214547.txt`:

```text
C2S #207 0x0019 [00]
S2C #207 0x000D [00]
C2S/S2C #208..#212 0x0016 plus S2C 0x0004[01] x5
C2S #213 0x0064 [01]
S2C #213 0x0064, 27 bytes
```

The successful retry used `captures/packets_20260717_223625.txt`:

```text
C2S #94 0x0019 [00]
S2C #94 0x000D [00]
C2S/S2C #95..#99 0x0016 plus S2C 0x0004[01] x5
C2S #100 0x0064 [01]
S2C #100 0x0064, 27 bytes
C2S/S2C #101 onward 0x0016 heartbeat resumes
```

The two 27-byte `S2C 0x0064` payloads have the same semantic fields:

```text
0a 01000000 00 7b0f0000 c3000000 00000000 02 02 ea07061116 TT TT
```

Only the trailing time bytes differ. Neither run emitted `S2C 0x006E`, used a
memory shortcut, or patched the executable/runtime.

## 2. Failed run: Win32 pump alive, game loop stopped (VERIFIED)

After failed `S2C #213 0x0064` the client remained on the Plaza loading image:

- screenshot:
  `artifacts/dynamic-analysis/restart2_outside_loading_stall_20260717_2215.bmp`;
- runtime watch: `scene=110 / phase=4 / dispatch_mode=0`;
- `self_actor_id=0x06D40057`, not a committed actor id;
- no subsequent heartbeat packets;
- Windows still classified the window as responding.

The two-second Frida observer continued to see the Windows message pump but saw
zero `worldInputFrame`, button, care, evolution, or protocol-field writes. This
proves that "Responding" alone is not a sufficient game-loop health signal.

The read-only snapshot
`artifacts/dynamic-analysis/x32dbg_hang_snapshot_137076_20260717_222446_385.json`
found the main/high-CPU thread stopped in a Win32 wait and only helper/network
threads carrying Azrok return addresses. It localizes the failure to an engine
loop/load stall but does **not** identify one definitive locking instruction.

## 3. Clean retry completed and stayed alive (VERIFIED)

The stalled PID was closed and the server/client were restarted cleanly. Native
`-NX200`, bootstrap evolution 0, persisted content, and the same natural sleep
growth path were used. The user clicked the real exit door. The client reached:

```text
scene=110
phase=4
dispatch_mode=1
self_actor_id=1
state1_dispatch_ready=true
Nexus=200 MiB
free arena bytes=162,818,672
```

Heartbeats continued for minutes after `S2C #100 0x0064`. Visual evidence is
`artifacts/dynamic-analysis/restart3_plaza_success_20260717_2253.bmp`, showing
RedRon in the outdoor Plaza.

## 4. Conclusion (INFERRED from the verified comparison)

The failed run is an intermittent client-side post-load race/deadlock, not a
malformed server transition packet. The strongest evidence is that an
equivalent semantic `0x0064` contract immediately succeeded after a clean
restart and entered state 1 with a valid self actor and resumed heartbeats.

The exact engine lock/wait owner remains **NOT VERIFIED**. If the stall repeats,
capture a deeper debugger stack at the first 20-second heartbeat gap rather
than changing the packet sequence.

## 5. Runtime monitoring shipped (VERIFIED in source/tests)

`azrok_server.py` now exposes a read-only `transition` summary built from:

- `scene` and `phase`;
- dispatch mode;
- committed self actor id;
- whether full `S2C 0x0064` was emitted;
- network heartbeat idle time;
- engine error dialog state.

The dashboard labels a healthy Plaza only when state 1, a valid self actor, and
a heartbeat within 20 seconds agree. `scene=110 / phase=4` with a committed
`0x0064` and stopped heartbeat is shown as a suspected post-`0x0064` stall.
Python compilation, dashboard JavaScript syntax validation, and the nine
content-builder unit tests pass.

**Restart-4 follow-up (VERIFIED, note 64):** the next normal restart activated
this monitor. Its observed progression was
`pathouse_stable -> pathouse_exit_ready -> plaza_healthy`, ending at
`scene=110 / phase=4 / dispatch_mode=1 / self_actor_id=1` with resumed
heartbeats. The pending-activation statement is therefore closed.

## 6. Visible exit-door identity correction

> **SUPERSEDED by 73.** Preserved below as the exact false conclusion and its
> former evidence chain.

The earlier `mirror_01` visible-door description is corrected:

- **VERIFIED:** the PatHouse WMB record named `mirror_01` is the wardrobe/mirror
  object that was visibly clicked during the failed coordinate probe;
- **VERIFIED:** the visible outside door mesh is `dm_door_0003_057` using
  `dm_door_0003.MDL`; the user's manual click at that door produced the natural
  `C2S 0x0019[00]` in the successful retry;
- **NOT VERIFIED:** whether the earlier `mirror_01` descriptor/action trace is
  separate invisible interaction metadata or was a static name-binding error.

The control API therefore names `dm_door_0003_057` as the visible exit and
retains the unresolved action-provenance distinction instead of presenting the
wardrobe as the door.
