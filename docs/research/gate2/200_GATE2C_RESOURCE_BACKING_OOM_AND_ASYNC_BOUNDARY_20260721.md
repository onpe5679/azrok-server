# 200 Gate 2c resource backing OOM and async boundary

Date: 2026-07-21

## Scope

One-tab, 1024x768 PatHouse Direct-DrawUP run. Static proxy/BoxedWine inspection
was paired with the existing live browser session. No native client or second
browser game was launched.

## VERIFIED -- OOM cause

- The failing `directdrawup1` session created one temporary texture per frame.
  Its last complete 120-frame window reported `direct_calls=242`,
  `direct_top_opcode=12:121`, and largest texture upload
  `handle=4577, kind=1, bytes=131072`.
- Immediately afterward Emscripten aborted while trying to grow the fixed
  1 GiB heap: `Cannot enlarge memory arrays to size 1073983488 bytes`.
- `Resource_Release` sent `COMMAND_DESTROY_RESOURCE` but intentionally retained
  both the small COM object and its large guest `data` allocation until process
  teardown. `CreateTexture` and `CreateBuffer` allocate that backing with
  `HeapAlloc`. The recurrent 128 KiB texture therefore leaked guest heap memory.

## VERIFIED -- fix and safety

- The proxy still retains the small zero-ref COM tombstone, which protects a
  late duplicate `Release` from a freed header.
- On first final `Release`, it now frees the resource backing after all upload
  bytes have been synchronously snapshotted into BoxedWine's owned batch.
- `TextureLock`, `TextureUnlock`, `Buffer_Lock`, `Buffer_Unlock`, and
  `Device_UpdateSurface` reject a destroyed resource or null backing. A final
  release while locked is logged and conservatively retains the backing.
- Static ordering proof: DirectUpload and DirectDrawUP copy caller-owned guest
  bytes into `batchedCommandBytes` before returning; no queued command retains
  the released guest `data` pointer.

Artifacts:

- DLL SHA-256: `F0E9D8ECFCDC94AD3A7BAFED5F8B15BE085BF213E4AB4ED280386CB081A7D681`
- package: `Azrok_D3D9Web_pathouse_directdrawup_oom2.zip`
- package SHA-256: `68105B3AC40B4095B555B289F488926E72C62952D5E1DA76889233081AF2ED84`

## VERIFIED -- live result

- The final package entered PatHouse through the existing ninth-heartbeat
  auto-selection route.
- Walls, floor, full carpet, table/chair, character face/shadow, HUD, Korean
  text, alpha, and culling remained intact.
- The same one-texture-per-frame workload continued past handles 4789 and 4909,
  beyond the old failure at handle 4577. Frame profiles continued at 23.02 and
  23.11 FPS with no OOM, exception, or `RESOURCE_RELEASE_LOCKED` report.
- Other complete post-fix PatHouse windows were 23.05, 22.41, 21.03, and 22.26
  FPS. The fix is a correctness/longevity fix; it does not claim a material FPS
  improvement.

## VERIFIED -- asynchronous submission boundary

The renderer is already asynchronous within a frame in the important sense:
state changes, binds, clears, draws, and upload packets are appended to one
ordered native batch and do not individually proxy to the browser main thread.
Current PatHouse still has about three synchronous crossings per frame:

- one Present batch submission;
- approximately one CreateTexture;
- approximately one DestroyResource.

Safe further pipelining requires a bounded 2--3 frame owned-buffer ring:

- DrawUP and Unlock may execute later only after their guest bytes are copied
  before the API returns.
- State, bind, clear, draw, upload, and ordered destroy can be queued.
- Readback, render-target locks, real query `GetData`, Reset/device-loss checks,
  and queue-full backpressure remain synchronous barriers.
- Create calls can be queued only if delayed host allocation failure is an
  accepted deviation; exact immediate HRESULT semantics require a wait.

This is useful but not a 50 FPS solution by itself. Complete windows currently
spend roughly 22--24% in worker-to-main proxy time; even an ideal overlap leaves
the interpreted guest work and host rendering. The next measurement must count
identical SetTexture/SetStreamSource/SetIndices/SetFVF/SetTransform/viewport/
scissor submissions and re-profile guest function ranges after DirectDrawUP.

## VERIFIED -- guest hotspot clarification

- The earlier 42.4% acknex / 36.6% proxy / 20.9% other split belongs to the
  pre-DirectDrawUP timeprofile7 build. It is not a current post-optimization
  absolute millisecond split.
- `acknex+0x46780` is the inner 24-byte position/normal transform-or-copy block;
  `+0x49650` is its 44-byte-record outer loop. They are one transform family.
- `acknex+0x8E050/+0x8E060` are adjacent blocks in one indexed mesh submission
  function that groups material/face runs before DrawIndexedPrimitive.
- No individual acknex block exceeded about 1--1.46% in the prior samples, so a
  single-block JIT/AOT is not yet justified. Function-range aggregation is the
  next valid CPU measurement.
