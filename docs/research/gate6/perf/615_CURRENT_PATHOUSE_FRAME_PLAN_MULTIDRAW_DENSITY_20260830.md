# 615 — Current PatHouse frame-plan / multi-draw density

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED implementation:** query-only `framePlanProbe=1` records complete
  draw-visible renderer state. It does not suppress, defer/buffer, merge or reorder a
  command. Clear, resource mutation, indexed draw and non-candidate DrawUP
  paths divide candidate segments.
- **VERIFIED visual/browser:** the accepted before/after screenshots both show
  actual PatHouse with the player Azron, rug, furniture, status HUD and clock.
- **VERIFIED dynamic:** one 120-Present PatHouse window contained 20,400 draws:
  19,080 DrawUP and 1,320 indexed, exactly 170 / 159 / 11 per Present.
- **VERIFIED dynamic:** 10,680 DrawUPs met the exact measured filter: blending
  off, depth test/write on, stencil off and full color mask. Their
  bit-exact canonical complete-state strings formed 1,560 segment-local groups.
  Per Present this is 89 candidates in 13 groups.
- **VERIFIED dynamic:** leaving the 81 non-candidates unchanged and replacing
  each candidate group by one call gives a theoretical 94 calls/Present,
  down from 170 by 76 or **44.7059%**. The largest one-frame group had 25
  draws.
- **VERIFIED browser:** the actual Edge/WebGL2 context returned
  `WEBGL_multi_draw.multiDrawArraysWEBGL`; support is not inferred from a
  compatibility table.
- **VERIFIED corrected rerun/repeat read:** after replacing JSON numeric
  serialization with bit-exact IEEE-754 serialization and adding viewport and
  host-mip identity boundaries, a fresh actual-PatHouse run produced the same
  counts. They remained identical when re-read after the native Present
  counter advanced from 8,358 to 8,653.
- **NOT VERIFIED / NOT ADOPTED:** equal complete state is not proof that
  non-adjacent draws may be reordered or that they are fully opaque. The
  measured artifact did not record alpha-test or depth-function distributions.
  Depth ties, alpha-tested cutouts,
  hidden framebuffer dependencies and state-group crossing still need an
  order proof. No `multiDrawArraysWEBGL()` call was added.
- **INFERRED priority:** the renderer has a real batching surface, but prior
  async-overlap measurements cap its contribution to critical-path FPS unless
  renderer work again becomes the longer side. The safer immediate steady-FPS
  candidate remains a guard-free structured guest-JIT region; frame planning
  stays as a parallel renderer track.

## Probe contract

At every DrawUP, after the production path has applied the vertex layout and
recomputed dirty transforms, the probe snapshots:

- primitive type, FVF and stride;
- viewport and scissor;
- every received render state;
- all bound texture identities, upload versions and optional host-generated
  material-mip state;
- sampler state;
- the complete fixed-function UBO state including transforms, material and
  active lights.

The current-frame canonical serialization string is used directly as the `Map` key, so
the count does not rely on a probabilistic hash. Strings are discarded on each
Present. The following make separate segments and therefore cannot be grouped
across by this count:

- clear and viewport/backbuffer resize;
- texture/buffer create, upload or destroy;
- any indexed draw;
- any DrawUP with blending, depth disabled, depth writes disabled, stencil,
  or a partial color mask.

Numeric state is serialized by exact IEEE-754 binary64 words before string
comparison, so `-0`, `+0`, NaN and infinities cannot be collapsed by JSON.
Object keys are sorted and array/typed-array order is preserved. The corrected
density result intentionally labels itself
`state-candidate-density-only-not-opacity-or-reorder-proof`. The first live
sample used a legacy field name and ordinary JSON serialization. A second
fresh PatHouse sample used the corrected bit-exact implementation and produced
the same values, so the table below is current-algorithm evidence.

## Actual PatHouse result

```text
window                         120 Presents
draws                          20,400  = 170/Present
DrawUP                         19,080  = 159/Present
indexed                         1,320  = 11/Present
state-filter DrawUP candidates 10,680  = 89/Present
candidate state groups          1,560  = 13/Present
theoretical calls              11,280  = 94/Present
theoretical reduction           9,120  = 76/Present = 44.7059%
largest group                       25
WEBGL_multi_draw support             yes
non-candidate reasons           blend 64/Present
                                depth-off 6/Present
                                indexed 11/Present
```

The corrected probe's short five-second direct-Present window was
62 / 5.017905 s = 12.3558 FPS. Exact recursive state serialization is
intentionally heavy; this FPS is diagnostic overhead evidence, not an A/B
candidate result. The earlier lightweight-schema run was 28.9213 FPS, but it
is not used as current-probe performance evidence.

## Why this is not yet a multi-draw implementation

The old adjacent-run probe found only five adjacent pairs among 159 DrawUPs.
The new 44.7% number is larger because it asks how many non-adjacent draws
return to exactly the same state. Turning that density into one multi-draw
call requires moving those draws next to one another. The measured
blend/depth/stencil/color-mask filter is useful, but it does not by itself
prove opacity or identical output
for equal-depth fragments or every alpha-test case.

A semantics-preserving implementation must therefore do one of:

1. prove order independence per segment from depth function and transformed
   geometry/depth overlap; or
2. retain original order and carry per-draw state/texture selection through a
   draw-ID aware shader/backend, which is a substantially larger design.

Visual similarity in one room is not enough to silently accept reordering for
other scenes.

## Verification

```text
node --check tools/boxedwine_local/web_backend/host/d3d9web-runtime.js  PASS
python tools/test_d3d9web_page_contract.py                            29/29 PASS
```

The page contract asserts the diagnostic gate and result label, requires the
only `multiDrawArraysWEBGL` symbol occurrence to be the support-property read,
and rejects any `multiDrawElementsWEBGL` occurrence.

## Artifacts

- `artifacts/performance/regional_frameplan_probe_bits1_actual_pathouse_20260830.csv`
- `artifacts/performance/regional_frameplan_probe_actual_pathouse_20260830.json`
- `artifacts/performance/regional_frameplan_probe_bits1_actual_pathouse_20260830.visual-review.csv`
- the two PNGs named in the visual-review CSV

## Next gate

1. Keep the probe, but do not enable it by default.
2. Implement and measure the lower-risk multi-laminar structured-loop JIT
   candidate identified by the current owner census.
3. In parallel, extend frame planning with an explicit order-independence
   classifier before writing a real multi-draw path.
