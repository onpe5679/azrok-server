# Stat 55/56 authority merge and reconnect persistence (2026-07-17)

This note closes the persistence hazard found in
`58_shipped_content_profile_dynamic_20260717.md`.  The client reports stat 55
and stat 56 as `1/2` through `C2S 0x0017`, while its 196-byte periodic
`C2S 0x0007` snapshot writes those two slots as `0/0`.  Blindly persisting the
snapshot would therefore erase the shipped pet-evolution/species properties
on the next connection.

No client executable bytes or process memory were changed for this fix.

## 1. Implemented authority rule

`AzrokServer._save_character_state_snapshot` now treats the two observed
`C2S 0x0017` fields as per-field authority:

```text
stat 0x37 (55): latest C2S 0017 value
stat 0x38 (56): latest C2S 0017 value
```

For each of these fields the fallback order is:

1. latest same-session `C2S 0x0017` value;
2. previous persisted value for the same character;
3. installed shipped-profile value;
4. incoming periodic-snapshot value.

After merging, the server recomputes the persisted subtotal at snapshot
offset `+0x96` over stat indices `0x1E..0x41`, then writes the 196-byte file
atomically through a temporary file plus `os.replace`.

The `C2S 0x0017` handler records authority only for the verified
`kind=0x07`, stat IDs `0x37/0x38` shape.  It does not invent authority for the
other stats.

## 2. Isolated regression test

`tools/test_content_builders.py` reproduces the live asymmetry with an
incoming periodic snapshot containing `0/0` and adjacent authoritative
values `1/2`.  It verifies:

- persisted stat 55/56 become `1/2`;
- the `+0x96` subtotal equals the post-merge stat sum;
- the server reports merged IDs `[0x37, 0x38]`.

The complete builder suite passes `9/9`, and `py_compile` passes for the
server, launcher, control API, and control page.

## 3. Wire-level persistence and clean reconnect proof

The persistence path was exercised with the real `Azrok1` character key
(`417a726f6b31`), real `C2S 0x0017` wire records for stat 55/56, and a captured
196-byte `C2S 0x0007` snapshot that contained `0/0` in those slots.  The
resulting file is:

```text
server_state/417a726f6b31_c2s0007.bin
length       = 196 bytes
stat 55      = 1
stat 56      = 2
subtotal     = 5043
computed sum = 5043
```

The launcher/server/client were then stopped and started cleanly.  The new
session capture is:

```text
captures/packets_20260717_195537.txt
```

The actual reconnect `S2C 0x0007` in that capture has:

```text
payload length            = 472 bytes
payload[1] species A      = 2
payload[2] model selector = 0
stat 55                   = 1
stat 56                   = 2
level                     = 26 after client normalization
EXP                       = 33000
```

The important separation is preserved: restoring stat 55/56 does not change
the independent bootstrap/model selector in `payload[2]`.  The reconnected
client reached PatHouse `scene=100`, phase `2`, native `Nexus=40`, remained
responsive, and continued normal `0x0016` heartbeat traffic.

## 4. Verdict

The exact stat-55/56 reconnect data-loss bug is fixed and dynamically proven.
The wider question of whether every other stat should prefer delta or
snapshot authority remains field-specific; this change deliberately does not
generalize beyond the two fields for which the contradiction was captured.

