# Gate 6 — frame-wide async ring, wait identity, and read-hot ZIP cache

Date: 2026-07-22

## Result

- **VERIFIED dynamic/browser:** the bounded frame-wide ordered async ring is the
  largest accepted renderer-side change in this phase.  PatHouse A-B-A measured
  36.546 / 30.392 / 36.021 FPS (async / sync / async), a reproducible
  +18.5--20.3%.  Sequence gaps, reorder events, and errors were all zero.
- **VERIFIED static + dynamic:** the persistent asset stall was not a D3D9
  texture upload.  `Data/Texture/HP_PZ_R_base_0.wis` was reopened and decoded
  by the guest animation path.  One logical reload is six `ReadFile` calls
  (five 4-byte header reads plus one 130,560-byte body read).
- **VERIFIED implementation/browser:** a path-independent compressed-ZIP cache
  now promotes only entries that demonstrate real repeat traffic in distinct
  read-active opens.  It fixed the failed second-open policy, retained the
  reference PatHouse render, and admitted the active face variants at only
  1.76 MiB retained cache use.
- **VERIFIED release measurement:** visible PatHouse A-B-A measured read-hot
  43.011 / face-only 38.459 / read-hot 40.416 FPS.  The two adjacent relative
  deltas are +11.84% and +5.09%; their median is +8.46%.  Foreground changes
  are retained as workload covariates under the adaptive interleave rule.  The
  50-FPS gate is **not yet met**.
- **VERIFIED adaptive recheck with covariates:** a fresh face-only A1 / read-hot
  B / face-only A2 run measured 36.771 / 39.747 / 37.098 FPS.  A1-to-A2 drift
  was only +0.89%; the two adjacent B effects were +8.09% and +7.14%, median
  +7.62%.  The page stayed visible throughout.  Foreground applications were
  recorded rather than used as a rejection rule, and renderer CPU/Present was
  61.04 / 56.57 / 58.01 ms.  The adaptive rule therefore stopped at A-B-A.

## 1. Frame-wide ordered async ring

### Implementation

- Three shared slots, 4 MiB each.
- `Present` completion is returned asynchronously.
- Every later synchronous tail drains prior work in FIFO order.
- The implementation is compile-time and Azrok-path bounded.

### Dynamic proof

| Run | FPS | FIFO result |
|---|---:|---|
| async A | 36.546 | gaps=0, reorders=0, errors=0 |
| sync B | 30.392 | control |
| async A2 | 36.021 | gaps=0, reorders=0, errors=0 |

**PARTIAL:** generic Reset/context-loss recovery and arbitrary multithreaded D3D
producer safety are not yet production-complete.  The measured Azrok path is
accepted; this is not yet advertised as a universal D3D9 runtime feature.

## 2. CPU and wait identity

**VERIFIED dynamic:** one 22.011-second process sample separated approximately:

- game worker CPU: 20.05 ms/frame;
- renderer-main CPU: 11.72 ms/frame;
- wall: 25.06 ms/frame;
- worker non-running residual: about 5 ms/frame.

The worker and renderer overlap, so their CPU totals must not be added as a
serial frame budget.

The first 720-frame syscall window measured 4.1986 ms/frame of presenting-thread
read wait.  The lifetime-safe identity profiler replaced a raw `KObject*` with
`shared_ptr<KObject>` and then identified the stable sources:

- fd 4: `anon_inode:[pipe]` (Wine server/reply traffic);
- a rotating file fd: `Data/Texture/HP_PZ_R_base_0.wis`.

Three stable 120-Present windows before caching measured total read wait
492/470/516 ms, of which WIS was 182/172/169 ms and the pipe was
310/298/347 ms.  Futex time was only 2/3/1 ms.

## 3. Why the face WIS repeats

**VERIFIED static:** the face-animation update builds
`%s_base_%d.wis` on every animation tick and constructs/destructs a local
resource manager.  The manager's cache therefore does not survive the call,
and the current index is reloaded even when it did not change.

**VERIFIED native dynamic:** native Wine file tracing shows the same repeated
loads.  This is an original game/Acknex resource-lifetime inefficiency, not a
D3D9 proxy file-I/O bug.  The proxy contains no WIS file read path.

All 113 `HP_*.wis` entries are face-animation variants (base/joy/sad/sick),
14,755,540 bytes total.  Ordinary room textures were observed loading once.

## 4. Rejected approaches

### ZIP STORE conversion

The original app entry is deflated (130,580 raw / 10,086 compressed bytes).
Replacing only `HP_PZ_R_base_0.wis` with a single STORE entry preserved pixels
but increased file wait to about 4.38 ms/frame and total read wait to about
7.08 ms/frame.  Browser direct `lseek/read` into the large app ZIP was worse
than the in-memory minizip path.  The shipped app ZIP was restored unchanged.

### Cache on second open

