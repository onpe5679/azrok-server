# 147 — D3D9 → WebGL2 A 방식 마샬링 설계 (2026-07-19)

## Decision

**PROPOSED:** guest replacement `d3d9.dll` implements the measured D3D9 COM
surface and serializes a versioned renderer command stream to a host bridge.
The DLL plus command ABI are portable; the bridge adapter is runtime-specific.
This avoids chaining through WineD3D.

## Browser-path evidence

**VERIFIED local source:** BoxedWine's Emscripten makefile supplies neither
`BOXEDWINE_OPENGL_SDL` nor `BOXEDWINE_VULKAN`. `KNativeSystem::getOpenGL()`
and `getVulkan()` therefore have no host 3D implementation in that build.
Under `__EMSCRIPTEN__`, `knativescreenSDL.cpp` selects
`SDL_RENDERER_SOFTWARE`. A source/project search finds no `WebGPU` token.
The current browser build consequently has no usable WineD3D/DXVK 3D target.

## Measured scope

**VERIFIED Gate 1:** 56 called COM methods / 1,891,345 calls; including the
sole DLL export `Direct3DCreate9`, the direct lower bound is 57 entrypoints.
The fixed-function render path averages 55 draws per Present (109,176
`DrawPrimitiveUP`, 6,776 indexed draws, 2,095 Presents). Real shader setters,
render-target switching, extra swap chains, gamma ramp, and `StretchRect` are
unobserved. `Reset` occurs twice and palette updates occur six times.

## Agreed ABI boundary; transport adapter still to be measured

```text
guest Azrok → replacement d3d9.dll → versioned command ABI
       → BoxedWine adapter → browser JS/WebGL2 backend
```

The portable contract stops at a compact, guest-owned command buffer. Guest
pointers never cross the boundary: commands contain scalar fields, copied
bytes, and 32-bit resource handles with generations. The runtime adapter owns
the transfer to JavaScript/WebGL2. Reusing the same contract in a future
CheerpX adapter is a portability goal, **NOT VERIFIED**: no CheerpX
guest-to-JavaScript transport has been exercised locally.

**VERIFIED source and native dynamic test:** BoxedWine already decodes the
sibling guest traps `CD 99` (OpenGL) and `CD 9A` (Vulkan). The Emscripten build
does not define Vulkan, so `INT 0x9A` was a no-op. A dedicated
`BOXEDWINE_D3D9WEB` branch now reuses that existing decoder slot without adding
an instruction enum or touching the JIT generators. Document 158 proves a
32-bit PE guest can push index/arguments, execute `CD 9A`, reach the native
BoxedWine callback, and receive `EAX=0x1234` with exact values. `INT 0x9A` is
therefore the first transport path; `INT 0x99` and `DeviceIoControl` are
fallbacks.

Document 159 closes the remaining browser boundary: host C++ delivered the
exact values to JavaScript and the JavaScript result returned synchronously to
guest EAX through the already-proven PE trap. The guest ABI does not require
one submit per frame or a particular transport.

Commands use `{magic, version, sequence, opcode, bytes}`. The initial browser
target is BoxedWine's single-thread Emscripten release. Once a real adapter
transport exists, direct per-call dispatch is permitted by the design.
Document 160 verifies one direct synchronous browser graphics command through
that transport. Frame batching is an optional later
optimization, not an ABI requirement. Creation, lock/unlock, `Reset`, and
`Present` remain synchronous results. Texture/VB/IB locks use guest CPU
backing; unlock sends the changed range. `Reset` recreates the implicit
backbuffer and reuploads guest-backed managed resources.

If a future build moves rendering across a worker/main-thread boundary, the
same opcodes can be coalesced at `Present` or moved to an OffscreenCanvas-owning
worker. That is explicitly **NOT** part of the initial implementation.

## WebGL2 plan

- Uniform-controlled GLSL emulates FVF/declarations, transforms, material,
  lights, fog/alpha, and texture-stage operations without state permutations.
- Material/light commands are mandatory: 70,045 / 6,415 / 4,072 observed.
- P8 uses a 256×1 RGBA palette texture; colour key is shader alpha/discard.
- `DrawPrimitiveUP` uses a streaming buffer; indexed draws bind resource handles.

## Measurement gate result and next proof

Document 154 completed the bounded native argument histograms on the smallest
useful scene. It measured the render/texture/sampler/FVF/texture/primitive
surface without another content tour. P8 and DXT were absent from that scene;
world transform slots 256..317 were present. Document 156 then expanded the
WebGL shader matrix capacity to the D3D9 hard limit of 256 and revalidated the
driver harness.

Document 157 verifies a clean named-CLI browser Azrok launch executes at
87–122 MIPS bursts without a probe or override, although the client remains
white and browser D3D output is still unverified. Document 158 completes the
native guest-to-host trap proof, and 159 verifies the full browser round trip.
Document 160 then verifies WebGL2 clear plus one triangle on the existing
shared canvas, including guest `EAX=0x3001` and exit 0. The next gate is the
minimal D3D9 COM/vtable subset, not more content traversal or probe expansion.
Document 161 completes that subset with a native-loaded x86 `d3d9.dll` and
successful `Create9/CreateDevice/Clear/BeginScene/EndScene/Present`. The active
gate is now expansion to the measured method/resource surface.

`CheckDeviceFormat` is a separate guest-side cache requirement: its 367,297
Gate 1 calls must not repeatedly execute capability work, regardless of
cross-boundary cost.

## Evidence

- `artifacts/d3d9_probe/20260719_gate1/d3d9_probe_full_session.log`
- `tools/d3d9_probe/d3d9proxy.cpp`
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/project/emscripten/makefile`
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/platform/sdl/knativesystem.cpp`
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/platform/sdl/knativescreenSDL.cpp`
- Read-only BoxedWine source search on 2026-07-19: generic `/dev` patterns
  exist, but no renderer-specific DeviceIoControl/custom-device bridge exists.
- `152_GATE2C_SCHEDULER_AND_WINE_GUI_SMOKE_20260719.md`
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/tools/opengl/gl.c`
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/source/opengl/glcommon.cpp`
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/source/emulation/cpu/decoder.cpp`
- `154_GATE1_ARGFLUSH_CHARACTER_SELECT_20260719.md`
- `156_WEB_WORLDVIEWARRAY_CAPACITY_20260719.md`
- `157_GATE2C_CLEAN_NAMED_CLI_MIPS_20260719.md`
- `158_D3D9WEB_INT9A_PHASE0_20260719.md`
- `159_D3D9WEB_EMSCRIPTEN_PHASE1_PHASE2_20260719.md`
- `160_D3D9WEB_WEBGL2_PHASE3_20260719.md`
- `161_D3D9WEB_D3D9_COM_PHASE4_20260719.md`
