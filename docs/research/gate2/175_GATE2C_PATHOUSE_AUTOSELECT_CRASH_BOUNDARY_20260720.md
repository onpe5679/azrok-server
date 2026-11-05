# 175 Gate 2c PatHouse automatic-selection crash boundary (2026-07-20)

## Scope

This is a bounded browser-render gate. It intentionally uses one existing
saved character and stops at the first PatHouse transition fault; it is not
content QA.

> **SUPERSEDES the PatHouse-render-status portion of 174.** The coordinate
> adapter itself remains a separate NOT VERIFIED usability issue because the
> user still observes manual-click drift.

## 2026-07-20 final gate result

> The earlier crash-boundary status below is retained as the investigation
> record. Its `PatHouse 3D pixels remain unverified` conclusion is superseded
> by this section.

### VERIFIED

1. The browser exception mapper placed the initial terminal fault in
   `/opt/wine/lib/wine/i386-unix/ntdll.dll.so+0x4B7BD`, not at a verified
   Acknex RVA. Immediately before it, the D3D9Web host reported
   `bad DestroyResource handle=44`; after making duplicate destroy harmless,
   it reported `bad UploadResource handle=44`. These are the same command
   stream ordering failure: a resource is released before an already-issued
   unlock upload reaches the browser dispatcher.
2. `Resource_Release` in the project-owned guest `d3d9.dll` sent its destroy
   command and immediately freed both the resource data and COM object at
   refcount zero. The fault record's non-object vtable value (`0xFFFFFFFF`)
   after such a release is direct use-after-free evidence. The bridge is
   asynchronous at this boundary, so immediate reclamation is invalid here.
3. The guest now clamps a zero refcount, emits `COMMAND_DESTROY_RESOURCE` only
   once, and retains the resource allocation until process teardown. The host
   records the matching retirement as deferred and retains its WebGL backing
   object for the bounded smoke session. The revised guest DLL was rebuilt,
   copied into the exact `Azrok_D3D9Web_pathouse_seh2.zip` mount, and
   SHA-256-verified against the packaged DLL.
4. The corrected browser run produced no `D3D9WEB_PHASE6_ERROR` and no
   terminal `D3D9WEB_PATHOUSE_AV`. Its runtime command counter reached
   `562,176` with `965` `Present` calls. A captured browser frame visibly
   contains the PatHouse floor, furniture, character, and original 2D UI.
   This is direct browser rendering proof, not a protocol-only result.
5. Full per-upload byte hashing/logging was then replaced with bounded
   resource-event sampling. This does not change render commands; it removes
   diagnostic work that was dominating the interpreter during asset loading.

### Remaining, intentionally out of this gate

- The legacy SDL/HTML input-coordinate mismatch still prevents reliable
  manual character-creation clicks. The verified saved-character auto-select
  path remains the bounded render-gate entry and avoids treating content UI
  automation as renderer proof.
- Some Wine SEH trace lines at `0x1065BDE6` are handled by Wine during loading.
  They did not terminate the revised run and are not attributed to a module or
  treated as a blocker without a module/RVA record.
- PatHouse is the only required scene for this render proof. Plaza/OX or
  broader gameplay QA must not be expanded without a separate need.

## Follow-up: input and performance measurement setup

### VERIFIED

1. On the rendered PatHouse page, the DOM input canvas measured `640x480` and
   its CSS rectangle measured `640x480`, while the D3D9Web overlay measured
   `1024x768` over the same rectangle. This is a directly observed mixed
   coordinate space.
2. Standard mouse click events bypass `Browser.calculateMouseCoords`; their
   target coordinates are written by Emscripten's `fillMouseEventData`. The
   original path wrote CSS pixels without scaling, while the native browser
   input path used the overlay dimensions. This explains the observed
   above/left cursor drift.
3. The page previously appended `sound=false`, which caused BoxedWine to add
   `-nosound`. It now launches with `sound=true`; the new command line was
   directly observed without `-nosound`.

### VERIFIED

- The real event payload must stay in the legacy SDL `Module.canvas` source
  space (`640x480` in the observed page). The native input layer then performs
  the sole `640x480 -> 1024x768` virtual-desktop conversion. Scaling into the
  1024x768 D3D9Web overlay before this step applied that conversion twice.
- The native `Module.canvas` query and the browser dispatch allocation change
  (`HEAPU8.slice` -> `HEAPU8.subarray`) were rebuilt as one matching
  Emscripten 6.0.3 multi-threaded JS/WASM pair through WSL GNU Make with
  `NO_DEPS=1`. The active `boxedwine.pathouseav.{js,wasm}` pair now hashes to
  `8A7EBD823D6FD41A1B9EE3D1F1AF7F7854809CCB0AF529AFA8BBB6F0314072D4` and
  `C8BC4C99DEE4C146116918822E326CD84CD2481A55A8EC25A41044DC7470CCBF`.

