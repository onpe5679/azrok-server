# Gate 2c: one-session multi-entry browser hotness gate

Date: 2026-07-21

## Build

- diagnostic macro: `BOXEDWINE_D3D9WEB_ENTRY_PROBE_MULTI1`
- app package: `Azrok_D3D9Web_pathouse_fvfcache_release1.zip`
- JavaScript SHA-256:
  `628FB67CAE89F95CFFEA72D54C9D391690B36A31C7C0B63D187D7767D143470E`
- WebAssembly SHA-256:
  `3F5143AFC4F2C4B981BC32368644AD7AEF09D1F7F0BF313343617C8B2119917F`

The five counters are shared `std::atomic<U32>` values with relaxed increments
across pthread workers. Browser messages publish count 1 and powers of two; the
visible values below are therefore verified lower bounds, not final exact
totals. Each RVA emitted a mandatory zero control and a relocated address.

## Full PatHouse result

The 1024x768 scene rendered with the accepted wall, doorway, carpet, table,
stool, character, face, shadow, HUD, Korean text, alpha, and culling result.
The final sampled frame reported `dpupCount=209544` and these exact-entry lower
bounds:

| RVA | relocated address | published lower bound |
|---|---:|---:|
| `0x0008E0A0` | `0x7F3EE0A0` | 33,554,432 |
| `0x0008E05E` | `0x7F3EE05E` | 33,554,432 |
| `0x00046760` | `0x7F3A6760` | 16,777,216 |
| `0x00049650` | `0x7F3A9650` | 16,777,216 |
| `0x000467AA` | `0x7F3A67AA` | 1,024 |

No relocated-address mismatch was observed. The server delivered the 736-byte
PatHouse bootstrap at `00:56:25.741Z`; the guest returned the expected 20-byte
and 45-byte follow-ups, then heartbeats continued until the tab was
deliberately closed at `00:59:24.258Z`.

## Decision

`0x8E0A0` and `0x8E05E` are the first genuinely hot dispatcher-visible
candidates. Implement `0x8E0A0` first because it is a three-instruction,
read-only loop latch and fits the existing guarded read/branch tier. The
write-bearing `0x8E05E` waits until that lower-risk A/B is complete.

The probe build performs five comparisons per dispatch and is not an FPS
baseline. Only a counter-free release build may be compared against the
current 33--34 FPS release band.

