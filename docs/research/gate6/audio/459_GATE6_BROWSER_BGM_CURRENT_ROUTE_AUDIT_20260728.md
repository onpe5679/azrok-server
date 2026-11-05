# 459 Gate 6 current browser BGM route and artifact audit (2026-07-28)

## Result

- **VERIFIED (current page static):** `tools/boxedwine_local/index_d3d9web_pathouse.html` defaults the guest root to `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1`, exports `LD_LIBRARY_PATH=/usr/local/lib`, enables sound unless `nosound` is explicit, and exposes the audio-trace collector.
- **VERIFIED (current root content):** the selected root is SHA-256 `329BEA48852C33C7937B9848EE37500060C31ADFA751F75CA256A8532EED4228` and contains the prior BGM repair artifacts: `winegstreamer.dll.so` SHA-256 `8793B5D7CDD503E05AF429950E8AD99DCFE898006F2D1B39DD6B8B770E3F9E20`, `dsound.dll.so` SHA-256 `5D427860505CEFD5C089D45BA1164367899A4EB2AEE24C5C3B7DC6B37A6E7F62`, PCRE2, `libgstaudioparsers.so`, and `libgstmpg123.so`.
- **VERIFIED (current source):** the threaded BoxedWine source inherits the pthread floating-point/XMM/MXCSR state with `copyFloatingPointStateFrom()`. The preserved Wine sources contain the GStreamer seek-flush callback and the full-80-ms DirectSound producer watermark (`aclen_frames = acbuf_frames`).
- **VERIFIED (live local serving):** port 8765 served the selected root as HTTP 200 with the expected 167,172,869-byte size.
- **VERIFIED (current launch routing):** `localhost.log` records `GET /index_d3d9web_pathouse.html?audioGesture=1` followed by a 404 for missing `assets_d3d9web/boxedwine.js`; that default route cannot start. The retry with the accepted runtime stem loaded JS/WASM, then requested `apps/Azrok_D3D9Web_pathouse_lockprobe-jit-modules.zip` and received 404. `boxedwine-shell.js` treats that JIT-cache sidecar as optional and continues via its callback, so this 404 alone does not prove that the guest stopped. No subsequent root/app transfer was logged, but IndexedDB persistence can satisfy them without a transfer; therefore neither guest execution nor BGM is established from this log alone.
- **NOT VERIFIED:** audible BGM in the currently intended 50-FPS runtime. A visible, user-gesture-started run with the fully specified accepted app/runtime/root remains required, followed by `audio_graph.log` and audible/capture evidence.

## Exact candidate launch contract

Use the already-proven audio root with the accepted runtime and an existing app bundle, rather than the page defaults:

```text
index_d3d9web_pathouse.html?pathouseav=1&audioGesture=1&audioFreq=44100
&root=TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1
&app=Azrok_D3D9Web_pathouse_guestbatch1
&p=run_azrok_seh.bat
&runtimeStem=boxedwine.upstreamjit64fn6inlineabi2
&jitCacheUrl=/profiles/azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-currentabi1.zip
&lean=1
```

The final audio acceptance must collect nonzero BGM PCM/graph evidence after the user gesture and verify a loop or a transition; loading a runtime or seeing a sound-effect event is insufficient.

## Evidence

- `tools/boxedwine_local/index_d3d9web_pathouse.html` lines 91, 199, 234
- `tools/boxedwine_local/localhost.log` lines 11359-11380
- `tools/boxedwine_local/fs/TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1.zip`
- `tools/boxedwine_local/bwujit_threaded_abi/source/kernel/kprocess.cpp` lines 1687-1710
- `tools/boxedwine_local/bwujit_threaded_abi/source/emulation/cpu/common/cpu.cpp` lines 1196-1218
- `artifacts/wine11_source/wine-11.0/dlls/winegstreamer/quartz_transform.c` lines 416-438
- `artifacts/wine11_source/wine-11.0/dlls/dsound/primary.c` lines 322-340
