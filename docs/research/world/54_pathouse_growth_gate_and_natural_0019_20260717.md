# PatHouse growth gate and natural `0x0019` outside request (2026-07-17)

> **SUPERSEDED by 60 and 62 in sections 1, 5, and 6.** The static sender chain
> remains valid. The live contract is bootstrap evolution 0, natural post-load
> promotion to `+0x130=1`, then natural `0x0019` and packet-only Plaza entry.

> **VISIBLE-ASSET CORRECTION by 73 (supersedes 63):** the WMB `mirror_01`
> record is the wardrobe/mirror. `dm_door_0003_057` is the bathroom/internal
> door. The strongest far-left outside candidate is `gate_mun_MDL_048` plus
> `doorframe_01`. Treat this note's descriptor/action chain as separate
> provenance until its relationship is dynamically resolved.

This note records the direct static chain that makes the PatHouse outside
interaction available, and the packet-only server continuation implemented
from that evidence.  The binary was read through Ghidra MCP.  No executable
bytes or live client memory were changed during the static pass.

The complete natural click-to-Plaza sequence was live-verified in note 62.

## 1. Exact growth/evolution gate

`HandleS2C_0007_LoadSetupBlob @ 0x0059E330` passes `payload[2]` to
`ProtocolState_SetField130Value @ 0x00599150`.  The latter stores it at
`ProtocolState + 0x130`.

`FUN_005465C0` is the corresponding reader:

```text
return *(u32 *)(ProtocolState + 0x130);
```

PatHouse hit testing in `FUN_0055AE90` tests the **runtime field** against zero.
It does not read a keyed stat slot and does not compare against a higher
threshold. The exact outside-action condition is therefore:

```text
ProtocolState+0x130 != 0
```

`S2C 0x0007 payload[2]` is only one load-time writer for this field. It must
remain zero during bootstrap in the supported profile. The verified successful
route lets a natural post-load care action change `+0x130` from 0 to 1. This is
independent of the 70 `u16` stat bag beginning at `S2C 0x0007 +0x0B`.

## 2. Natural PatHouse outside chain

`FUN_00557570` builds the PatHouse entity-name/type table used by
`FUN_0055AE90`.  The only table entry that reaches the outside request is:

| Entity `tex_name` | Type | Growth condition | Local action |
|---|---:|---|---:|
| `mirror_01` | `0x20` | `ProtocolState+0x130 != 0` | `0x6F` |

The full statically confirmed continuation is:

```text
post-load natural care evolution
  -> ProtocolState+0x130 != 0
  -> PatHouse trace matches mirror_01 / type 0x20
  -> FUN_0055AE90 returns action 0x6F
  -> FUN_00532F70
  -> FUN_00560B60(0x6F)
  -> FUN_0055BDB0(0x3F)       // local walk/action sequence
  -> FUN_0055BBB0 or FUN_0055CBC0 on completion
  -> FUN_00568710
  -> FUN_00594820
  -> C2S 0x0019, payload 00
```

The `mirror_01` name is direct binary evidence, although the rendered object
may look like the outside door/portal to a player.  Until a live trace binds
the visible mesh to this name, documentation should keep the runtime-facing
"outside interaction" label and the exact `mirror_01` asset name together.

## 3. Door-like PatHouse objects that are not the outside request

The PatHouse table and runtime setup contain other door-like names.  They do
not reach `C2S 0x0019`:

| Object/model | Type | `FUN_0055AE90` result | Continuation |
|---|---:|---:|---|
| `doorframe_01` | `0x1F` | default `0x26` | generic click-to-walk/hit handling in `FUN_0055B5E0` |
| `Data\\Space\\PatHouse\\door.MDL` | `0x1F` | default `0x26` | same generic handling; no room load or socket sender |
| `dm_door_0003_057` | `0x24` | default `0x26` | same generic handling; no room load or socket sender |

