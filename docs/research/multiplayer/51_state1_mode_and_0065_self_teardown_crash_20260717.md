# State-1 mode proof and the S2C 0x0065 self-teardown crash (2026-07-17)

This note supersedes every earlier statement that an empty server-to-client
`0x0065` is a safe active-Plaza roster flush or readiness probe.  The work was
performed with the original `Nexus=40` client, no executable patch, and no
client-memory write.

## 1. Direct owner and lightweight observation

The verified embedded dispatcher owner is:

```text
CGameManager = gm
CGame         = gm + 0xE4A
CLogicManager = CGame + 0x17756 = gm + 0x185A0
gate          = logic + 0x163D8 = gm
mode          = logic + 0x163E4
```

The control panel used to run two whole-process reverse searches from every
`/api/state` poll even though the direct owner was already known.  A sample
scan read about 864 MB and took about two seconds.  `collect_runtime_state`
now uses the direct owner for ordinary telemetry; reverse/vtable scans are
available only through the explicit `deep_dispatch_scan=True` diagnostic.
The live API latency fell to about 176 ms in the clean run.

## 2. Plaza changes dispatch mode 0 to mode 1

Evidence:

- `artifacts/dynamic-analysis/plaza_mode_probe_clean_20260717_140003.jsonl`
- `artifacts/dynamic-analysis/x32_gate_trace_20260717_1405.jsonl`

The clean memory samples show:

```text
14:00:03.673  scene=110 phase=3 mode=0 gate=gm
14:00:03.937  scene=110 phase=3 mode=0, C2S 0x0064 observed
14:00:04.203  scene=110 phase=4 mode=1 actor=1 gate=gm
```

The programmatic x32dbg Automate trace independently proves the instruction
boundary.  On inbound opcode `0x0064`, `DispatchInbound_ByClientMode` enters
with mode 0; by `0x00594447`, `0x00594457`, and `0x0059445D` the gate is the
non-null `gm` pointer and the mode is 1.  Thus the supported 0064-only Plaza
path naturally enables state-1 dispatch.

## 3. The delayed exit was caused by proactive S2C 0x0065

The same trace records this exact order:

```text
inbound S2C 0x0064 -> gate=gm, mode=1
inbound S2C 0x0065(empty) -> gate=gm, mode=1
first-chance AV C0000005 at 0x005F3AF4
```

Ghidra resolves the crash path as:

```text
DispatchState1_S2C @ 0x00613740
  -> HandleS2C_0065 @ 0x00615B20
  -> FUN_0050D5D0
  -> FUN_00526F10(base + 0x35C20)  # fixed self-actor slot teardown
  -> remote-list teardown at base + 0x4A723

next active Plaza minimap frame:
FUN_00511C20 -> FUN_005F3AC0
  -> current self accessor returns NULL
  -> 0x005F3AF4: MOV ECX,[EAX+0x10]
  -> NULL+0x10 access violation
```

Therefore `0x0065` is not merely a remote-roster flush.  It tears down the
self actor and the remote actor container.  Its empty payload is structurally
valid, but its active-Plaza lifecycle position is destructive.  A following
`0x0066/0x0068` cannot repair self: the `0x0066` handler skips the self id and
allocates only non-self actors.

## 4. Supported relay correction and live revalidation

`azrok_server.py` now follows this minimum lifecycle:

- solo Plaza entry: no roster packet;
- real peer join: peer-only S2C `0x0066` actor upsert plus `0x0068` position;
- movement: C2S `0x0066` translated to peer S2C `0x0068`;
- S2C `0x0065`: never emitted automatically;
- departure/removal: verified S2C `0x0067 <departed non-self id>` removes one
  real remote actor on leave/disconnect without clearing self; see note 52.

Clean capture after the correction:

- `captures/packets_20260717_140843.txt`
- one-client result after 12 seconds: `scene=110`, `phase=4`, `mode=1`,
  `actor=1`, `gate=gm`, `Responding=true`;
- no S2C `0x0065` occurred;
- a second real client then entered the same 0064-only Plaza;
- the server emitted exactly two S2C `0x0066` 26-byte actor records and two
  S2C `0x0068` 24-byte position records, one peer upsert in each direction;
- the capture still contained zero S2C `0x0065` packets.

The earlier stable Plaza sessions are now reconciled: Plaza entry itself was
not the crash.  The unsafe proactive `0x0065` relay, added during the later
two-client experiment, was the differentiating packet.

## 5. Live two-client movement and rendering proof

The same clean capture was kept open while the user manually clicked to move
the second client.  This produced repeated, direction-specific pairs:

```text
client 2 C2S 0x0066 <from x,y -> to x,y>
server   S2C 0x0068 <entity_id=3, new x,y> to client 1
```

Each observed C2S movement report had a corresponding peer S2C position
record.  C2S `0x0067` stop/direction reports were logged but intentionally not
echoed.  No S2C `0x0065` occurred.

The wire result was also verified visually with the two real game windows:
both rendered the named actors `Azrok1` and `Guest` at distinct positions in
the same outdoor Plaza.  Both clients remained connected and responsive in
`scene=110`, `phase=4`, `dispatch_mode=1`.  This is the first combined proof
that a real peer is spawned, rendered, and moved through the reconstructed
server relay rather than merely appearing in a packet capture.

## 6. Supersession

Superseded claims include:

- `27_state1_0065_empty_probe_2026-07-17.md`: the OX/mode-2 observation does
  not prove active-Plaza/mode-1 safety;
- `31_plaza_gym_c2s_direction_split_and_progression_2026-07-17.md`: empty
  S2C `0x0065` is not a safe roster-phase marker;
- `45_two_client_plaza_targeted_roster_20260717.md`: the old wire capture is
  historical evidence only; its proactive `0x0065` recipe is unsupported.