The first generalized cache admitted every compressed entry on its second
`FsZipNode::open`, even if the open did not read a byte.  It was correctness-safe
but performance-invalid:

- release stem48: 38.036 FPS versus 37.737 control (+0.79%, noise band);
- profile stem49: the active WIS still consumed 103--255 ms per 120 Presents in
  later windows and 309--349 ms in earlier windows;
- root Wine modules, fonts/config, and app startup assets could reserve the
  global 32 MiB budget before the persistent face workload.

This policy is rejected and superseded by the read-hot policy below.

## 5. Adopted read-hot compressed-entry cache

### Admission contract

For a deflated ZIP entry no larger than 1 MiB:

1. Each `FsZipOpenNode` accumulates only positive bytes actually returned.
2. On idempotent close/destruction it reports once to its owning `FsZipNode`.
3. The first read-active open establishes the baseline.
4. Later read-active opens add repeat bytes, saturating at
   `max(64 KiB, entry length)`.
5. Only a following open may promote after at least two read-active opens and
   the repeat-byte threshold.
6. Published bytes are immutable and node-owned; global retained budget is
   32 MiB.  STORE/direct entries remain on the original path.

The policy is path- and extension-independent.  It therefore applies to other
textures or assets only after their own repeated reads pay back at least the
entry-sized allocation; one-shot room textures are not eagerly cached.

### Static safety findings

**VERIFIED static:** publication is after complete inflate; open nodes retain
the node/cache by `shared_ptr`; cached reads preserve private file positions;
negative positions return `EINVAL`; COW/local overlays and STORE/direct paths
retain their existing behavior.

Two blockers were found and fixed before the accepted build:

- reporting from under `FsZip::readMutex` would invert archive/node lock order;
  byte accounting is now open-local and reporting occurs at close, outside the
  archive lock;
- normal `KFile` destruction deletes the open node without explicitly calling
  `close()`.  `FsZipOpenNode::~FsZipOpenNode()` now calls the idempotent close,
  matching the existing file-node ownership pattern.

Allocation now occurs before budget reservation and the destructor releases
the retained vector before returning its budget.  Static re-audit found no
normal-package deadlock, UAF, double return, or partial-publication blocker.

**PARTIAL:** malformed ZIP signed-return behavior and rare internal
close/reopen statistic undercount are inherited/nonblocking for the fixed valid
Azrok packages.

### Dynamic admission and wait result

Profile stem50 directly logged:

```text
AZROK_ZIP_CACHE_ADMIT .../HP_PZ_R_base_0.wis bytes=130580 used=1496918 read_opens=2 repeat_bytes=130580
AZROK_ZIP_CACHE_ADMIT .../HP_PZ_R_base_1.wis bytes=130580 used=1627498 read_opens=2 repeat_bytes=130580
AZROK_ZIP_CACHE_ADMIT .../HP_PZ_R_base_2.wis bytes=130580 used=1758078 read_opens=2 repeat_bytes=130580
```

There were zero budget denials in the retained log window.  Six later windows
reduced WIS blocking time from an old-policy mean 167.3 ms/120 frames to
38.7 ms/120 frames (-76.9%).  Total blocking read time moved from 463.0 to
329.2 ms/120 frames (-28.9%).  Cached guest `ReadFile` syscalls still appear in
the profiler; the reduction is removal of repeated archive inflate/cursor work,
not removal of the Win32 calls themselves.

## 6. Release FPS and visual gate

All retained scenes were one-tab, 1024x768, `document.visibilityState=visible`,
with the user foreground left untouched.  A foreground-app transition does not
invalidate a visible window; it is recorded as a workload covariate.  Only a
hidden/fully throttled renderer window is discarded.

| Build / condition | 1,320-frame FPS | Status |
|---|---:|---|
| no-cache control, AfterFX stable | 37.737 | retained historical control |
| read-hot A1, foreground AfterFX | 43.011 | A-B delta +11.84% |
| face-only B, foreground AfterFX→WindowsTerminal | 38.459 | retained B |
| read-hot A2, foreground AfterFX | 40.416 | A-B delta +5.09% |

Both adjacent A-B differences have the same sign and exceed the ±3% noise band,
so the adaptive rule stops at A-B-A instead of paying for A-B-A-B.  The median
relative effect is +8.46%.  The A2 result is also +7.10% versus the retained
stable no-cache control.  Renderer CPU/frame was not captured for these already
completed windows and is required as an additional covariate in subsequent
interleaved measurements.

### Adaptive A-B-A recheck with foreground and renderer CPU covariates

The measurement policy was tightened for normal user work on the same machine:

- default to A-B-A because each runtime swap plus PatHouse entry costs roughly
  two minutes;
- retain foreground changes and record the process/window title as a covariate;
- retain renderer CPU/Present as a second covariate;
- discard only `document.hidden`, non-`visible` visibility, or confirmed full
  renderer throttling/occlusion;
