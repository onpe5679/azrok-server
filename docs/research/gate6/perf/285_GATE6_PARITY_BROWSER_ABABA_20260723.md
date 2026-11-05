# 285. Gate 6 parity browser gate and adaptive A-B-A-B-A

## Status

- **VERIFIED raw record:** `azrok-jit-record-parity67-cfoffix-record2-raw.zip`
  is 62,459,642 bytes, SHA-256
  `3C7ED608364695374AD05807A3A98DA96835A8D80C769231B1CBA7F3145AC13E`.
  It contains 41,792 unique v5 Wasm blocks, and the manifest count is also
  41,792.
- **VERIFIED final grouped cache:** `azrok-jit-grouped-commonfast64-depthlocal-inlinefetch-parity67.zip`
  is 6,735,149 bytes, SHA-256
  `B72A4F53A9FE2DD465946BDB4458207F81B8B369AC700F8636DFE903C449E3DB`.
  The final manifest has 41,792 entries, 135 groups, and 32,433 direct-call
  patches. All accepted pipeline options remain identical.
- **VERIFIED static gate:** all 135 group modules pass
  `WebAssembly.validate`. Binaryen text inspection finds zero actual calls
  to both `fn_22` (P) and `fn_23` (NP).
- **VERIFIED browser/runtime:** the parity cache registered as
  `groups=135 entries=41792 patches=32433`; the first JIT block executed; the
  client completed login, heartbeat #9 auto-select, `Data\Space\PatHouse`,
  `0x0007/0x0005/0x000A/0x000B`, two `0x0017` requests, and `0x0008`.
  The 1024x768 PatHouse render retained the reference walls, carpet, character,
  furniture, Korean UI, and texture output.
- **VERIFIED completed adaptive measurement:** exact visible PatHouse windows
  were A1 49.0516, B1 44.5769, A2 43.2118, B2 44.8233, and A3 44.6550 FPS.
  The four candidate-relative adjacent-boundary deltas were -9.1224%,
  +3.1590%, +3.7292%, and +0.3767%; their median was only +1.7679%, inside
  the predeclared approximately +/-3% noise band. The bracketing-B median was
  -0.6725%, and the condition means were A 45.6395 versus B 44.7001 FPS
  (-2.0583%).
- **VERIFIED decision -- do not adopt parity67:** parity67 produced no
  significant browser improvement. Keep the accepted ABI2 runtime/cache as
  the active baseline. This rejects this cache transformation, not the static
  correctness of its P/NP/CFOF implementation.

## Direct evidence

The final cache build reported:

```text
Optimized: 41792/41792
Groups: 135
Direct calls: 10811 tail sites rewritten
MT generic indirect: 301714 common-dispatch tails rewritten
Reloc: 37537 entries with slot arrays, 32433 direct-call sites patched
Zip bytes: 62,459,642 B -> 6,735,149 B
```

Independent final-file reinspection confirmed:

```text
WebAssembly.validate: 135/135
fn_22(P) actual calls: 0
fn_23(NP) actual calls: 0
```

The dynamic server sequence was:

```text
login 0x0000
heartbeat #9
AUTO-SELECT EXISTING slot 0
S2C 0x0003 Data\Space\PatHouse
S2C 0x0007, 0x0005, 0x000A, 0x000B
C2S 0x0017 x2, 0x0008
heartbeat continues
```

## Adaptive measurement

The decision windows used exact `D3D9WEB_FPS_SAMPLE` Present deltas, not a
visual HUD estimate.

| Leg | Runtime/cache | Exact FPS | Visibility | Renderer average CPU |
|---|---|---:|---|---:|
| A1 | accepted ABI2 / accepted cache | 49.0516 | visible | not available after reboot PID remap |
| B1 | parity67 / fresh parity cache | 44.5769 | visible | 218.230% |
| A2 | accepted ABI2 / accepted cache | 43.2118 | visible | 219.044% |
| B2 | parity67 / fresh parity cache | 44.8233 | visible | 220.249% |
| A3 | accepted ABI2 / accepted cache | 44.6550 | visible | 216.775% |

The baseline moved -11.9054% between A1 and A2, above the adaptive 3% drift
gate, while the two candidate windows differed by only +0.5527%. The closing
A3 was therefore required and was collected after a user Reload restored the
same tab.

A3 direct evidence:

```text
Exact FPS: 44.6550453565
Present samples: 15
Present delta: 1800
Accumulated elapsed_ms: 40308.995
document.hidden: false -> false
visibilityState: visible -> visible
renderer PID: 66372
renderer CPU: average 216.775%, median 218.723%
foreground covariate: Idle 41/41 in the immediately preceding simultaneous window
```

The four candidate-relative adjacent-boundary deltas are:

```text
B1/A1 - 1 = -9.1224%
B1/A2 - 1 = +3.1590%
B2/A2 - 1 = +3.7292%
B2/A3 - 1 = +0.3767%
median       +1.7679%
```

That median is below the approximately +/-3% measurement-noise threshold.
The independently useful bracketed comparisons also disagree in sign
(-3.3704% for B1, +2.0254% for B2), with a -0.6725% median. Thus there is no
direct evidence of a meaningful improvement and parity67 is not adopted. No
loading-screen or character-select FPS was accepted.

## Service interruption

The first A3 attempt remained visible and continued to Present at roughly
150 FPS on the loading scene. The server received only the first heartbeat.
Afterward all four local ports (8765, 9200, 9201, and 9300) disappeared
together, which is consistent with the common supervisor exiting rather than
an isolated HTTP, TCP, or bridge failure. A new long-running supervisor
restored all four listeners. After the user performed the required same-tab
Reload, the accepted baseline completed login, heartbeat-paced automatic slot
selection, PatHouse bootstrap, and the final A3 measurement above.
