# Gate 6: direct Present correction, BGM route, and current runtime boundary

Date: 2026-07-28 KST

## VERIFIED

- The browser HUD previously shared its `BroadcastChannel` by build only. A
  sibling guest could therefore overwrite the visible FPS value. The channel is
  now scoped by build plus explicit run role (`p`, or `fpsScope`/instance).
  This repairs the HUD observation boundary; it does not change the guest
  frame rate.
- The normal page parameter builder set `lean=1` only in its internal parameter
  object while the renderer read `location.search`. The page now mirrors the
  default into the address before the renderer loads, so normal safe launches
  actually disable diagnostic inventories.
- With one visible `1024x768` PatHouse guest, private HTTPS, original
  `PetHouse.mp3` fallback BGM unpaused and unmuted, and the lean/nullcall route,
  the direct 30-second counter measured **745 Presents / 30.003 s = 24.83
  FPS**.
- Switching the same visible single session to the ABI-matching 94-group / 
  30,550-block JIT replay registered successfully. The original fallback BGM
  remained `PetHouse.mp3`, unpaused and unmuted, with its playback time
  advancing. In the current `Azrok_D3D9Web_pathouse_stateblock1` package, the
  direct 30-second result was **954 Presents / 30.0003 s = 31.7996 FPS**.
- The retained `recompose1` package (guest batch plus exact transient texture
  recycle, while retaining the StateBlock source surface) reached the same
  visible PatHouse scene and the same BGM continuity. Its direct result was
  **1,231 Presents / 30.0005 s = 41.0327 FPS**. Enabling its documented
  pool/shader-colour/DrawUP-ring companion flags produced **1,240 Presents /
  30.0011 s = 41.3318 FPS**. This is a real improvement over the current
  StateBlock package but still not an adoption of a 50-FPS claim.
- Therefore neither current route satisfies the project's 50-FPS gate. The
  header values (including a transient 115 FPS during selection) are not used
  as performance evidence.
- The older `inlinefetch2` accepted-cache file cannot be substituted to recover
  its historical higher samples: its generic-indirect reloc-map base is
  `12,964,392`, while the live current runtime requires `12,968,408`. The
  page rejected the mismatch before guest execution. It was not treated as an
  FPS sample, and the session was restored to the ABI-matching current cache.

## BGM boundary

The browser fallback begins in the real launch click and re-arms at full media
volume through the visible `BGM 다시 재생` control. In the JIT replay run it
selected the original same-origin `PetHouse.mp3`, reported `paused=false`,
`muted=false`, `readyState=4`, `loop=true`, and advanced from 17.32 to 65.27
seconds while the 30-second Present sample ran.

This proves browser decode/playback continuity, not physical speaker audibility:
the available in-app browser inspection surface does not expose an audio-output
meter or hardware endpoint volume. The native Wine GStreamer route remains
known-broken; the original MP3 fallback is the current containment route.

## NOT VERIFIED

- Physical speaker/headphone audibility from the user-facing in-app browser.
- A 3x30-second direct-Present all-at-least-50-FPS result on the StateBlock
  package that is required for natural Plaza entry.
