# 490 Gate 6 current control 50-FPS stability (2026-07-28)

## Direct result

The current default control page was freshly reloaded after the direct-Present
bridge repair.  It remained visible at the displayed `1024x768` PatHouse gate
for 305 seconds before measurement; its backing store was `640x480`, which is
the intentional page scaling contract.

After a 15-second warmup, three adjacent external 30-second direct-Present
windows gave:

| Window | Present delta | Wall time | Direct Present FPS | Source |
|---|---:|---:|---:|---|
| A1 | 5,574 | 30,005.738 ms | 185.7645 | `D3D9WebDebug` |
| A2 | 5,518 | 30,016.390 ms | 183.8329 | `D3D9WebDebug` |
| A3 | 5,562 | 30,003.576 ms | 185.3779 | `D3D9WebDebug` |

- **VERIFIED:** all windows were visible at both endpoints, had nonzero direct
  Presents, and passed the measurement validity checks.
- **VERIFIED:** the three-window range is 183.8329--185.7645 FPS (1.05% peak
  spread), comfortably maintaining the requested 50-FPS desktop floor.
- **VERIFIED:** the BGM primary route for this fresh control page was the
  separately verified native browser media containment route from 489.

## Scope

This is the current desktop control's 50-FPS maintenance proof, not an
optimization-candidate comparison.  A future change to runtime/JIT/rendering
still requires the stricter clean A/B/A (A/B/A/B on drift), working-set,
rate-stability, and sync-drain comparison contracts before replacing this
control.
