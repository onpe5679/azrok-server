# 603 — Current PatHouse visual witness and command-shape fingerprint rejection

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED visual/browser:** the canonical command-shape tuple
  `1:120:21480:14158560:2109626789:0:0` was present while the visible game
  canvas still showed the mouse-camera transition/loading screen, not
  PatHouse.
- **REJECTED:** the four fresh Default/NoLiftoff rows 69.1551 / 72.2915 /
  70.2774 / 69.9113 FPS are structurally valid direct-Present observations,
  but they are not PatHouse measurements and carry no V8 mode conclusion.
- **VERIFIED visual/browser:** keeping the final browser alive for another
  30 seconds reached the actual PatHouse room with carpet, furniture, player
  Azron, HUD, Korean text, and the three empty character-slot labels visible.
- **VERIFIED dynamic:** that visually accepted PatHouse then measured
  877 direct Presents / 30.007850 s = **29.2257 FPS** at CSS 1024x768 and
  backing 640x480.
- **VERIFIED diagnostic boundary:** a page-realm CDP CPU profile in the same
  accepted PatHouse collected 18,692 samples. `packFFVertexData` held 819
  samples (4.3816% of all samples), `packFFPixelStages` 361 (1.9313%),
  `packFFPixelState` 204 (1.0914%), and GC 207 (1.1074%). This profile covers
  the page/main renderer realm, not the primary guest CPU pthread.
- **NOT VERIFIED:** current PatHouse Default vs NoLiftoff, guest-worker hot
  Wasm regions, and a deployable performance improvement.

## Why the former fingerprint gate failed

Documents 439 and 450 already warned that the tuple hashes command id,
command byte length, and order only. It does not hash payload and is not a
semantic room/camera/map witness. The new current fastboot4 run directly
demonstrates the consequence: the transition screen and later room can share
the admitted command shape.

The first diagnostic run used a fresh Edge profile, current immutable app,
root, runtime and replay:

```text
app     Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts2_startersplash1_fastboot4
root    TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1-acp949-xim25koreanlocale2
runtime boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2
cache   azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-currentabi1.zip
replay  94 groups / 30,550 entries / 28,944 patches
```

The browser was visible on DISPLAY9 at requested window placement
`7760,100 1500x1200`. The command-shape observer detached exactly after the
canonical tuple. The immediate post-measure screenshot still showed the
transition screen. Thirty seconds later the same tab showed PatHouse and the
HUD fell from the transition-screen 68–74 FPS range to about 26–29 FPS.

Therefore a timer delay plus the canonical tuple is insufficient. Future
performance rows require a pixel/visual PatHouse witness captured immediately
before or after the timing interval. Until an automated semantic witness is
proved, visual review is mandatory.

## Rejected Default/NoLiftoff rows

| Order | Role | FPS | Direct Presents / wall | Decision |
|---:|---|---:|---:|---|
| 1 | Default A1 | 69.1551 | 2075 / 30.005019 s | rejected, transition screen |
| 2 | NoLiftoff B1 | 72.2915 | 2169 / 30.003531 s | rejected, transition screen |
| 3 | Default A2 | 70.2774 | 2109 / 30.009664 s | rejected, transition screen |
| 4 | NoLiftoff B2 | 69.9113 | 2098 / 30.009438 s | rejected, transition screen |

The raw rows are preserved. The canonical rejection table adds
`Accepted=false` and a fixed reason; nothing was deleted.

## Actual PatHouse witness

The final maintained tab was captured twice:

1. immediately after fingerprint admission — transition/loading screen;
2. 30 seconds later — actual PatHouse.

Only the second state was admitted for the attached direct-Present sample:

```text
visibility     visible
canvas CSS     1024x768
canvas backing 640x480
direct         877 / 30007.850 ms
FPS            29.2257
```

This is one current control observation, not a stable 50-FPS or V8-tiering
claim. Fresh PatHouse controls still need a visual witness per leg and the
normal A-B-A(B) drift rule.

## CDP profile boundary

`Invoke-AzrokWasmCpuProfile.ps1` profiles the page target. It successfully
identified renderer/host costs such as state packing, GL `bufferData`,
vertex-color swizzling, and GC. It also saw the Emscripten runtime main-realm
Wasm function, but it did not profile the long-running guest CPU pthread.

The browser exposed 44 worker CDP targets. A first all-worker simultaneous
profile attempt did not finish within 90 seconds because active pthreads do
not reliably return to their JS event loop. The attempt was interrupted;
page direct Presents continued and the visual PatHouse remained intact.
This is diagnostic failure evidence, not a worker profile.

## Artifacts

- `artifacts/performance/regional_visual_witness_early_20260830.png`
- `artifacts/performance/regional_visual_witness_final_20260830.png`
- `artifacts/performance/regional_visual_witness_plus30s_20260830.png`
- `artifacts/performance/regional_aot_actual_pathouse_attached_20260830.csv`
- `artifacts/performance/regional_aot_actual_pathouse_cpu_profile_20260830.json`
- `artifacts/performance/regional_aot_actual_pathouse_cpu_profile_20260830.csv`
- `artifacts/performance/regional_aot_liftoff_abab_canonical_20260830.csv`
- `artifacts/performance/regional_aot_liftoff_abab_canonical_20260830.rejections.csv`

## Next gate

1. Add a direct pixel/visual PatHouse witness to the fresh-process sampler;
   command shape may remain a secondary workload covariate only.
2. Re-run fresh Default controls until actual PatHouse direct-Present rows are
   stable.
3. Measure guest CPU bookkeeping with a runtime-side clock-free census or a
   bounded worker-specific profiler; do not call the page profile guest CPU.
4. Only then reopen Default/NoLiftoff or choose a fused regional AOT target.

