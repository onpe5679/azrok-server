# 482 Gate 6 default replay and BGM route (2026-07-28)

## Conclusion

- **VERIFIED (dynamic/browser):** The former `boxedwine.nullcall1` replay attempt fails before guest launch because it does not export `_wasm_jit_set_persistence_active`. It is not a valid replay runtime.
- **VERIFIED (dynamic/browser):** The exact replay pair `boxedwine.upstreamjit64fn6inlineabi2` and `/profiles/azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-currentabi1.zip` completes registration: 94 groups, 30,550 blocks, and 28,944 patches.
- **VERIFIED (dynamic/browser):** On that pair, the same fresh launch has `webBgmFallback=playing`, `webBgmFallbackTransport=webaudio`, and `webBgmFallbackTrack=PetHouse.mp3`.
- **VERIFIED (implementation plus dynamic/browser):** The no-query default now selects the guesttexrecycle4 package, `run_azrok_seh.bat`, lean mode, the exact replay runtime/cache pair, and the Web Audio BGM route. A clean no-query launch registered the same replay values and BGM state.
- **NOT VERIFIED:** A 50 FPS direct-Present result in the current embedded browser. This change restores the verified execution baseline only; it is not a new FPS measurement.
- **NOT VERIFIED:** Physical speaker audibility. Browser state proves decode, context routing, and source start but cannot meter the user's actual speaker output.

## Regression boundary

The audio repair made BGM independent of Wine audio, but the page still defaulted
to `jitCacheUrl=off`. A direct switch to `nullcall1` would have made matters
worse: the browser directly reported the missing grouped-replay export. The
only accepted default is therefore the paired upstream runtime and current ABI
cache already pinned by the attached Present harness.

## Evidence

1. `tools/browser_diagnostics/Invoke-AzrokAttachedPresentSample.ps1` requires the upstream JIT stem and the current ABI cache for Control A.
2. A fresh private-browser explicit-pair launch logged `AZROK_JIT_REPLAY_REGISTERED groups=94 entries=30550 patches=28944` and a simultaneous Web Audio BGM state.
3. A fresh no-query launch produced the same registered replay and BGM dataset values.

