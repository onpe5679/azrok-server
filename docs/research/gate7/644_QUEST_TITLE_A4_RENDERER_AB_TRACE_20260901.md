# 644 — Quest title A4 renderer A/B and live trace

Date: 2026-09-01 KST

## Direct live result

- **VERIFIED:** an actual account-bound browser session reached PatHouse and displayed the reported state: upper quest-list title glyphs were corrupted while the lower quest title/body `이유식을 먹여보자` rendered correctly.
- **VERIFIED / REJECTED:** the plain-DLL/recycle-off canary reproduced the upper-title corruption in that same quest panel. Texture recycle is not the fix.
- **VERIFIED:** all live dynamic text candidates were `D3DFMT_A4R4G4B4` (format 26), DrawPrimitiveUP, 40-byte FVF 708 vertices, fixed-function `MODULATE(TEXTURE, DIFFUSE)` color/alpha, blend `SRCALPHA/INVSRCALPHA`, alpha-test disabled, and nearest min/mag filtering.
- **VERIFIED / REJECTED:** forcing `CLAMP_TO_EDGE` for A4 text textures did not repair the upper title in the actual quest panel.
- **VERIFIED / REJECTED:** preserving raw D3D A4R4G4B4 word order instead of converting to WebGL RGBA4 did not reach first game screen after 151 seconds; it is not a viable fix.

## Trace boundary

The live title/body text rows are 1024x32 A4 textures. The trace showed their normal texture-stage and blend contracts; a subset used D3D default WRAP addressing, but the sampled U/V rectangle stays inside the texture and clamp A/B had no visual effect. Therefore the next hypothesis is not texture recycle, generic sampler filtering, address mode, or nibble rotation.

An opt-in `questTitleTrace=1` instrument was added to the host runtime. It records only 1024x32 A4 text draws and preserves the latest 128 records, avoiding character-select startup records displacing the quest frame. `a4Dump=<handle>` support was also added to emit a selected raw A4 texture as PNG, but the follow-up reload stalled during engine initialization (162 seconds, no Present) and is excluded from evidence.

## Production boundary

The production default retains the known-safe D3D9 path. All new renderer controls are query-gated diagnostics/candidates (`questTitleTrace`, `a4TextClamp`, `a4RawOrder`, `a4Dump`) and change no normal player behavior. No title fix has been promoted because no candidate has corrected the actual quest panel.
