# 199 — Gate 2c guest time profile and direct DrawPrimitiveUP

Date: 2026-07-21

## Scope

PatHouse one-scene browser run at 1024x768, one browser tab, no user input. The
character-selection placeholder text is excluded from visual acceptance per the
user's instruction.

## VERIFIED — measurement method

- `normalPlatformMultiThreaded.cpp` samples one in 32 `cpu->run()` calls.
- The final `timeprofile7` build uses 10-second windows, 8,192 block slots, and
  an 8,192-read average timer calibration. The measured timer overhead was
  291 ns and dropped blocks were zero or negligible.
- `active_pct_x100` remains invalid: per-run browser timer quantization and
  instrumentation overhead make the extrapolated absolute active time exceed
  wall time. It is not used below.
- Module and block percentages are relative shares of the same sampled guest
  run time. Four complete `pid=71, tid=72` windows were collected only after an
  intact, idle PatHouse became visible.

## VERIFIED — guest CPU shares

Weighted over four 10-second PatHouse windows (`sample_us` total 3,920,089):

| Guest component | Sampled guest run-time share |
|---|---:|
| `acknex.dll` total | 42.4% |
| proxy `d3d9.dll` total | 36.6% |
| Wine/libc/ntdll and other | 20.9% |

Largest individual blocks:

| Block | Meaning | Weighted share |
|---|---|---:|
| private `d3d9.dll+0x10E0` | byte-at-a-time `ByteCopy` loop | 29.2% |
| private `d3d9.dll+0x1140` | `D3D9WebCall` | 5.1% |
| `acknex.dll+0x46780` | object/copy/transform dispatch | about 1.46% |
| `acknex.dll+0x49650`, `+0x8E050/60` | object loop and DrawIndexed submission | about 1% each |

`acknex.dll` is the largest module in aggregate, but its cost is distributed.
The proxy byte copy is the largest removable single block. These guest shares
must not be added to `proxy_pct`: a synchronous `D3D9WebCall` can include the
same worker-to-main wait measured by the host bridge.

## VERIFIED — copy-site measurement before optimization

The unoptimized proxy emitted per-callsite calls and bytes once per 120
Presents. In stable PatHouse every window reported:

- `DrawPrimitiveUP` payload: 18,480 calls, about 29.15 MB
- transform copies: 7,200 calls, 460,800 bytes
- DrawUP headers: 18,480 calls, 443,520 bytes
- clear: 480 calls, 9,600 bytes
- UpdateSurface/palette/declaration: zero in steady state

This establishes DrawUP payload copying as the first optimization target before
implementing it.

## VERIFIED — `rep movsd/movsb` candidate

- Replaced the proxy byte loop with `cld; rep movsd; rep movsb`.
- Static disassembly verified callee-saved ESI/EDI preservation and `cld`.
- All 12 legal call sites are non-overlapping; UpdateSurface explicitly rejects
  a same-texture copy.
- Stable A aggregate: 17.95 FPS. Stable B aggregate: 20.44 FPS. A2 aggregate:
  19.49 FPS. The improvement was positive but close to session drift.
- A later B2 run had only 1,920 uploads/53.12 MB instead of 2,160/60.44 MB and
  was rejected as a different graphics workload.

## VERIFIED — direct DrawPrimitiveUP

Implementation:

- Guest sends a fixed 24-byte descriptor through `D3D9WebCall(base+4)`.
- BoxedWine validates primitive count/stride/byte size and synchronously copies
  vertex bytes from guest memory directly into the ordered host batch before
  returning. It never retains the guest pointer until Present.
- The existing JS packet remains `[24-byte opcode-10 header][vertex payload]`.
- Unsupported older hosts return a known failure value and the proxy falls back
  to the original packet path.

Static safety and runtime results:

- DLL SHA-256: `6B39DA5DD1C49115C5015FF9978B5906E0390B15777E703817AA2B2625BD6334`
- WASM SHA-256: `CA3DA3CDDDEEAF158EED4F9AEB7AEE6FFF7B1C2ECF70127EF1D03863045D7414`
- Package SHA-256: `0970C911C214FCE1807451E8EC4D92D16DDBB089518F7C3C549F9B4C7932969E`
- Stable PatHouse windows: 22.21, 21.23, 22.84, 22.33 FPS.
- Equal-frame aggregate: `480 / 21.675 s = 22.15 FPS`.
- Same DrawUP workload remained present (18,480 calls/about 29.15 MB per 120
  frames), while the guest byte copy was bypassed.
- No direct-DrawUP reject, bad DrawPrimitiveUP, bad upload, GL error, SEH, or
  OOM was observed.
- Walls, floor, full carpet pattern, table/chair textures, character face and
  shadow, alpha, HUD, Korean text, and culling remained intact.

Compared with the two unoptimized A aggregates pooled by equal frames
(`18.65 FPS`), direct DrawUP is approximately 18.8% faster. It is accepted as
the current browser candidate, but it is not close to the 50 FPS goal.

## Next measurement gate

`acknex.dll` is now the largest aggregate guest module (42.4%), while no one
acknex block dominates. The next optimization must measure either a wider
trace/JIT coverage set or the per-frame dynamic VB/IB upload producers. Do not
infer a single x87 hotspot: the measured leaders are integer copy/control and
draw submission, and the previously observed matrix block is SSE.

