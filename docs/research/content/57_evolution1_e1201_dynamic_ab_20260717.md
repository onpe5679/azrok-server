# Evolution-1 `E1201` dynamic A/B at native `Nexus=40`

Date: 2026-07-17

This note corrects the earlier proposal in
`54_pathouse_growth_gate_and_natural_0019_20260717.md` that made evolution 1
the supported default. Static analysis correctly proved that a nonzero
`S2C 0x0007 payload[2]` opens the PatHouse outside interaction, but that fact
does not prove it is safe to inject the mature state during initial room
bootstrap.

## 1. Direct error evidence

The two fresh default-evolution-1 runs were:

- `captures/packets_20260717_154421.txt`
- `captures/packets_20260717_160053.txt`

Both stop after the same 29-packet sequence. The second process was PID
`22976`. Enumerating its visible top-level and child windows without sending
input returned:

```text
class = #32770
title = Error E1201
child Static = Nexus too small (40)
```

The control server's read-only watches at the stopped state were:

```text
scene_opcode  = 100
phase_31792   = 3
self_actor_id = 0
nexus         = 40
dispatch_mode = 0
last C2S      = 0x0008, 41 zero bytes
```

Therefore the failure is not a generic "startup failure" label. It is the
Acknex resource-limit error at the original runtime Nexus value.

## 2. Packet-level control comparison

The useful controls are the unpatched/native-Nexus runs:

- `captures/packets_20260717_150309.txt`: stable PatHouse, later full
  `C2S 0x0007`, 504 captured packets and continuing heartbeats.
- `captures/packets_20260717_081659.txt`: stable PatHouse, Plaza traversal,
  Gym entry, movement and content interaction.

Comparing the full setup bundle in `150309` with the first failing run:

| Packet | Result |
|---|---|
| `S2C 0x0003` | byte-identical PatHouse resource root |
| `S2C 0x0005` | byte-identical six-byte zero payload |
| `S2C 0x000A` | byte-identical; SHA-256 prefix `f4437e504b0f` |
| `S2C 0x000B` | byte-identical; SHA-256 prefix `d8c0e8eca72d` |
| `S2C 0x0007` | generated time differs as expected; the only functional difference is `payload[2]`, `0 -> 1` |

The two failing captures independently reproduce the same boundary: they emit
`C2S 0x0008`, then no full `C2S 0x0007` state snapshot and no later
heartbeat. The live process remains at phase 3 with no self actor while the
modal E1201 dialog is open.

This establishes a direct dynamic correlation between the new initial
nonzero field and `E1201`. It does not by itself prove which internal engine
allocation consumes the last Nexus slots; that is a separate static/debugger
question.

## 3. Post-load full replay is also unsafe

`captures/packets_20260717_160908.txt` tested the cheapest timing alternative:

1. initial full `S2C 0x0007` with `payload[2]=0`;
2. client completed enough of PatHouse initialization to send the natural
   196-byte `C2S 0x0007` snapshot;
3. a manual full `S2C 0x0007` replay used `payload[2]=1`;
4. the client again displayed `Error E1201 / Nexus too small (40)`.

The readout after the second failure was:

```text
PID            = 129324
Responding     = true (modal dialog is pumping messages)
Working set    = 300.2 MiB
Private memory = 357.6 MiB
scene / phase  = 100 / 3
self actor     = 0
nexus          = 40
```

This falsifies the simple workaround "load stage 0 first and replay the full
setup blob as stage 1 afterward." A repeated full `0x0007` is already known
to re-enter room/setup work; changing only its timing does not turn it into a
lightweight evolution update.

## 4. Server-side correction

The packet-first supported baseline should therefore be:

1. keep the initial `S2C 0x0007 payload[2]` at `0`;
2. do not replay a full `S2C 0x0007` merely to open the outside gate;
3. recover the original growth-completion contract that changes the relevant
   client state after in-house progression;
4. only then test the natural `mirror_01 -> action 0x6F -> C2S 0x0019` chain.

This matches the user's historical gameplay correction: a newly entered
PatHouse character was not supposed to leave immediately; the Azron had to
grow first. Making evolution 1 an initial convenience default skipped that
gameplay contract and exposed an engine resource boundary.

Increasing Nexus remains useful as a diagnostic control, but it is not a
protocol restoration and must not become the supported fix. A command-line
or WDL engine-setting investigation may explain the original distribution's
resource policy, yet the game-preservation target still requires the natural
growth transition to be reconstructed.

## 5. Dynamic tooling result

The visible error and runtime state were obtained read-only. A `cdbX86`
attach with immediate detach was attempted to capture the waiting stack, but
Windows rejected debugger initialization with error 87. No breakpoint or
memory write occurred. The transcript is:

- `artifacts/dynamic-analysis/e1201_cdb_attach_20260717.log`

The consolidated raw observation is:

- `artifacts/dynamic-analysis/E1201_EVOLUTION1_AB_20260717.txt`

## 6. Existing dynamic lead for the real growth contract

`captures/packets_20260717_093328.txt` contains a useful but deliberately
non-authoritative old probe. A manual 196-byte `S2C 0x0007` (a C2S snapshot
mistakenly used in the reverse direction) was followed immediately by fourteen
natural client reports with the verified six-byte layout
`C2S 0x0017 <kind=0x07, stat_id, u32 value>`:

```text
00/256, 01/0, 03/45, 04/40, 05/50, 06/30, 07/55,
08/100, 0A/20, 0C/22, 0E/20, 10/25, 17/80, 18/1
```

The undersized inbound packet must not be replayed: the full handler consumes
472 bytes, so the historical probe relied on out-of-bounds receive-buffer
contents. The valuable observation is only the client behavior after a state
change: the client has a live path that serializes individual state/stat deltas
as `C2S 0x0017`. Tracing which legitimate in-house content completion enables
that sender, and which threshold eventually changes the evolution selector,
is a better dynamic pivot than another full `S2C 0x0007` replay.
