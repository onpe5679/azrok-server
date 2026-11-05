# Gate 6: recycle topology gate and recomposition A/B (2026-07-22)

## Scope

This gate followed document 266. It first measured the remaining synchronous
guest-worker to renderer-main boundary after the exact transient RGB565 handle
recycle became steady. It then recomposed the previously retained standalone
zero/conditional optimizations into one build, as requested, and compared that
build against the current accepted release under the new scheduler policy.

All dynamic runs used the original `Azrok.exe`, one browser tab, 1024x768
PatHouse, no gameplay input, and a page that remained
`visibilityState=visible` and `hidden=false`.

## 1. Frame-boundary topology after handle recycle

### VERIFIED - static instrumentation

The existing `boxedwine.bridgeopt1` runtime is the accepted ordered sync-tail
bridge profiler. It records one clock only around each actual main-thread
dispatch and classifies the flush reason. `reason_id=11` is the Present-terminal
ordered batch. The runtime hashes are:

- JS: `C54910A5308593F0E97789FBED834DDFE60A4A149ED93185691448FB21F53E68`
- Wasm: `E73FD08314FBCD47DE347B2D28907AA4DC87DC27BC93C64CA15DB3C2195AC8DB`

### VERIFIED - dynamic browser measurement

The profiler ran with `Azrok_D3D9Web_pathouse_guesttexrecycle4`.
Reference rendering remained intact: complete carpet UV, walls, table/chairs,
character face/shadow, Korean text, alpha and culling. There were no fatal,
OOM, bad-upload, GL, or bridge errors.

In steady windows the normal result was exactly:

- `main_roundtrips=120` per 120 Presents = 1 round trip/frame
- `mode=batch reason_id=11 calls=120`
- no `reason_id=12` CreateTexture row
- reason totals exactly equaled frame-profile totals

Nine clean 120-Present windows placed the single Present-terminal main-thread
wait at 5.3206--5.8404 ms/frame, 5.5970 ms/frame mean. Intermittent UI texture
updates produced isolated 121-round-trip windows with one `reason_id=12` tail;
therefore the topology is normally one terminal boundary, not permanently one.

**Decision:** the predeclared rejection threshold was about 1 ms/frame. The
measured terminal wait is greater than 5 ms/frame, so a frame-wide ordered
asynchronous producer/consumer ring remains the next large candidate.
Present-only async remains rejected; synchronous tails must drain the ring.

## 2. Integrated recomposition build

### VERIFIED - build/static composition

`tools/d3d9_web_backend/build_recompose_guest.bat` compiles both guest feature
gates into one proxy:

- `D3D9WEB_GUEST_BATCH=1` (guest `+5` ABI)
- `D3D9WEB_TRANSIENT_TEXTURE_RECYCLE=1` (exact handle-only recycle)

The resulting DLL is `d3d9_web.recompose1.dll`:

- DLL SHA-256: `8561D893D08851BBDC8627D67F7624446E57590EB1CFE7473660EA9EFCB14F0D`
- package: `Azrok_D3D9Web_pathouse_recompose1.zip`
- package SHA-256: `51D8F6375CC0378DDDA048F65CAE5C506962EC8195883D8A8EA73ED345B658E0`
- embedded `./d3d9.dll` hash exactly matches the standalone DLL

The all-ON browser condition also enabled `pool=1`, `shaderColor=1`, and
`upRing=1` (ring-buffer/bufferSubData), while retaining `-O3`, the official MT
WASM JIT, ordered sync-tail bridge batching, Texture+Viewport cache, FVF cache,
and the RGB565 direct view. `chain8`, Transform cache, and host `upBatch` were
not enabled. Host `upBatch` is mutually exclusive with `upRing` and was not the
requested bridge-batching feature.

The all-ON build rendered the same accepted PatHouse reference and produced no
fatal, OOM, bad-upload, GL, or bridge errors.

## 3. Visible-background A/B under the new scheduler policy

Both conditions used `boxedwine.upstreamjit32bridgebatch`, one tab, and 1,200
real `COMMAND.PRESENT` calls. OS foreground was Comet at both the start and end
of each measurement; no foreground window was stolen.

| condition | elapsed | aggregate FPS |
|---|---:|---:|
| accepted control (`statecache_release1`) | 36.407 s | 32.9607 |
| all-ON recomposition (`recompose1`) | 37.385 s | 32.0984 |

The integrated result is -2.616% versus control. It does not satisfy the
requested meaningful-uplift condition.

### Decision

- **REJECTED as an integrated performance build:** no uplift; do not adopt.
- Do not run reverse one-by-one decomposition because that was conditional on
  a positive integrated result.
- Standalone zero/negative results are now confirmed not to reveal a hidden
  positive interaction in this requested combination.
- Return to the same-thread topology candidate: a frame-wide ordered async
  ring with explicit drain points and generation/error propagation.

## 4. Scheduler calibration status

The new policy was directly rechecked as `Win32PrioritySeparation=0x18`.
This document adds a valid visible-background A/B, but a same-environment
natural Codex-foreground interval was not available because the user was using
other applications. Foreground/background delta calibration remains PARTIAL;
future work must not steal focus merely to complete it.

