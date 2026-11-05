# 189 Gate 2c Emscripten native-socket helper boundary

Date: 2026-07-20

## Scope

This is one browser-startup repair and one bounded PatHouse rendering gate. It
does not expand gameplay or content QA.

## Source-mapped reproduction — VERIFIED

The 1 GiB, assertion-enabled browser build maps the recurrent browser worker
exception to these symbols:

```text
wasm-function[8812] -> std::__2::__shared_weak_count::__release_weak()
wasm-function[4165] -> kpanic_fmt<int&>(char const*, int&)
wasm-function[4168] -> startNativeSocketsThread()
wasm-function[7466] -> SDL_FreeErrBuf
wasm-function[7442] -> SDL_SYS_CreateThread
```

`startNativeSocketsThread()` calls `Platform::nativeSocketPair()` in
`source/kernel/knativesocket.cpp`. The Emscripten build resolves that to the
unsupported `__syscall_socketpair` path reported immediately before the
exception. This establishes the causal chain that document 188 deliberately
left unproven.

## Repair — IMPLEMENTED, NOT YET DYNAMICALLY VERIFIED

For `__EMSCRIPTEN__`, the multi-threaded helper thread, its AF_LOCAL
`socketpair`, and pipe wake sends are suppressed. The browser retains its
already-present `checkWaitingNativeSockets(0)` calls from
`source/sdl/emscripten/mainloop.cpp`, which poll SOCKFS directly. Native
multi-threaded builds retain the original select-helper thread unchanged.

The same build retains the bounded 640x480 canvas to 1024x768 guest mouse
coordinate transform from 187. It is still awaiting one live click check.

## 3D face orientation — VERIFIED CODE CHANGE, PENDING VISUAL CHECK

The D3D9Web host maps `D3DRS_CULLMODE` as follows with WebGL's CCW
front-face convention:

| D3D state | meaning | WebGL face discarded |
|---|---|---|
| `D3DCULL_NONE` (1) | discard nothing | culling disabled |
| `D3DCULL_CW` (2) | discard clockwise faces | `BACK` |
| `D3DCULL_CCW` (3) | discard counter-clockwise faces | `FRONT` |

The prior host map used the opposite faces. Both the served runtime and its
canonical `tools/web_backend` source now carry the corrected map. Syntax and
the existing real-driver fixed-function round-trip suite pass; a visible
PatHouse scene remains required to confirm the actual meshes.

## Next direct measurement

Run only the repaired browser asset to the existing PatHouse bootstrap. The
pass conditions are: no `__syscall_socketpair` warning/unaligned exception,
visible 3D room, correct front/back face appearance, and one Create-button
click whose game cursor lands at the physical pointer position.
