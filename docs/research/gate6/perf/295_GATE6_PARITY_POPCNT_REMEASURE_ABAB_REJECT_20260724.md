# 295. Gate 6 parity popcnt inline: overnight direct-Present A-B-A-B remeasurement

## Status

**VERIFIED static/runtime/browser / visible direct-Present A-B-A-B: REJECTED
for performance.** This is the required clean remeasurement of the already
correct parity67 artifact, performed because document 285's earlier adaptive
run had a 11.9% baseline drift and was inconclusive for performance direction.
It does not revise the static correctness result: P/NP helper calls remain
removed, and the parity runtime/cache pair remains fail-closed and reference
render-correct. It does decisively retain the existing decision not to adopt
the candidate.

## Exact paired artifacts and runtime proof

Each leg atomically selected both its runtime stem and its matching cache;
there was no cross-stem/cache mix.

| condition | runtime stem | cache | replay status |
| --- | --- | --- | --- |
| A | `boxedwine.upstreamjit64fn6inlineabi2` | `azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2.zip` | legacy-v2, 134 groups / 41,625 entries / 32,439 patches |
| B | `boxedwine.upstreamjit67parity1` | `azrok-jit-grouped-commonfast64-depthlocal-inlinefetch-parity67.zip` | legacy-v2, 135 groups / 41,792 entries / 32,433 patches |

**VERIFIED browser:** the B runtime reported `jitReplay=registered`,
`jitReplayPair=legacy-v2`, `jitReplayPublicationAbi=12`, and its exact
135/41,792/32,433 registration. Its generic and inline-fetch ABI strings
matched the accepted loader contract. Both conditions completed the normal
saved-character path and rendered the complete 1024x768 PatHouse room
(character, room geometry, furniture, HUD and Korean UI) before each capture.

No build, cache generation, or competing foreground workload was active during
any capture. All four windows used the strict page-realm
`D3D9WebDebug.presents` counter over a nominal 30-second interval while the
document remained visible; loading and character-selection frames were
excluded.

## A-B-A-B measurement

| leg | condition | direct Presents / seconds | FPS |
| --- | --- | --- | ---: |
| A1 | accepted ABI2 | 1,423 / 30.003 | **47.43** |
| B1 | parity67 | 1,364 / 30.000 | **45.47** |
| A2 | accepted ABI2 | 1,531 / 30.000 | **51.03** |
| B2 | parity67 | 1,435 / 30.006 | **47.82** |

The A1-to-A2 baseline moved +7.59%, beyond the +/-3% drift gate. The planned
three-leg run was therefore correctly extended to B2 rather than deciding from
A1/B1/A2 alone.

The two adjacent A-to-B effects have the same direction:

```text
B1 / A1 - 1 = -4.13%
B2 / A2 - 1 = -6.29%
median       = -5.21%
```

Both losses exceed the +/-3% noise band. The B condition also increased
45.47 -> 47.82 FPS in the same drift direction as A, so the extension does not
support treating B1 as an isolated environmental low point. The paired
candidate penalty therefore repeats despite the baseline drift.

## Decision

Keep `boxedwine.upstreamjit64fn6inlineabi2` plus
`azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2.zip` live. Do not
adopt parity67 and do not mix it into the next candidate. The runtime-lazy
Z/NZ pure-Wasm inline candidate may now begin as a separate cache/runtime
experiment with its own static gate, cache-OFF visual integrity gate, and
visible A-B-A only after its own fail-closed loader contract exists.
