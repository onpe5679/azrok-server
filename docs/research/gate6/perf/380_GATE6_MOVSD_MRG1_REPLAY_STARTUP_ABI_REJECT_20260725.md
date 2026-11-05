# 380 — MRG1 replay startup ABI rejection

Date: 2026-07-25  
Status: **VERIFIED** — MRG1 replay artifact is rejected before guest start; no FPS verdict.

## Direct browser evidence

On a fresh watcher-created Edge profile, CDP verified one `about:blank` page, the three anti-throttling flags, and a 724 MiB initial Edge working set. The sole page was navigated to MRG1's pinned 114-group URL and its enabled button was activated with CDP `Input.dispatchMouseEvent`, not `Runtime.evaluate`. `navigator.userActivation.hasBeenActive` was then `true`.

The initial retry reached `jitReplay=staged`, `groups=114`, `wasmJitMtPendingGroups.length=114`, and `wasmJitPersistenceWanted=true`, but never registered a group or presented a frame. Its app/root/private ZIP requests completed and the app/root ZIP files were directly visible in `FS.readdir('/')`.

A second, fresh, URL-gated passive dependency trace recorded:

```
[{atMs:24895.8,count:1}, {atMs:24897.6,count:2}, {atMs:24897.8,count:3},
 {atMs:24913.3,count:2}, {atMs:24928.4,count:1}, {atMs:26194.7,count:0}]
```

Thus all Emscripten pre-run dependencies, including the generated pthread pool, resolved. The former `loading-workers` hypothesis is **rejected**. No dependency was removed, forced, or bypassed by this diagnostic.

After count zero, the live runtime still had `jitReplay=staged`, pending 114, zero registered groups and zero Presents. Direct CDP evaluation found `typeof Module._wasm_jit_get_movsd_runtime_zero_guard_abi_version === 'undefined'`. The page replay handler requires that value to be ABI 1 for the MRG1 raw/cache identity and therefore fails closed before registration.

## Static artifact corroboration

The served MRG1 sidecar and its Build/MRG1 source copy are byte-identical:

```
boxedwine.upstreamjit64fn6inlineabi2movsdruntimezero1.js
SHA-256 80195DB565C5000935130E534F4724EC1570DFE9F6D6FAB85C02665739DB0572
```

That hash is also the ordinary accepted ABI2 JS hash. It has no generated assignment for `_wasm_jit_get_movsd_runtime_zero_guard_abi_version`, whereas the MRG1 make target explicitly requires that export in `EXTRA_LD_FLAGS`. The MRG1 Wasm is 3,050,102 bytes, SHA-256 `BF47108D49A2C217475833E3CF8466023F79685315571F83DB2EAFF1CCEF5D39`.

Consequently the artifact presently staged under the MRG1 name is not a replay-compatible MRG1 JS/Wasm sidecar pair, despite the target declaration. The runtime identity gate did its intended job and prevented guest execution.

## Rebuild recovery (VERIFIED, new generation only)

The stale-link cause is now directly bounded: the link rule does not list its flag/LD command line as a prerequisite, so changing the requested export can leave an otherwise up-to-date MRG1 link sidecar in place. A first rebuild attempt was stopped before compilation because the native make environment had no POSIX `grep`; a second low-priority `-j31` rebuild with Git's `usr/bin` on PATH completed without an error line.

The rebuilt `Build/MRG1/boxedwine.js` contains the required generated guard assignment and is 327,079 bytes, SHA-256 `46CC633AEA9C1301C4264C921FCA7DEEEF1F82F762768F62E90A22BFB16C9F85`. Its Wasm is 3,050,114 bytes, SHA-256 `CC3C94C05B2E95E0239DEA7D2B5262649C7CC2688369C3ABA15AE9C07C985AD0`. Both were copied to the served MRG1 names only after matching source/destination SHA-256 checks; the rejected sidecars were preserved under `artifacts/boxedwine/mrg1_rebuild_20260725/stale_sidecar_before_rebuild/`.

This creates a new MRG1 generation. The old 35,804-entry raw and 114-group archive are bound to the rejected sidecars and remain preserved evidence only; they are not eligible for this rebuilt runtime.

## Consequence and next gate

This is an **artifact/preflight rejection**, not a MOVSD semantic or FPS rejection. Do not use the 379 raw/cache for replay or A-B-A(B); do not weaken the ABI gate. Rebuild MRG1 from the declared target, verify the generated JS assignment and live ABI=1, then perform a new private cache-off record, transform, identity pin, replay render proof, and only then fresh-process accepted-vs-candidate performance measurement. Existing accepted, MRG2 and parity assets remain untouched.
