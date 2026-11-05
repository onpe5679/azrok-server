# Gate 6 host overlap, Present async ceiling, and safe state cache

Date: 2026-07-22 KST

## Conclusion

- **VERIFIED (OS dynamic):** the BoxedWine game worker and Chromium `CrRendererMain`
  overlap. Across two same-window `GetThreadTimes` runs, 22.01078 wall seconds
  contained 13.953125 worker CPU seconds and 8.65625 renderer-main CPU seconds.
  Their sum exceeds wall by 0.59860 seconds, proving at least 2.72% wall overlap.
  They must not be added as a serial critical path.
- **NOT VERIFIED:** exact runnable/blocked union time. ETW context-switch collection could
  not be started without disturbing an already active NT Kernel Logger.
- **VERIFIED (browser dynamic):** a three-clock-per-frame async-gap probe found that
  `Present` waits only 0.998625 ms/frame while the gap from that Present to the next
  synchronous `CreateTexture` tail is 8.842469 ms/frame. Present-only async execution
  can therefore recover at most about 1 ms/frame, not the missing 15--20 ms.
- **VERIFIED (current PatHouse measurement):** clock-free guest counters reconfirmed
  exactly 240 redundant transforms, 480 redundant viewports, and 1,560 redundant
  texture binds per 120 Presents. This is 2, 4, and 13 calls/frame respectively.
- **VERIFIED (implementation/static):** texture and viewport equality suppression is
  byte/pointer exact, disabled while recording a StateBlock, invalid after CreateDevice,
  Reset, or bridge failure, and becomes valid only after successful enqueue. Setter
  logical state and texture COM references now commit only after bridge success; failure
  rolls back rather than exposing host-divergent state to StateBlock Capture.
- **VERIFIED (browser/visual):** the retained texture+viewport release preserves the
  1024x768 PatHouse carpet, walls, furniture, character, face, shadow, Korean text,
  UI alpha, and culling.
- **PARTIAL (performance):** two foreground-guarded texture+viewport sessions pooled
  2,880 Presents / 85.349 s = **33.744 FPS**. Two control sessions pooled 2,640
  Presents / 81.411 s = **32.428 FPS**. The aggregate difference is +4.06%, or
  about 1.203 ms/frame. Session variance is material, so this is retained as a small
  optimization, not claimed as a new 50-FPS-class lever.
- **REJECTED:** adding transform equality comparison. One controlled 1,440-Present
  run was 32.540 FPS versus the two-session texture+viewport aggregate 33.744 FPS;
  the interpreted 64-byte comparison costs more than two saved calls/frame. The
  production default leaves transform caching disabled.

## Exact overlap evidence

Same-window OS CPU accounting produced:

| wall | worker CPU | renderer-main CPU | minimum overlap |
|---:|---:|---:|---:|
| 12.00951 s | 8.03125 s | 4.53125 s | 0.55299 s |
| 10.00127 s | 5.921875 s | 4.125 s | 0.04561 s |
| **22.01078 s** | **13.953125 s** | **8.65625 s** | **0.59860 s** |

A separate 1.367-ms cycle-counter bin sampler saw both counters advance in
5,286 / 7,317 bins (72.24%). That is interleave/coactivity evidence, not an
exact simultaneous-duration measure.

The retained no-profile OS budget remains:

- worker CPU: 18.786 ms/frame;
- renderer-main CPU: 11.225 ms/frame;
- worker non-running residual: 11.124 ms/frame;
- host JavaScript execution: 5.805 ms/frame in its own profile domain.

These values overlap and are not additive.

## Present async gap measurement

The source-of-truth build tree was `C:\bwujit`; the similarly named workspace
artifact checkout was stale. A compile-time-only `BOXEDWINE_D3D9WEB_ASYNC_GAP_PROFILE`
probe paired each successful Present wait with entry to the next synchronous tail.
It used no per-command clock and reported zero overwritten pairs.

Eight 120-frame windows, 960 paired frames total:

```text
Present wait total       =   958,680 us = 0.998625 ms/frame
Present -> next tail     = 8,488,770 us = 8.842469 ms/frame
next tail opcode         = CreateTexture, 960/960
event minimum / maximum  = 7.315 / 12.925 ms
overwritten pairs        = 0 / 960
```

