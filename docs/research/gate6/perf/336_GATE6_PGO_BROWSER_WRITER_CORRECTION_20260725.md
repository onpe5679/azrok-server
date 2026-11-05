# Gate 6 PGO browser writer correction (2026-07-25)

Status: **VERIFIED static / browser participant map corrected**

## Correction to 334

Document 334 correctly required an all-writer quorum, but overextended a
native-host fact into the browser target: `knativesocket.cpp:455-490` creates a
`KNativeThread` only outside `__EMSCRIPTEN__`.  The accepted browser path uses
`BOXEDWINE_EMSCRIPTEN_SOCKETS`; `checkWaitingNativeSockets()` is called by the
Emscripten MainLoop (`source/sdl/emscripten/mainloop.cpp:54-84,130-160`), with
the corresponding socket branch at `source/kernel/knativesocket.cpp:332-390`.

Therefore browser socket work belongs to the **MainLoop** participant and must
not be registered as an additional NativeSocket writer.  Counting both would
freeze an impossible extra quorum member and fail-close every capture.

## Corrected browser inventory

- **VERIFIED:** guest CPU pthreads; register before `platformStartThread`, make
  active around `cpu->run()`, poll only after its return, and unregister before
  CPU/thread cleanup.
- **VERIFIED:** the PROXY_TO_PTHREAD application/MainLoop worker; it requires a
  separate lifecycle and callback-boundary safe point.
- **NOT VERIFIED:** whether SDL/Emscripten audio has any instrumented-Wasm
  callback writer.  `SDL_QueueAudio` plus browser-main audio proxy glue is not
  sufficient to exclude it.
- **INFERRED pending build-path proof:** Player/background thread paths are not
  yet a browser writer admission or exclusion proof.  UI is compiled out by
  the accepted Emscripten `BOXEDWINE_DISABLE_UI` flag.

## Safe next slice

Do not expose PGO buffers or wire MainLoop yet.  First connect only the private
CPU lifecycle fixture: synchronous registration before thread start, failure
unregistration on start error, exception-safe active clear around `cpu->run()`,
post-return poll, and final unregister before cleanup.  A two-CPU fixture must
prove no capture before both post-run polls and fail release on forced
termination/start failure.  MainLoop and audio identity remain separate gates.
