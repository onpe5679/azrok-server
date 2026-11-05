# Gate 2c texture-binding cache and native window (2026-07-20)

## VERIFIED

- Native `Azrok.exe -NX 200 -NWND ...` PatHouse was measured with Windows `GetWindowRect` and `GetClientRect`: both are `1024x768`, at `(0,0)`. It is the current visual reference.
- Native and browser carpet draws (DPUP ordinals 22, 24--29) match in vertex hash, primitive/FVF/stride, WORLD, effective texture-stage and sampler state, per-draw render state, and logical texture-identity pattern.
- Guest and host texture layouts both use the same tight per-mip pitch, contiguous offsets, and supported format conversions. No half-width row-pitch arithmetic was found.
- A real host-side state bug existed: texture create/upload bound an internal resource on a GL texture unit without invalidating `gpuTextureHandles`. A later draw could therefore skip the D3D texture rebind and sample the upload resource instead of `boundTextures[stage]`.
- The browser host and mirrored source now invalidate unit 0 after create/upload. `bindTexture` also updates the GPU binding shadow and clears the sampler-dirty bit after applying it.
- The served path uses cache token `texturebinding1`; direct HTTP retrieval contains both the invalidation and the bounded one-frame `bindingOk` diagnostic.
- Both edited runtime files pass `node --check`.

## INFERRED

- This stale GL binding can directly explain wrong object textures, including the observed carpet repetition and prior furniture/character-texture corruption. It is not yet proven to be the only carpet cause because the corrected frame has not been visually observed.

## NOT VERIFIED

- Corrected PatHouse visual equality against the native reference.
- Native texture mip-byte hashes versus browser `resource.raw` hashes.
- VIEW/PROJECTION/viewport equality for the same captured draw frame.
- Steady 120-Present FPS after the rendering fix.

No additional game instance should be started until the existing native window has actually exited. The next browser run must be a single session and must first report carpet `bindingOk=1.1` for ordinals 22--29 before visual and performance conclusions.
