# 146 — Gate 2b: protocol-controlled Plaza→OX reproduction (2026-07-19)

## Purpose

The prior OX AV was reached after interactive world navigation. This run
removes that variable while preserving the real client-side OX admission step:
the local server drives PatHouse→Plaza and the OX portal reply; the original
client must still choose to emit `C2S 00C8` and process the OX packets.

## Control boundary

**VERIFIED implementation:** `POST /api/ox/enter` was added to the local
control API. It calls the existing OX portal gate only for a connected healthy
Plaza client and sends exactly `S2C 006E[0000]`. It does **not** fabricate or
log a client `C2S 006B`; the event is explicitly marked
`request_origin=protocol-control`. Duplicate protection and the existing
connection/room validation remain in the shared portal handler.

The client launcher is `tools/launch_gate2b_protocol_portal.py`, pinned to the
Wine 11 Vulkan root, `-NX 200`, the named `-PL/-DIR/-IP` startup contract, and
the `gate2b_wine11_vulkan_20260719` preservation namespace. Both changed Python
modules pass `python -m py_compile azrok_server.py azrok_control.py`.

## Live packet result

**VERIFIED live:** with the controller listening on TCP `9200` and API `9300`,
the original BoxedWine client completed the following route without clicking an
in-world door or portal:

```text
S2C 000D[00] (manual controller boundary)
  → natural C2S 0016[01] ×5
  → request-bound S2C 0004[01] ×5
  → natural C2S 0064[01]
  → S2C 0064 (27 B; Plaza)
  → controller S2C 006E[0000]
  → natural C2S 00C8 (empty)
  → S2C 00C8 (14 B all zero), S2C 00CC, S2C 00CE (131 B)
```

At the server boundary the client was admitted to `OX Quiz (mode 2)`, default
room, participant `2`, question `1 + 1 = 2`; no server-side rejection or
missing response occurred.

Immediately after `S2C 00CE`, the BoxedWine process exited. The guarded host
AV is identical to the prior UI-driven reproduction:

```text
EIP=7F3BDFB8  fault=33006D10  EAX=33006D00  BMAP readable=0
PANEL x=00073C00 (463), y=00081800 (518), flags=00004000
return=acknex!0x10010957 (generic panel render loop)
```

## Conclusion

**VERIFIED:** manually navigating the Plaza/OX portal is not the cause of the
guest crash. A protocol-controlled portal reply reaches the same mode-2
admission and the same invalid OX GUI background pointer. The remaining cause
is therefore below portal selection/route input: live ownership or last writer
of the panel at `(463,518)` remains **NOT VERIFIED**.

This creates a reusable low-interaction OX repro: select the existing character,
then use `000D` and `/api/ox/enter`; no world click is needed after PatHouse.

## Evidence

- `tools/launch_gate2b_protocol_portal.py`
- `artifacts/boxedwine/20260719_gate2b_native/server_9200_control9300_protocol_portal_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_protocol_portal_stdout.log`
- `docs/research/145_GATE2B_VULKAN_OX_C8_GUEST_AV_20260719.md`
