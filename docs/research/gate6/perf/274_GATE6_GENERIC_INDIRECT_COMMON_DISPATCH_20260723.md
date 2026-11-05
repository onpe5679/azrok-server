# 274. Gate 6 — generic indirect common dispatcher

Date: 2026-07-23 KST

## Status

- **VERIFIED:** The release-ABI common dispatcher cache is structurally valid and preserves the accepted PatHouse rendering.
- **VERIFIED:** It removes 98.4628% of outer C++ -> compiled-Wasm activations in the profile build.
- **VERIFIED:** Release A-B-A-B improves the robust adjacent median by 20.7996% and the condition mean by 18.6522%.
- **VERIFIED:** The accepted candidate is still below the final 50 FPS gate: best 49.1323 FPS, condition mean 44.3778 FPS.
- **VERIFIED / NOT ADOPTED:** A post-publication plain relocation-map load candidate was structurally safe on the current startup-only loader, but its performance was not reproducible and it failed the 50 FPS gate.

## Measurement correction: profile ABI

The earlier profile runtime placed four `BOXEDWINE_AZROK_WAIT_FRAME_PROFILE` counters in the middle of `CPU`. Saved Wasm modules embed `CPU` member offsets, so replaying those modules against that profile layout changed every later field by 16 bytes. Comparisons made with that mismatched profile build are invalid and must not be used as release evidence.

The counters now live at the end of `CPU`. Direct getter disassembly verifies the corrected profile ABI:

| Field | Offset/value |
|---|---:|
| `CPU::nextOp` | 740 |
| direct-chain depth | 1660 |
| bailout | 132 |
| `DecodedOp::pfnJitCode` | 12 |
| profile reloc map | 12977448 |
| reloc map capacity | 262144 |

The release57 runtime differs only in its map address, directly verified as `12963176`.

## Common-dispatch artifact

Release artifact:

- `profiles/azrok-jit-grouped-commonfast64-releaseabi1.zip`
- SHA-256 `BDAE891D823DE742AD4A143FC10EBB48F965BADF4E4D35CBFF62CF04C32A828A`
- 134 groups, 41,625 exported entries
- 44,721,921 uncompressed Wasm bytes
- 300,477 rewritten common tails:
  - fallback 245,517
  - fast-success 54,960
  - three-load 29,102
  - jump 25,858

**VERIFIED static:** all 134 modules pass `WebAssembly.validate`; every group has exactly one byte-identical dispatcher; entry functions contain no duplicated `table.size/table.get` guard; old map `12977448` occurs zero times; release map `12963176` occurs once per dispatcher and zero times in entries.

## Boundary result

Corrected profile windows, each 120 Presents:

| Cache | JIT block dispatches |
|---|---:|
| publication-safe | 35,064,342 / 34,528,638 / 35,407,125 |
| common dispatcher | 544,541 / 531,025 / 538,530 |

Aggregate outer activations fall from 291,666.9583 to 4,483.6000 per frame: **98.4628% removed**, or **65.052x fewer** C++ -> compiled-Wasm entries.

## Release A-B-A-B

All four windows were `document.visibilityState=visible`, with `WindowsTerminal` recorded as the foreground application. Hidden/occluded samples were not used. PatHouse walls, carpet, furniture, character face, Korean UI, and 1024x768 D3D canvas remained reference-correct in both candidate runs.

| Order | Condition | dP | dM | FPS |
|---:|---|---:|---:|---:|
| 1 | A publication-safe | 6,120 | 150,469.995 | 40.6726 |
| 2 | B common dispatcher | 5,760 | 117,234.555 | 49.1323 |
| 3 | A publication-safe | 3,960 | 116,024.835 | 34.1306 |
| 4 | B common dispatcher | 5,040 | 127,197.630 | 39.6234 |

The A drift was -16.0844%, so the adaptive rule correctly extended A-B-A to A-B-A-B. Adjacent B effects are +20.7996%, +43.9536%, and +16.0933%; their median is **+20.7996%**. The conservative same-order pairs are +20.7996% and +16.0933%. Condition means are 37.4016 -> 44.3778 FPS, **+18.6522%**.

Frame time drops by 4.2334 ms in pair 1 and 4.0616 ms in pair 2, an unusually consistent approximately 4.15 ms/frame despite the environment drift. The common dispatcher is therefore adopted as the new baseline, but the 50 FPS goal is not yet met.

### CPU covariate correction

`dP/dM` is valid for FPS because any duplicate observations multiply numerator and denominator together. `dP` alone is not a physical frame count, so the earlier `renderer CPU / dP` values must not be called CPU ms/frame. Future windows record an independent wall interval and use it only as a covariate; it does not alter the FPS decision.

## Relocation-map plain load: not adopted

The common dispatcher still executes one shared relocation-map atomic load per guest block. The candidate retains the atomic `pfnJitCode` acquire and changes only the later map payload read to `i32.load`.

**VERIFIED static safety for the current Azrok startup-only loader:** the runtime writes `map[slot]` before publishing `pfnJitCode`; the map has one writer site, slots are monotonic and never reused, retirement does not clear the map, invalidation first exchanges `pfnJitCode` to null, and the outer active-owner hazard covers the complete synchronous tail chain. This is not automatically safe for an old runtime that enables generic mode after blocks have already been published, so the startup-only requirement must remain explicit.

Artifact SHA-256: `2965511F34A7133C559B8C882CB2E49508A9DB729296EBDD249C9AF4E342E598`. All 134 modules validate. Compared with atomic releaseabi1, all 41,625 entry bodies are byte-identical and each group changes only its final dispatcher's map read from `fe 10 02 00` to `28 02 00`; the pfn atomic load remains unchanged.

Fresh B-C-B-C results:

| Order | Condition | dP | dM | FPS | Wall ms |
|---:|---|---:|---:|---:|---:|
| 1 | B atomic map | 3,600 | 91,979.445 | 39.1392 | 30,061 |
| 2 | C plain map | 3,480 | 91,738.970 | 37.9337 | 30,053 |
| 3 | B atomic map | 3,240 | 83,992.890 | 38.5747 | 30,066 |
| 4 | C plain map | 4,080 | 90,001.680 | 45.3325 | 30,060 |

B drift is only -1.4423%, but C drift is +19.5045%. Adjacent C effects are -3.0799%, -1.6617%, and +17.5187%; the official median is **-1.6617%**. Although the pooled value is 41.5977 versus B 38.8697, it is driven by the unreproduced C2 outlier and is not adoption evidence. Corrected renderer CPU covariates conflict in the same way. The plain-load candidate is therefore retained only as an opt-in artifact and the atomic map load remains the default.

## Open gates

1. Re-profile the accepted common-dispatch release so the remaining guest execution, D3D bridge, and host rendering shares are measured after the 98.46% boundary reduction.
2. Choose the next optimization only from that new decomposition; do not continue one-instruction dispatcher variants without evidence.
3. Preserve PatHouse reference rendering, BGM loop, input, Korean text, and zero worker/table/ring errors in the final candidate.
4. Require pooled stable PatHouse FPS >=50.
