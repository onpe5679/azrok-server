# 142 Gate 2b: Wine 11 Vulkan OX entry exits after C8

Date: 2026-07-19

Status: **VERIFIED** packet sequence and client exit; exit cause **NOT VERIFIED**.

## Context

This occurred after the verified Wine 11 Vulkan PatHouse scene in 141. The
user drove the running native client from PatHouse through the natural outside
transition and clicked the OX entrance. Codex did not send any UI input or
terminate the BoxedWine process after the successful PatHouse screenshot.

## Captured sequence (VERIFIED)

The isolated preservation server recorded:

```text
C2S 0x0019                 natural PatHouse outside request
S2C 0x000D[00]             request-driven calibration arm
C2S 0x0016 / S2C 0x0004[01] x5
C2S 0x0064 / S2C 0x0064    natural Plaza transition
C2S 0x006B (empty)         natural OX portal request
S2C 0x006E (2 bytes)       OX portal reply
C2S 0x00C8 (empty)
S2C 0x00C8 (14 bytes)
client disconnected
Boxedwine shutdown
```

The server remained listening on port 9200 after the disconnect. The
BoxedWine stdout has no guest exception, and the local Windows Application
event log query for BoxedWine/Azrok/Application Error in the following
15-minute interval returned no event.

## Boundary

The observed exit is after the visible Vulkan PatHouse proof and after normal
Plaza/OX portal packet traffic starts. It therefore does not reverse 141's
PatHouse renderer result. It is a separate Gate 2b OX-state compatibility
investigation. The native client has already completed the same server's full
post-`0x00C8` OX sequence through Plaza recovery (122), so an incomplete OX
contract is excluded. A later traced run showed no D3D9 Reset/device-loss
event at entry (144), and a no-D3D-trace SEH run then reproduced an unhandled
guest `c0000005` immediately after S2C C8 (145). 145 subsequently maps the
fault to `acknex.dll!0x1001DFB8`, an invalid non-null panel-background BMAP
dereference; caller chain and asset/ownership root cause remain NOT VERIFIED.

## Evidence

- `artifacts/boxedwine/20260719_gate2b_native/server_9200_wine11_vulkan_seeded_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_seeded_pathouse_stdout.log`
