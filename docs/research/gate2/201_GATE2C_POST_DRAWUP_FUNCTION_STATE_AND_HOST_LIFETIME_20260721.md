# 201 Gate 2c post-DrawUP function, state, and host lifetime measurement

Date: 2026-07-21

## Scope

One browser tab and one original `Azrok.exe` process were kept in an intact
1024x768 PatHouse scene. The `timeprofile8state` build combines the accepted
DirectDrawUP guest-copy bypass, the guest resource-backing OOM fix, sampled
`cpu->run()` timing, compiled-WASM state equality counters, and host resource
lifetime counters. No native client or second browser session was launched.

## VERIFIED -- intact steady workload

- The retained scene shows the complete carpet, walls, doorway, table/stool,
  character face and shadow, HUD, Korean text, alpha, and corrected culling.
- Accepted 120-Present windows have the steady signature
  `upload_calls=2160`, `upload_bytes=60440880`, `direct_calls=240`, and
  `direct_top_opcode=12:120`.
- Five consecutive representative steady windows measured 20.56, 21.24,
  21.05, 22.05, and 21.03 FPS: mean 21.186 FPS.
- The earlier 18.01 FPS window had 2162 uploads and 242 direct calls and is
  rejected as a transition-contaminated window.
- Browser warnings/errors were empty. The WebSocket remained bidirectionally
  alive for 290.715 seconds after PatHouse bootstrap, with 30 heartbeats in
  each direction and no close, relay error, OOM, SEH, panic, or exception.

## VERIFIED -- host resource retirement closes the second leak

The prior guest backing fix did not retire host resource-table entries or GL
textures: `destroyResource` only marked `destroyRequested`. The runtime now
deletes a texture/buffer after BoxedWine's existing ordered destroy flush,
rejects deletion if the handle is still bound, calls `gl.deleteTexture` for a
texture, and removes the handle from `resources`.

In stable PatHouse windows:

- `create=destroy=deleted=120` per 120 Presents;
- `missing=0`, `bound_blocked=0`;
- `live=139` remains constant across consecutive windows.

The plateau, intact screen, and empty browser error console directly verify
that this recurrent one-texture-per-frame path no longer grows the host table
or leaves GL textures live. This is a longevity fix, not an FPS claim.

## VERIFIED -- current post-DrawUP guest module split

The profiler samples one of every 32 `cpu->run()` calls and measures elapsed
time for the selected calls. Only `dropped=0` ten-second windows are accepted;
the old `active_pct` field remains invalid and is not used.

Representative clean windows place Acknex at about 60--61%, the proxy D3D DLL
at about 7--9%, and Wine/BoxedWine/other modules at about 30--32% of sampled
`cpu->run()` time. The exact split varies when synchronous D3D9WebCall waiting
changes, so it is not converted into an absolute 50 ms frame budget.

Across the profiled windows, the largest proxy block is consistently
`d3d9.dll+0x1130`, linker-mapped to `D3D9WebCall`. The former interpreted
`ByteCopy` hotspot is absent after DirectDrawUP. The top 32 basic blocks cover
only about 38--39% of sampled time.

The profiler key is a 16-byte bucket, so boundary buckets are not treated as
exact EIPs. A `dropped=0` window (`sample_us=863111`) was mapped to the exact
Acknex SHA's Ghidra function ranges and decompiled bodies:

- `FUN_1004a6d0`: 51,252 sampled us, 5.94% of guest sampled time and 9.78% of
  Acknex. It performs CPU vertex interpolation/transform, writes 0x34-byte
  records, and reaches VB Lock/Unlock; 109/396 instructions are x87.
- The verified `FUN_1004a6d0 -> FUN_10049630 -> FUN_10046760` transform chain
  totals 11.78% of guest sampled time and 19.41% of Acknex.
- `FUN_1008df5d`: 35,497 us, 4.11% guest. It groups material/face runs and
  invokes SetVertexDeclaration, SetStreamSource, SetIndices, and
  DrawIndexedPrimitive. This is a command/state candidate, not the first AOT
  target.
- Pure scalar-SSE coordinate/normal kernels `FUN_101041d7` and
  `FUN_101042a3` total about 4.05% guest. Their small side-effect surface makes
  them the safest first address-specialized WASM-SIMD AOT/JIT experiment.
- Mixed/x87 candidates `FUN_1004a6d0`, `FUN_1004ac30`, `FUN_1003ea60`, and
  `FUN_10049fa0` total about 9.43% guest. The highest-leverage trace is the
  `0x4aa80..0x4abdd` hot loop, not wholesale replacement of the Lock/Unlock
  wrapper function.

No single function or x87 family can explain the 22-to-65 FPS gap. The
measurement supports a staged multi-family hot-loop AOT/general block-JIT
strategy after the cheaper safe state/command reduction.

## VERIFIED -- redundant D3D state surface

The compiled BoxedWine bridge compares state packets without changing
behavior. Every steady 120-frame window reports:

```text
state calls=70920 changed=50280 same=20640 same=29.10%
same_payload_bytes=196320 same_batch_bytes=278880 resets=0
```

Per opcode (`calls / changed / same`):

| State | Calls | Changed | Same | Same rate |
|---|---:|---:|---:|---:|
| FVF | 19,080 | 720 | 18,360 | 96.23% |
| Texture | 16,200 | 14,640 | 1,560 | 9.63% |
| Viewport | 480 | 0 | 480 | 100% |
| Transform | 3,600 | 3,360 | 240 | 6.67% |
| StreamSource | 1,320 | 1,320 | 0 | 0% |
| Indices | 1,320 | 1,320 | 0 | 0% |
| VertexDeclaration | 1,560 | 1,560 | 0 | 0% |

RenderState, TextureStageState, and SamplerState show no duplicate packets
because the guest proxy already suppresses them. The largest remaining
measured candidate is therefore SetFVF at 153 identical calls per frame.
This is a call-count result, not a CPU-time or FPS-saving claim.

## VERIFIED -- SetFVF safety gate exposes a proxy standards gap

Gate 1 measured `BeginStateBlock=1`, `EndStateBlock=0`, `Reset=2`,
`SetFVF=119628`, and `SetVertexDeclaration=6776`. Current proxy code sets
`recording_state_block=TRUE` on BeginStateBlock, never clears it, has no
EndStateBlock implementation/vtable slot, and returns D3D_OK. Reset also does
not invalidate an FVF-valid generation, and SetFVF commits its shadow before
SendCommand succeeds.

Consequently, identical FVF calls must not yet be dropped. Standard-preserving
suppression requires all of the following:

- a valid FVF shadow;
- no vertex declaration bound;
- raw FVF equality;
- no active state-block recording;
- commit only after successful command submission;
- invalidate on Reset and successful external SetVertexDeclaration.

The next measurement build must record Begin/End Present numbers,
`SetFVF_while_recording`, and equality calls blocked by declaration versus
recording. If the single Begin is only an unconsumed capability probe, that
must be shown dynamically before a game-path-specific optimization may ignore
it. Otherwise the missing state-block contract must be implemented first.

## Status

- Host/guest recurrent resource leaks: **VERIFIED closed** for the observed
  PatHouse path.
- Post-DrawUP CPU surface: **VERIFIED distributed**, Acknex now dominates the
  sampled guest execution rather than proxy ByteCopy. The largest verified
  transform chain is 11.78% of guest sampled time.
- Redundant FVF surface: **VERIFIED large**, but optimization is **BLOCKED BY
  MEASUREMENT** of state-block timing and semantics.
- 50/65 FPS goal: **NOT VERIFIED**; current measured mean is 21.186 FPS.