Because the host cannot overlap more work than the worker actually waits for the
Present result, a large two-slot async ring was rejected at this gate. Resource
ordering, sticky error propagation, Reset draining, generation changes, and immutable
buffer ownership would add substantial risk for a ceiling of about 1 ms/frame.

## Measurement before state-cache implementation

The clock-free equality profile was compiled with all three new caches disabled.
Four stable PatHouse windows were consistent:

```text
transform calls=3600 same=240
viewport  calls=480  same=480
texture   calls=16080..16140 same=1560
```

This reconfirms the older profile in the current official-JIT/bridge-batch workload.
The selection-screen counts were explicitly excluded.

## Static safety contract

The retained texture+viewport suppression requires:

1. argument validation and StateBlock recording occur before equality checks;
2. CreateDevice begins invalid through zero initialization;
3. Reset and every bridge failure invalidate host-synchronization caches;
4. equality is pointer-exact for texture and byte-exact for the 24-byte
   `D3DVIEWPORT9` (which has no padding);
5. a changed setter AddRefs/copies the candidate but commits the device shadow only
   after successful bridge enqueue;
6. a failed texture bind releases the candidate and preserves the old device-held
   reference;
7. StateBlock Apply may no-op only when the committed logical shadow and valid host
   synchronization shadow agree.

### Remaining D3D9 standard gaps

- **NOT VERIFIED / existing defect:** successful Reset does not yet restore all guest
  and host D3D9 defaults or release/null every bound texture reference. This workload
  measured Reset=0; the retained optimization is accepted only for that observed path.
- **NOT IMPLEMENTED:** `GetTransform` (slot 45) and `GetTexture` (slot 66).
- **NOT VERIFIED:** complete DEFAULT-pool resource/reset loss behavior and final device
  teardown reference release.

These are now explicit compatibility tasks; they are not hidden behind the performance
claim.

## Foreground-controlled A/B

Two attempted texture+viewport intervals were discarded before analysis because their
ending foreground windows were Windows Settings and a hidden `sunshine.exe` window.
For accepted runs, a 250-ms guard sampled 229 times over 60 seconds, always finding
ChatGPT PID 15032 / HWND `0x10A82`; off-target and restore-failure counts were zero.

| arm | intervals | Presents | pooled FPS | mean | median | SD |
|---|---:|---:|---:|---:|---:|---:|
| control A1 | 11 | 1,320 | 32.873 | 32.915 | 33.076 | 1.232 |
| control A2 | 11 | 1,320 | 31.995 | 32.058 | 32.189 | 1.480 |
| texture+viewport B1 | 12 | 1,440 | 35.126 | 35.144 | 35.077 | 0.820 |
| texture+viewport B2 | 12 | 1,440 | 32.466 | 32.554 | 32.832 | 1.773 |
| plus transform | 12 | 1,440 | 32.540 | 32.591 | 32.618 | 1.329 |

Control A1 had correct before/after foreground but not the continuous guard; A2 and
all B arms used the continuous guard. The aggregate is retained conservatively because
the B sessions differ by 8.2% from each other.

## Artifacts

- diagnostic DLL SHA-256:
  `872E032FCDFF144813108D2029C4D8D6BFB071AA4B030EDDF1477EE7074C79DB`
- retained release DLL SHA-256:
  `A3FEB9785F884E8CEBE3F4FD88DCFAE3073AC58C04F6EED6E29F70DC7D2AE5B1`
- retained package:
  `Azrok_D3D9Web_pathouse_statecache_release1.zip`
- retained package SHA-256:
  `3A7F42FD75B4CAD5DFC232E1E308E6A3C5D04CEB57E6E7FC61B4A26A39211E68`

## Next measured gate

The host already batches commands, but the guest still executes one interpreted
`INT 0x9A` for each state setter. The next gate is a versioned guest-created framed
state stream passed through a new BoxedWine ABI, flushed before every non-state command.
The existing `+2` ABI cannot accept such a stream: it treats the entire argument as one
packet and reads its first DWORD as the opcode.
