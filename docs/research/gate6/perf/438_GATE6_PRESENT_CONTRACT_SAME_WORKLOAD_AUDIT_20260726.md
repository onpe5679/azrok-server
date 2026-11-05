# 438. Present measurement contract: same-workload witness audit

Date: 2026-07-26  
Status: **VERIFIED existing-observability boundary; scene identity remains NOT VERIFIED**

## Why 437 cannot be repaired by reinterpreting existing counters

The attached sampler's direct source is intentionally narrower than a guest
scene assertion. `Measure-CdpPresentWindow` checks the expected URL,
visibility, CSS `1024x768`, and increasing direct Presents; its own source
states that Present activity alone cannot distinguish loading/selection from
PatHouse (`tools/browser_diagnostics/CdpPresent.psm1`, lines 79--98 and
137--146). Thus its valid rows in 437 cannot retrospectively be called a
same-workload proof.

Read-only CDP inspection of the live B2 page directly verified the exact
private replay identity (`registered`, `154/48,902/41,721`, helper ABI1), a
visible existing `#d3d9web-canvas` at CSS/intrinsic `1024x768`, and increasing
`D3D9WebDebug.presents`. `D3D9WebAsyncRingDebug` exposed callbacks,
sequences, errors, gaps, and reorders; its latest eight complete windows were
contiguous sequences 16,441--17,400, each with 120 submitted/reaped Presents,
inflight/max-inflight 1/1, ring-full 0, sync-drains 120, and errors 0. The
textarea independently carried the corresponding `D3D9WEB_PRESENT_WINDOW` and
`D3D9WEB_ASYNC_RING_FRAME` lines. No restart, navigation, build, cache
generation, FPS sample, or source change occurred in this audit.

Those are **VERIFIED renderer/bridge-continuity facts only**. They do not
export room, player, camera, geometry, or D3D command composition.

## Static boundary

`D3D9WebDebug.presents` increments only when host dispatch receives
`COMMAND.PRESENT`; in lean mode its other command/opcode counters are inactive
(`web_backend/host/d3d9web-runtime.js`, lines 147--183 and 2825--2906).
The async ring requires terminal opcode 11 (Present), records callback
sequence/error state, then dispatches the raw batch
(`source/opengl/d3d9web.cpp`, lines 399--432 and 441--493). This supports a
strong dispatch/reap liveness proxy, not a scene identity.

The page argv binds root/app/batch/resolution/audio but no current guest-room
or camera export (`index_d3d9web_pathouse.html`, line 151). The WS bridge is a
raw binary relay with byte-count logging, not a semantic room-state source.
Existing `D3D9WebProbe` is startup inventory and lean mode intentionally
disables hot command/profile diagnostics. Turning non-lean/host profiling on
inside an FPS leg would change its workload and is not permitted as evidence.

The existing `D3D9WebRuntime.samplePixels` uses `gl.readPixels` on the existing
context. It creates no context, but animation and synchronous readback make it
an unsafe fingerprint without a separate stable-point/tolerance contract; it
was not invoked.

## Decision and next contract

The next card must add a **separate, non-FPS diagnostic** workload witness
before any INT9A rerun. It must be fail-closed and role-neutral: normalize the
full launch tuple (`root`, `app`, `p`, `resolution`, `ws`, audio and input
flags, lean flags, sound), with only build/stem/cache/candidate mode
role-dependent; record both direct Present and async callback/sequence deltas;
and directly seal a scene-relevant batch or guest-state fingerprint. The
diagnostic must establish its own stability on fresh accepted controls before
being used as an admission gate. Existing counters cannot be promoted to that
role.
