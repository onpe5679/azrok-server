# 426. INT 0x9A direct helper: production async all-route guest-batch witness

Date: 2026-07-26  
Status: **VERIFIED private cache-OFF served-game runtime; async P1 row closed**

## Scope and prior boundary

425 proved that the private `BOXEDWINE_WASM_JIT_INT9A_SEQUENCE_CENSUS` telemetry correctly binds route bits to the exact asynchronous terminal-Present slot, but the ordinary PatHouse route produced a valid coverage-negative mask-60 result.  That did not establish index 5 dead globally.  This card uses the already-existing, separately packaged real-game guest-batch application, not a synthetic `__TEST` route call and not an accepted artifact:

```text
app=Azrok_D3D9Web_pathouse_guestbatch1
runtimeStem=boxedwine.upstreamjit64fn6inlineabi2int9asequencecensus1
int9aSequenceCensus=1
jitCacheUrl=off
```

The telemetry JS/Wasm is the exact staged/served private target verified in 425.  The app ZIP is only selected by the private page URL; no accepted stem, ZIP, cache, record, replay or production direct helper is changed.

## Served-game runtime witness

**VERIFIED.** The one existing CDP `page` target was navigated directly to the URL above; no tab was created.  Immediately before start, `document.visibilityState` was `visible`, the private page reported its runtime-ready state, and the run control was activated by CDP pointer press/release rather than a DOM click.  The served game reached CSS canvas `1024x768` on the user-established primary display.

The page-owned ABI reader then returned this sealed record:

```text
[1,15,15,1,120,1681,1800,1800,120,60,120,1681,1800,60,11]
```

The fields establish all required facts simultaneously:

| Field | Direct value | Required invariant |
|---|---:|---|
| ABI / words / state | `1 / 15 / 1` | exact telemetry layout and sealed state |
| submitted / reaped slots | `120 / 120` | all terminal slots were callback-reaped |
| first / last / reaped sequence | `1681 / 1800 / 1800` | contiguous sequence closure |
| required / last route mask | `60 / 60` | exact index-2 terminal Present + upload + DrawPrimitiveUP + guest-batch route set |
| qualifying / first / last qualified | `120 / 1681 / 1800` | every sealed slot has that exact route mask |
| terminal opcode | `11` | each terminal is Present |

The same direct reader reported async-ring `callbacks=1877`, `errors=0`, `gaps=0`, `reorders=0`, and `lastSequence=1877`.  The telemetry only accepts a qualifier after main-thread dispatch returned `D3D9WEB_OK`, the exact slot reached callback-written `COMPLETED`, and the worker reaped that slot.  Its bit 2 is the terminal Present dispatch; the mask intentionally does not claim a separately distinguishable non-Present generic index-2 call.  It is therefore a completed JS-dispatch acknowledgement, not a GPU-completion claim.

## Decision

424's remaining async index-2..5 P1 row is now **closed**.  Together with 422/423, the prerequisite fixture/census matrix now has direct evidence for synchronous index/range/state/fault/SMC rows and the production async per-terminal all-route row.

This does **not** authorize a performance claim, cache, record/replay, or an unguarded Wasm replacement.  The next card may perform the separate static design/audit for one private C++ re-decode-guarded specialized helper only, preserving the 421 contract: EIP; all eight GP commits; all three protected stack reads; D3D/JS/EAX return behavior; successor and invalidation; and SMC/bailout fallback.  It must remain a distinct private stem until its own differential fixture, cache-OFF real-game render, fresh record/replay and primary-display Present A-B-A(B) gates pass.

No 30-second FPS sample was taken or used in this card.  The primary-display baseline remains unmeasured after the display move and must be re-established separately by fresh accepted A samples.
