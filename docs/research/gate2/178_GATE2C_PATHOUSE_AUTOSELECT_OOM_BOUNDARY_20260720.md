# 178 Gate 2c PatHouse auto-select and memory boundary (2026-07-20)

## Scope

This is the one-scene browser rendering gate only. It does not broaden
gameplay/content QA.

## VERIFIED

1. A fresh browser session logged in as `player`, received an S2C `0x0000`
   lobby roster containing slot 0 `Azrok1`, and then sent normal C2S
   `0x0016` heartbeats. The preservation server's opt-in auto-select guard
   was directly logged as `char_created=False`, `has_characters=True`, and
   `sent=False` through its eighth pre-select heartbeat.
2. On the ninth heartbeat, the existing C2S `0x0005` selection handler ran
   for slot zero and emitted the normal PatHouse bootstrap: S2C `0x0003`
   (`Data\\Space\\PatHouse`), `0x0007`, `0x0005`, `0x000A`, and `0x000B`.
   The client followed with C2S `0x0017`, `0x0017`, `0x0008`, and continuing
   heartbeats. This bypasses the unreliable manual character-create click;
   it does not synthesize a client-side packet.
3. The SEH diagnostic package stayed connected past that transition and the
   browser visibly rendered the original PatHouse 3D floor, furniture,
   character, and 2D HUD. This re-confirms the bounded browser render gate.
4. The same run later emitted a browser-worker OOM, not a D3D9 API rejection:
   `Cannot enlarge memory arrays to size 537030656 bytes` with the active
   Emscripten initial memory fixed at `536870912` bytes. The page then showed
   `Exception thrown, see JavaScript console`. Therefore this build cannot be
   used for a sustained FPS claim after PatHouse asset growth.
5. The Emscripten makefile's memory value is now parameterized as
   `INITIAL_MEMORY ?= 536870912`; the ongoing isolated profile build passes
   `INITIAL_MEMORY=1073741824`. The default remains unchanged for unrelated
   targets.

## NOT VERIFIED

- The 1 GiB build has not yet rendered PatHouse or produced a steady-state
  `Present` FPS sample.
- A follow-up partial-upload package was built, but its browser console sample
  was not persisted. It is therefore not evidence that the recurrent
  `handle=10` buffer has a smaller dirty range or that the new package avoids
  OOM. The next run retains bounded 120-Present bridge/cache samples in
  `sessionStorage` for collection.
- The temporary server guard trace is diagnostic-only and must be removed
  before promotion of the auto-select runner.