### NOT VERIFIED

- Manual three-point cursor validation, including the real character-creation
  button, remains required. The active browser process predates the rebuilt
  pair until it is relaunched.
- A live command counter was added to expose opcode distribution every 1024
  bridge commands. A fresh run is required to derive a reliable steady-state
  FPS and choose CPU versus renderer optimization.

## Follow-up: first steady-state performance measurement

### VERIFIED

1. Before guest-side redundant-state suppression, a 10-second PatHouse sample
   produced `98` Present calls (about `9.8 FPS`). `SetRenderState`,
   `SetTextureStageState`, and `SetSamplerState` accounted for roughly
   `42,000` bridge commands in that sample.
2. The guest D3D9 device now sends each of those state commands only on its
   first use or when its value changes; validity bits ensure an initial zero
   state is not accidentally suppressed. The revised DLL was rebuilt and
   mounted as `Azrok_D3D9Web_pathouse_seh3.zip`.
3. A comparable later 10-second sample reached `126` Present calls (about
   `12.6 FPS`). State commands fell sharply, but `DrawPrimitiveUP` still
   accounted for about `448` calls per second. The 50-FPS target is therefore
   not met, and duplicated state writes are no longer the dominant limiter.

### INFERRED, pending direct timing counters

- The remaining dominant cost is likely synchronous worker-to-main-thread
  proxying for each D3D bridge command. The multi-threaded Emscripten target
  uses `PROXY_TO_PTHREAD` while OffscreenCanvas support is disabled, so every
  `INT 0x9A` render command crosses that boundary. Direct per-op timing and
  x87 instruction counts are the next required measurement before adopting
  command batching or a CPU JIT strategy.

### Pending runtime verification

- The rebuilt JS/WASM pair is packaged but has not yet received a fresh,
  comparable 10-second PatHouse performance sample. No FPS benefit is claimed
  for `subarray` until that sample is collected.

## VERIFIED

1. The local preservation server's opt-in `--auto-select-existing` path sends
   no invented selection packet. After the eighth normal `0x0016` heartbeat,
   it invokes the server's existing C2S `0x0005` selection handler with slot
   zero.
2. The live browser client accepted that route and the server recorded the
   normal selection bootstrap: S2C `0x0003` with
   `Data\\Space\\PatHouse`, S2C `0x0007` (472 bytes), followed by the
   existing `0x0005`, `0x000A`, and `0x000B` bootstrap packets. The client then
   sent its normal `0x0017` updates and `0x0008` inventory snapshot.
3. The original client then terminated with Wine's unhandled access violation
   `c0000005` at guest address `0x1072B7BD`; the server observed a disconnect.
   The D3D9Web host had already accepted texture/resource commands and emitted
   no `D3D9WEB_PHASE6_ERROR`, so the fault is after the network route and is
   not yet attributable to a specific renderer resource or original module.
4. The first one-address host mapper compared `cpu->eip` directly against the
   absolute Wine address. That comparison is invalid when a nonzero guest code
   segment base is present. The browser-only mapper now compares
   `CS.base + EIP` instead, and posts its one-shot module/RVA/register result to
   a project-local diagnostic receiver. This changes neither the client binary
   nor the D3D command path.
5. PE-section measurements exclude `Azrok.exe` and the custom `d3d9.dll` as
   executable owners of `0x1072B7BD`: the former is fixed at `0x00400000` and
   relocation-stripped, while no 64 KiB-aligned relocation of the latter puts
   that address in its `.text`. If `acknex.dll` was relocated to `0x10700000`,
   the address decodes as `acknex.dll+0x2B7BD`: a vtable-reachable cleanup
   method that calls `Release` on `this+0xC60` and `this+0xC64`, then clears
   the latter field. Its owner pointer is ESI.

## NOT VERIFIED

- The faulting module, RVA, and access operands remain pending one refreshed
  browser run of the rebuilt diagnostic WASM. No root cause or renderer fix is
  claimed until that record exists.
- The `acknex.dll+0x2B7BD` mapping is a strong conditional candidate, not a
  runtime module-map proof. The refreshed mapper records ESI, EDI, and the
  readable owner fields `+0xC60/+0xC64` to distinguish a bad owner from a
  bad COM-resource lifetime.
- PatHouse 3D pixels remain unverified.

## Next measurement

Run only the rebuilt diagnostic package through the existing saved-character
auto-selection route and collect the single `D3D9WEB_PATHOUSE_AV` record.
Use its module/RVA to choose either original-client static analysis or a
D3D9Web correction. Do not expand gameplay coverage before that render gate.
