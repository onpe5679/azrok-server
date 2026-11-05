# 514 Gate 6 state-churn probe (2026-07-28)

## VERIFIED (static)

- Current in-app PatHouse has about 159 `DrawPrimitiveUP` calls per Present,
  but only about five directly adjacent pairs.  A draw-only merge cannot
  provide the required 50-FPS uplift without proving the intervening state
  commands redundant.
- `d3d9web-runtime.js` previously marks every received render-state and
  texture-stage-state command dirty, and binds every received texture even
  when the client resends the same value.
- URL-gated `stateChurnProbe=1` now counts same-value versus total commands
  for render states, texture-stage states, sampler states, texture bindings,
  and stream bindings.  It emits one `D3D9WEB_STATE_CHURN` result per 120
  Presents and does not suppress, reorder, or change any command.
- `node --check tools\\boxedwine_local\\web_backend\\host\\d3d9web-runtime.js`
  and `python tools\\test_d3d9web_page_contract.py` both pass after the
  addition (2026-07-28).

## NOT VERIFIED

- No visible PatHouse 120-Present state-churn result has yet been collected.
  A same-value count alone is not permission to skip a state command; any
  optimization requires visual/BGM-preserving A/B measurement and the three
  30-second 50-FPS acceptance windows.