- extend to A-B-A-B only if the two adjacent effects conflict or overlap the
  approximately +/-3% noise band.

The exact comparison used preserved artifacts, not a rebuild of the legacy
target name: face-only A was `boxedwine.upstreamjit47facewiscacherelease1` and
general read-hot B was `boxedwine.upstreamjit51readhotrelease1`.

| Order | Runtime | FPS | Renderer CPU ms/Present | Foreground samples | Visibility |
|---|---|---:|---:|---|---|
| A1 | face-only stem47 | 36.771 | 61.04 | Comet 16; After Effects 14 | visible |
| B | general read-hot stem51 | 39.747 | 56.57 | OneCommander 30 | visible |
| A2 | face-only stem47 | 37.098 | 58.01 | Windows Terminal 29; Task Manager 1 | visible |

A1-to-A2 drift was +0.89%.  B improved the two adjacent comparisons by +8.09%
and +7.14%; their median is +7.62%.  Both exceed the noise band with the same
sign, so A-B-A-B was not warranted.  CPU/Present changed by -7.32% and -2.47%
against the adjacent A samples (median -4.90%), directionally consistent with
the FPS result but retained as a covariate rather than the primary decision
metric.  Fresh screenshots in all three runs preserved the PatHouse carpet,
walls, furniture, character face/body, Korean text, alpha, and culling.

**VERIFIED browser visual:** carpet, walls, furniture, character face/body,
Korean UI, and alpha/culling remained reference-correct.  Async ring sequence
gaps/reorders/errors remained zero.  The known stale lower character-selection
text is explicitly outside this gate per user instruction.

## 7. Artifacts and next bottleneck

- profile: `boxedwine.upstreamjit50readhotprofile1`
- accepted release: `boxedwine.upstreamjit51readhotrelease1`
- release JS SHA256:
  `99A873D527A41763F141B0829FE1CB6BDDC029BEFD0D9E218B234F8E825CDDDC`
- release WASM SHA256:
  `66B3D651B7A659C8AE897DD7353C2C25A3EEAEE1C6850C84E35E47865F214195`

The accepted release remains below the 50-FPS goal.  After removing most WIS
archive work, the stable remaining exact wait candidate is the Wine fd-4 reply
pipe (roughly 2.5 ms/frame in retained identity windows), followed by the
remaining game-worker CPU.  The next gate should attribute the fd-4 Wine-server
requests by caller/request kind before attempting another scheduling or JIT
variant.

## 8. Wine server reply attribution and OS-thread split

**VERIFIED static:** exact Wine 11 uses a 306-entry request enum.  The client
sends the fixed 64-byte request union through its per-thread request fd and
then reads a fixed 64-byte reply.  The observed syscall EIP `0x1054d1c2` maps
to the exact guest libc `read+0x57` syscall instruction; fd 4/len 64 is the
Wine reply path, not an inferred Acknex caller.

The profile reuses the existing `ksyscall()` entry/exit clock.  It validates
the guest request header, complete `writev` descriptor array, Unix-socket fd,
request id/range/variable length, and consumes the thread-local attribution on
the first successful fixed reply.  Static re-audit found no remaining P0 in
the Azrok diagnostic path.  The run directly confirmed request fd 3.

Four complete, visible PatHouse windows (480 Presents) attributed all 921 ms
of fd-4 blocking time:

| Wine request | Blocking us | Share of fd-4 | ms/frame |
|---|---:|---:|---:|
| `create_file` (44) | 434,000 | 47.12% | 0.904 |
| `select` (29) | 124,000 | 13.46% | 0.258 |
| `set_queue_mask` (116) | 95,000 | 10.31% | 0.198 |
| `close_handle` (21) | 89,000 | 9.66% | 0.185 |
| `get_handle_fd` (48) | 88,000 | 9.55% | 0.183 |
| `event_op` (31) | 71,000 | 7.71% | 0.148 |
| `get_directory_cache_entry` (49) | 20,000 | 2.17% | 0.042 |

Total fd-4 wait is therefore 1.919 ms/frame, not the missing roughly 30 ms.
Server-call batching cannot by itself reach 50 FPS and is not the next gate.

**VERIFIED dynamic OS accounting:** the active game page renderer was PID
39644.  Native thread-name queries over a five-second sample showed one
`DedicatedWorker thread` at 4,296.9 CPU ms, `CrRendererMain` at 2,359.4 ms,
and the next three dedicated workers at 906.2, 796.9, and 625.0 ms.  This
identifies the primary guest/WASM worker as the largest CPU consumer while the
renderer main and other guest workers run concurrently.  A system-wide WPR
CPU-stack trace was attempted but Windows denied the required profiling
policy; no trace session remained active.  The next low-overhead gate is a
JIT-executed-block versus interpreter-block count on the primary worker, not
another wall-clock sampler.
