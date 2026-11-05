# 499 Gate 6 in-app host/GPU split (2026-07-28)

## VERIFIED

- The page-delivery interval matched worker-reported Present elapsed time at
  both high and low rates (`deliverySkewMs` within about 0.2 ms).  Page-realm
  message delivery is not the source of the sustained drop.
- In the low PatHouse state, 120 Presents took about 2.9--3.1 seconds and the
  host WebGL batch time rose from about 1.5 ms to 7.6 ms per batch.
- The low-rate sampled command profile contained roughly 159 DrawPrimitiveUP
  operations per batch.  Its sampled per-draw host cost is small individually,
  but their aggregate matches the larger batch cost.
- `EXT_disjoint_timer_query_webgl2` is available.  On the selection scene it
  reported `941 us` per batch; on the rendered PatHouse scene it reported
  `6310 us` per batch while direct Present was 40.8 FPS.  The current
  in-app PatHouse limit is therefore GPU/compositor-bound, not BGM, page
  delivery, or the guest network loop.

## Next test

- A lower 4:3 guest backbuffer is a justified adaptive-resolution candidate.
  It must preserve original UI/input/BGM and meet the 50 FPS floor in a
  visible direct-Present window before adoption.
