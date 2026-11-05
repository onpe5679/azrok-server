# 433. Fresh cache-OFF bootstrap delay: accepted control resolution

Date: 2026-07-26  
Status: **VERIFIED accepted-control delayed render; private rebuilt render still NOT VERIFIED**

## Correction to 432

432 stopped observing too early.  Its accepted cache-OFF control remained on the same sole visible primary-display page and later reached the real rendered scene.  The former 0-Present interval is therefore a delayed common bootstrap, not evidence that either the accepted stem or the rebuilt INT9A candidate is permanently stalled.

## Direct control evidence

The browser bridge accepted the fresh control connection about **5 minutes 40 seconds** after its page/asset load:

```text
06:20:17 KST  accepted HTML load
06:20:25 KST  accepted JS/Wasm and root/app ZIP requests
06:25:57 KST  9201 WS_ACCEPT -> TCP_CONNECTED(9200)
```

The service then directly records the paced `0x0016` heartbeats.  The current connection advanced `pre_select` 0 through 8; on the threshold, the existing opt-in server path emitted the slot-0 C2S-`0x0005` selection, after which server state reports `char_created=True` and the normal client `0x0017`/`0x0008` follow-up traffic.

Browser output subsequently contains repeated actual render windows, for example:

```text
D3D9WEB_ASYNC_RING_FRAME presents=120 submitted=120 reaped=120
  first_seq=8881 last_seq=9000 inflight=1 max_inflight=1
  ring_full=0 sync_drains=120 errors=0
```

The following windows continue through sequence 9480 with zero async errors, gaps and reorders.  A separate page probe at the same phase reported 1,527 direct Presents (HUD accumulation 1,440).  These are render/liveness facts only; neither is a 30-second FPS sample.

## Interpretation

`run_wineboot boot event wait timed out` appears before the eventual audio/D3D/socket/Present progression.  It is therefore **NOT VERIFIED** as a terminal failure or as the causal source of the delay.  The directly proven common gate is the fresh browser's delayed bridge connection plus the server's deliberately paced eight-heartbeat auto-select sequence.  Its exact cause is not yet fully decomposed.

The rebuilt INT9A run in 432 was terminated before this interval completed, so it has not yet supplied the required nonzero specialized direct witness.  It remains cache-OFF render-open, not rejected.  The next candidate run must retain the current fresh-process hygiene but wait through bridge connection and auto-select completion before declaring any 0-Present observation.

## Decision

No record/replay/FPS action is authorized yet.  The next live step is one fresh rebuilt-private cache-OFF run with a bootstrap readiness gate that waits for bridge connection and either a nonzero Present or a bounded, evidence-backed failure state.  Only then can the private record sequence resume.
