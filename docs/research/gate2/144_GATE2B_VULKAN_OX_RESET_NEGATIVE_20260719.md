# 144 Gate 2b: Vulkan OX Reset negative result

Date: 2026-07-19

Status: **VERIFIED** for the traced Wine 11 Vulkan run.

## Purpose

Test the proposed explanation that the original Vulkan OX-after-C8 exit (142)
was caused by a D3D9 device `Reset` or device-loss path.

## Natural OX evidence

The existing isolated Wine 11 Vulkan account was launched with
`WINEDEBUG=+d3d9,+d3d`. The normal client path reached Plaza and then OX. The
same preservation-server log contains two natural portal attempts:

```text
attempt 1: C2S 006B -> S2C 006E -> C2S C8 -> S2C C8 -> disconnect
attempt 2: C2S 006B (#64) -> S2C 006E -> C2S C8 (#67) -> S2C C8
```

For attempt 2 the user observed successful OX-quiz entry while the BoxedWine
process remained live at that observation point. Later no-D3D-trace and
SEH-only repetitions reproduced the C8 guest crash; do not use this temporary
survival observation to classify the exit as non-deterministic (145).

## Reset result

The 608,282,236-byte trace contains exactly two D3D9 Reset entries:

```text
4704: d3d9_device_Reset
5269: d3d9_device_Reset
```

Both appear during initial device creation/configuration, before the millions
of subsequent render-trace lines and before either OX portal attempt. There is
no later `d3d9_device_Reset`, `d3d9_device_TestCooperativeLevel`,
`D3DERR_DEVICELOST`, or `D3DERR_DEVICENOTRESET` record at OX entry.

Therefore **Reset/device-loss is excluded as the observed OX-entry mechanism
in this run**. 145 subsequently proves the repeatable guest-side C8 access
violation, so 142 can no longer treat Reset as its leading branch.

## Consequences

- The post-C8 server-contract hypothesis was already excluded by 122 and is
  additionally inconsistent with the successful second Vulkan OX entry.
- The reproduced disconnect lies outside the D3D9 Reset/device-loss path
  measured here (145).
- The browser-backend decision remains governed by WineD3D's missing room,
  not by the historical Vulkan OX exit.

## Evidence

- `artifacts/boxedwine/20260719_gate2b_native/server_9200_wine11_vulkan_seeded_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_ox_reset_trace_retry_stdout.log`
