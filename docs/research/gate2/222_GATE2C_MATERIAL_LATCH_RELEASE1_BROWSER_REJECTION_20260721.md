# Gate 2c: material-latch release 1 browser rejection

Date: 2026-07-21

## Scope

This is the first counter-free browser A/B for the live `0x1008E0A0`
INC/CMP/JC helper. It uses the accepted
`Azrok_D3D9Web_pathouse_fvfcache_release1.zip` app and enables only
`BOXEDWINE_D3D9WEB_MATERIAL_LATCH_AOT` on top of the existing hot-AOT release.

- JavaScript SHA-256:
  `27CA8E486FF6A464CEE1489C70FA76A099B8552C45B1A0875E62391F49837714`
- WebAssembly SHA-256:
  `C4903FBBF75698E8D17A7DD2896633019E7D2A60CC3EC752AB40B1164F19F454`

## VERIFIED rendering and transport

The 1024x768 PatHouse scene retained the accepted walls, doorway, carpet,
table, stool, character face and shadow, HUD, Korean text, alpha, and culling.
The automatic bootstrap arrived at `01:29:42.319Z`; heartbeats continued until
the deliberately closed tab produced `WS_CLOSED` at `01:32:07.431Z`.

## VERIFIED performance rejection

Five consecutive 5-second `D3D9WebDebug.presents` windows measured:

```text
32.200, 33.459, 32.910, 32.598, 33.393 FPS
mean = 32.912 FPS
```

Document 212's counter-free baseline mean was 33.842 FPS. This first helper is
therefore 2.747% lower, not an improvement. It is rejected in its current
form and is not selected as the default release.

The implementation validates the exact nine-byte code on every one of tens
of millions of latch entries using three separate KMemory reads. Static and
dynamic correctness remain valid, but that guard cost can erase the saved
three interpreter dispatches. The next iteration replaces those three calls
with one allocation-free resident-page byte snapshot, then requires a native
microbenchmark before another browser session.

