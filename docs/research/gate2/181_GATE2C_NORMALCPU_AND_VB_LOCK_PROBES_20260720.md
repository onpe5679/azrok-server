# 181 Gate 2c NormalCPU and dynamic-VB probes (2026-07-20)

## VERIFIED

1. PatHouse worker opcode samples map as follows in the BoxedWine decoder:
   opcode 13 is `ADD r/m32, imm32`; 301 is `SHRD r16, r16, imm8`; and 324 is
   `CMPXCHG r32, r32`. Each already uses a dedicated NormalCPU handler rather
   than a generic fallback.
2. The browser Emscripten profile has no `BOXEDWINE_JIT`. Its NormalCPU loop
   invokes each decoded operation through an indirect handler pointer.
3. `BOXEDWINE_DIRECT_NORMAL_DISPATCH` preserves the same handlers but changes
   the next-operation transition to the direct dispatch path. A separate 1
   GiB `Build/ProfileDirect` artifact is being built for a screenshot and
   120-Present A/B test; the known-good profile remains unchanged.
4. `handle=10`, kind-2 uploads originate only from the D3D9-web vertex-buffer
   `Lock`/`Unlock` path. For `size == 0`, the wrapper deliberately resolves the
   lock to the remainder of the buffer, so the observed 108,940-byte upload is
   either `Lock(0, 0, ...)` or an explicit whole-buffer lock.
5. Eight bounded first-use lock probes now carry requested size, resolved size,
   D3D lock flags, and a full-buffer FNV-1a hash through the existing upload
   command. The host emits `D3D9WEB_VB_LOCK` only for those eight samples.
   This avoids adding a hash to steady-state frames.

## NOT VERIFIED

- Whether Acknex genuinely rewrites the dynamic vertex data each frame, or
  repeats identical contents.
- Whether direct normal dispatch materially raises PatHouse FPS.

## Decision rule

- Differing hashes prove genuine dynamic geometry: retain upload semantics and
  measure CPU dispatch before proposing an upload skip.
- Identical hashes permit a guest-side unchanged-buffer suppression experiment.
- The direct-dispatch profile is promoted only if it produces a visible
  PatHouse frame and an improved comparable 120-Present result with no WebGL
  errors.
