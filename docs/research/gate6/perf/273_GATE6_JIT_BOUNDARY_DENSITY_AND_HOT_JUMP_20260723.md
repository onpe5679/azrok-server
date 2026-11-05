# 273 - JIT boundary density and exact hot-jump gate

Date: 2026-07-23 KST

## Current result

- **VERIFIED dynamic/browser:** a timer-free counter in the accepted
  publication-safe PatHouse replay measured 464,419,085 outer compiled-WASM
  activations across 1,440 real Presents: **322,513.25 activations/frame**.
  The same windows had 0 interpreter fallback blocks.  This proves that the
  remaining JIT problem is short compiled-block dispatch density, not missing
  JIT installation.
- **VERIFIED dynamic/browser:** the async ring was not saturated in those
  windows (`ring_full=0`, `max_inflight=1`, zero FIFO errors).
- **VERIFIED static/build/browser / forward-only gate rejected early:** SCC
  forward-edge cycle breaking produced 13,989 publication-safe rewrites
  (3,176 more than the accepted 10,813) and validated 134/134 group modules.
  Its stable PatHouse windows measured 313,438.13 outer activations/frame,
  only **2.814% fewer** than control.  This is too small to be the missing
  5--6 ms/frame lever, so a full FPS A-B-A was intentionally skipped.
- **VERIFIED prior profile + current static:** the hottest known Acknex loop is
  the `acknex+0x49650` island.  Its persistence manifest includes a self
  `jump` edge, while every accepted grouped-cache rewrite so far targeted only
  `next1/next2`; therefore cyclic8 never stitched this hottest edge.
- **VERIFIED static / exact hot-jump candidate rejected before build:** the
  raw manifest's `0x7F3A9650 -> 0x7F3A9650` self-`jump` is located after an
  unconditional `CALL`/`next1` return.  Binaryen therefore removes that arm as
  unreachable, and group 113 contains no surviving jump success arm for the
  structural matcher to rewrite.  The experimental build was stopped and no
  ZIP was deployed.
- **IN PROGRESS:** the next gate is a generic, bounded worker-local
  `return_call_indirect` tail.  Unlike another single-edge special case, this
  can cover dynamic indirect thunks and `RET` targets and therefore has a path
  to reducing the measured 322,513 outer activations/frame materially.  It is
  fail-closed behind exact `nextOp`, live publication, table readiness,
  relocation-base, yield, bailout, and depth guards; the original dispatcher
  return remains the fallback.

## Counter definition

`jit_blocks` increments once at the C++ `boxedwine_wasm_call_block` boundary.
Direct Wasm `return_call` tails inside a grouped module do not increment it.
Consequently the per-Present difference directly measures how many expensive
outer dispatch activations an offline stitch actually removed, without a
clock call in the hot path.

Control aggregate (last 12 stable windows):

```text
presents=1440
wall_us=36743000
jit_blocks=464419085
warmup_blocks=4167
pending_blocks=372
nojit_blocks=0
jit_blocks/frame=322513.2535
```

Forward-only aggregate (last 6 stable windows):

```text
presents=720
wall_us=18814000
jit_blocks=225675457
warmup_blocks=10547
pending_blocks=5
nojit_blocks=0
jit_blocks/frame=313438.1347
boundary reduction=2.8139%
```

Both browser sessions retained the reference 1024x768 PatHouse scene and used
the fixed `bgmloop3-dsound80ms1` root.  The displayed profile-build FPS is not
used as a release acceptance number because the profile target also contains
older syscall clocks; only the zero-clock counters above are used here.

## Forward-only artifact

- ZIP: `tools/boxedwine_local/profiles/azrok-jit-grouped-hotnext12-cyclebreak1-pubguard1.zip`
- SHA-256: `8484A5F9A1D0AB876E26920A613D6DB4D2E7A6FADF7E59640FD8261F9DE04F0B`
- groups / entries: 134 / 41,625
- rewrites / patches: 13,989 / 41,967
- cycle-break candidate edges admitted: 4,348
- `WebAssembly.validate`: 134/134
- publication ABI: `pfnJitCodeOffset=12`, one token word

## Why the exact self-jump was not deployable

The verified hot island is not represented as one surviving static jump in the
optimized grouped module.  Its real flow is:

```text
9650 CALL 6760 -> indirect thunk -> transform -> RET
     -> second indirect thunk -> transform -> RET -> 9659
9659 interior JL 9650 (taken 99.949%) -> fall 966D -> outer RET
```

The current raw-manifest graph does not expose the indirect and `RET` edges
needed to complete that cycle.  Treating `9659 -> 9650` as an apparently
cross-SCC edge would therefore be unsafe and could create an unbounded chain.
The unused exact-jump matcher remains experimental and is not a production
artifact.

## Next acceptance gate

The generic indirect-tail build must first validate every grouped module, keep
publication/invalidation ordering fail-closed, reduce outer activations/frame
materially, and preserve the reference render/protocol/FIFO.  Only then is it
promoted to the adaptive real-environment A-B-A FPS protocol.  A small counter
delta is an immediate rejection and returns the browser to the accepted
publication-safe acyclic cache.
