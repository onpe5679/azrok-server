# 382 ??Cache-off transient bootstrap recovery

Date: 2026-07-25  
Status: **VERIFIED** ??the earlier bounded zero-Present state was transient;
not an FPS measurement.

## Direct dynamic observation

The watcher-fresh, sole visible accepted ABI2 cache-off control documented in
381 was left running without navigation, input, build, cache generation, or
performance capture. A later read-only CDP observation on that *same* page
directly found:

- `document.visibilityState=visible`, focus true, CSS/backing canvas
  `1024x768`;
- direct Present `4,388`, HUD Present `4,320`, HUD accumulated
  `43,748.5 ms`;
- textarea telemetry with `D3D9WEB_FPS_SAMPLE` and
  `D3D9WEB_ASYNC_RING_FRAME ... reaped=120 ... errors=0`;
- `Module.websocket` at `ws://127.0.0.1:9201` with binary subprotocol; and
- live OS TCP links renderer -> 9201 bridge -> 9200 game service.

The earlier 0-Present/no-9201 state and the later advancing-Present/connected
state are direct reads of the same control page. Therefore the bounded
zero-Present snapshot in 381 was a transient guest/bridge bootstrap phase, not
a durable common environment boundary and not evidence about MRG1 performance.

## Consequence

MRG1 generation-2 must be given an equivalent, explicitly bounded readiness
window and then independently prove cache-off real-game rendering before its
required fresh record -> private transform/pin -> replay-render ->
fresh-process accepted-vs-MRG1 A-B-A(B) sequence. No 30-second FPS value was
sampled or adopted here. Document 381 is retained as the earlier bounded
observation and is superseded for its persistent-boundary conclusion.
