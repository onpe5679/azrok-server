# 503 Gate 6 in-app bridge workload (2026-07-28)

## VERIFIED

- The existing private `boxedwine.upstreamjit21bridgeprofile` runtime reached
  a visible 1024x768 PatHouse scene with the same original BGM fallback
  unpaused, unmuted, ready state 4 and advancing.
- Its settled 120-Present bridge windows contained approximately 90,600 bridge
  calls: 69,120 generic calls, 2,400 direct uploads and 19,080 DrawUP calls.
  That is about 755 bridge calls, 576 generic commands, 20 uploads and 159
  DrawUP calls per Present. Main-thread round trips remained approximately one
  per Present, not hundreds per Present.
- The profile runtime is diagnostic-only and its visible HUD fell to 27.6 FPS;
  this is not a release performance result. It nevertheless establishes the
  current command-workload shape.
- A fresh current-release test of the separately packaged guest-batch app
  rendered normal PatHouse and kept BGM active, but its visible HUD settled at
  31.5 FPS. It is not a 50-FPS candidate and is not selected.

## Conclusion

The active guesttex-recycle route remains preferable to guest-batch. The
remaining practical bottleneck is high guest command construction/bridge
workload, especially the repeated generic and DrawUP path; neither BGM nor a
single per-Present synchronous drain explains the current narrow-view result.

## NOT VERIFIED

- The profile runtime has no matching replay/cache identity and adds its own
  instrumentation cost, so its timing cannot quantify a release speedup.
- No current narrow in-app route has yet produced three valid 30-second
  50-FPS windows.
