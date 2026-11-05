# Gate 2C: browser audio, GStreamer MP3, and thread FPU inheritance

Date: 2026-07-21

## Result

- **VERIFIED (user/runtime):** `boxedwine.audioprobe1` restored audible browser sound effects. The user directly confirmed SFX playback; BGM remained silent with the Korean3 root.
- **VERIFIED (static/runtime):** Wine's MP3 BGM path is Quartz/DirectShow through `winegstreamer`, not the preserved CD-audio MCI probe. `PetHouse.mp3` opens, but the old root could not load `winegstreamer.so` because `libpcre2-8.so.0` was absent.
- **VERIFIED (package):** the minimal MP3 closure is `libpcre2-8.so.0.7.1`, `libgstaudioparsers.so`, and `libgstmpg123.so`. Both GStreamer factories load with an isolated registry.
- **VERIFIED (dynamic):** parser-only reaches EOS. Adding `mpg123audiodec` formerly terminated native BoxedWine with Windows status `0xC000008F` (`STATUS_FLOAT_INEXACT_RESULT`). Standalone `mpg123` decodes the same file to a 15,063,596-byte WAV with RC 0.
- **VERIFIED (dynamic):** forcing S16LE and F32LE both failed after the first `MPG123_NEED_MORE`; therefore the file, parser, decoder selection, and output format are not the discriminating cause.
- **VERIFIED (static):** the pthread `CLONE_THREAD` branch created a fresh CPU but did not call `KThread::clone()`. `FPU::reset()` leaves `cw=0`, while `FINIT()` uses the normal masked value `0x037f`. GStreamer's streaming thread therefore began with every x87 exception unmasked.
- **VERIFIED (implementation/runtime):** the thread branch now inherits the parent CPU state before applying child stack/EIP/TLS. `CPU::clone()` also copies XMM registers and MXCSR. A clean native Release build then produced decoded S16LE 44.1 kHz stereo caps and completed PREROLL -> PLAYING -> EOS with guest RC 0; `0xC000008F` did not recur.
- **VERIFIED (build):** the same source rebuilt as the 1 GiB pthread WASM runtime `boxedwine.audiofpu1`; JavaScript syntax validation passed.
- **NOT VERIFIED:** audible browser BGM through the final Wine/Quartz graph still requires the one-tab visible game test.

## Minimal root additions

`TinyCore15Wine11.0-wsaeventfix5-korean4-bgm1.zip` adds:

- `usr/local/lib/libpcre2-8.so.0.7.1`
- `usr/local/lib/libpcre2-8.so.0.link` -> `libpcre2-8.so.0.7.1`
- `usr/local/lib/gstreamer-1.0/libgstaudioparsers.so`
- `usr/local/lib/gstreamer-1.0/libgstmpg123.so`

The browser launcher supplies `LD_LIBRARY_PATH=/usr/local/lib` so Wine's Unix-side GStreamer module can resolve PCRE2 without replacing the existing root or regenerating its loader cache.

## Evidence

- `artifacts/boxedwine/20260719_gate2b_native/wine11_gstreamer_pethouse_parser_only4_20260721_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/wine11_gstreamer_pethouse_parser_decoder1_20260721_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/wine11_mpg123_pethouse_standalone1_20260721_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/wine11_gstreamer_pethouse_mpg123_s16le1_20260721_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/wine11_gstreamer_pethouse_mpg123_f32le1_20260721_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/wine11_gstreamer_pethouse_clonexmm1_20260721_stdout.log`
- `artifacts/boxedwine/20260719_gate2b_native/dumps/gstreamer_mpg123_20260721/`

## Artifact hashes

- Korean4 BGM root SHA-256: `36167BB33777C6FE60F98B9C00CB153FE0D4A3BCE0AF855762F009B98FBBEE83`
- `boxedwine.audiofpu1.js` SHA-256: `741DD115F9AC4D4A8EADFF3B9EEA2BA5D89D63B836C8167A5B5A88050276437A`
- `boxedwine.audiofpu1.wasm` SHA-256: `955D56AA6AC35AE727878906229F4721701604DDF5D49EE17826DE263A29A16A`