Types `0x1F` and `0x24` have no dedicated cases in `FUN_0055AE90`.  Their
door-like names are therefore insufficient evidence for a destination or a
network contract.

## 4. PatHouse outside versus Plaza local-room doors

PatHouse does not call `FUN_00530FE0` from its click dispatcher.  Its native
server boundary is the growth-gated `C2S 0x0019[00]` outside request above.

The familiar local selectors belong to the Hansol/Plaza path instead.
`FUN_006122C0` is the native caller that supplies a local index to
`FUN_00530FE0`, after a Plaza door/zone selection:

| Plaza local index | Client-loaded room |
|---:|---|
| `1` | `playroom.wmb` |
| `2` | `gym.wmb` |
| `3` | `magic.wmb` |
| `4` | `cook.wmb` |
| `5` | `shop.wmb` |
| `6` | `library_1.wmb` |

Consequently, a direct RPC call to `FUN_00530FE0` is not a faithful PatHouse
door test.  It bypasses the outside request, Plaza selection, walk/arrival,
and native local-room continuation.  Direct `FUN_00530FE0` execution must
remain sealed as a diagnostic shortcut.

## 5. Current packet-only server continuation

The restored default starts at bootstrap evolution stage `0` and uses the
native Acknex `-NX200` arena:

```text
azrok_launcher.py --evolution default: 0
azrok_launcher.py --nexus default: 200 (native -NX200)
S2C 0x0007 payload[2]: 0
natural care action -> ProtocolState+0x130: 0 -> 1
```

This avoids the unsafe evolved bootstrap while preserving client-owned growth.
The 40 MiB engine baseline remains available through `--nexus 40` for A/B.

When the server receives the natural request, the default continuation is:

```text
C2S 0x0019[00]
  -> reset/arm per-client request-driven Hansol calibration state
  -> S2C 0x000D[00]
  -> answer the client's natural calibration requests
  -> natural C2S 0x0064
  -> authoritative S2C 0x0064 (supported 0064-only Plaza route)
```

The `0x0019` handler does not write `gm+0x31C71`, `gm+0x31C72`, or any other
client memory in its default path.  The historical memory-write plus broad
`0x0003/0x0007/0x0005/0x000A/0x000B` replay remains available only behind
the explicit `AZROK_LEGACY_0019_MEMORY_SHORTCUT=1` diagnostic opt-in.  Its
default is off and it must stay off for protocol-first experiments.

`S2C 0x006E` is not part of the supported response.  Its ready commit can
drive the later OX path, so the supported Plaza reply mode remains
`0064`-only.

## 6. Live verification matrix

1. **VERIFIED:** unmodified binaries, native `-NX200`, bootstrap evolution 0,
   stable PatHouse `scene=100/phase=2`.
2. **VERIFIED:** natural sleep action changed `+0x130` from 0 to 1 and rendered
   RedRon without E1201.
3. **VERIFIED:** the user manually clicked the visible outside interaction and
   produced exactly one natural `C2S 0x0019[00]`.
4. **VERIFIED:** exactly one `S2C 0x000D[00]`; memory shortcut false and no
   client memory write.
5. **VERIFIED:** five request-driven `S2C 0x0004[01]`, natural `C2S 0x0064`,
   authoritative `S2C 0x0064`, no `S2C 0x006E`.
6. **VERIFIED:** rendered outdoor Plaza, `scene=110/phase=4/mode=1`, continued
   heartbeat and Plaza movement. Evidence: `captures/packets_20260717_211306.txt`.
7. **NOT VERIFIED:** a second complete client/server restart reproduction.
8. **NOT VERIFIED:** evolution-0 negative outside-door control.
9. **NOT VERIFIED:** a subsequent Plaza local-room door after this exact run.

If the natural `S2C 0x000D` attempt crashes, attach x32dbg before repeating
and record the first failing instruction.  Do not re-enable the memory
shortcut or call `FUN_00530FE0` directly to turn that failure into an apparent
success.
