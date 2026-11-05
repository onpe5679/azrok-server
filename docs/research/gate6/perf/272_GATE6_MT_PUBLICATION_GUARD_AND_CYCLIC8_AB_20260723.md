# 272 - MT direct-tail publication guard and bounded cyclic8 A/B

Date: 2026-07-23 KST

## Result

- **VERIFIED static/build/browser:** the accepted document-271 fast-tail cache
  had a correctness hole.  `targetReloc[0] == liveTarget` proved relocation
  identity but not that the target's exact compiled entry was still published.
  Invalidation atomically clears `DecodedOp::pfnJitCode` while the imported
  relocation array can remain alive until retirement, so a stale table entry
  was reachable.
- **VERIFIED fix:** imported group arrays now reserve one publication-token
  word.  Accepted publication stores the exact table index there before
  publishing `pfnJitCode`.  Every offline direct tail checks relocation
  identity and atomically compares that token to the target's live
  `pfnJitCode` before the call.  Invalidation to zero and a later new table
  index both fail closed to the dispatcher.
- **VERIFIED safe baseline replacement:** the rebuilt acyclic cache has 134
  valid groups, 41,625 entries, 10,813 rewrites, and 32,439 patches, exactly
  three patches per rewrite.  The browser loader measured the live ABI offset
  as 12 and registered the cache before `main()`.
- **VERIFIED adaptive A-B-A-B / cyclic8 NOT ADOPTED:** safe acyclic A and
  publication-safe cyclic8 B measured 36.995 / 39.541 / 38.938 / 37.404 FPS.
  Adjacent effects were +6.882% and -3.940%; their two-pair center is +1.471%
  and condition means differ by only +1.332%.  The effects disagree in sign
  and remain inside the real-environment noise band.  Cyclic8 stays opt-in;
  the publication-safe acyclic artifact becomes the default for stem55.

## 1. Static defect and exact guard

The old direct tail checked:

```text
target relocation slot 0 == live target pointer
cpu->yield == 0
```

That array slot is an identity pointer, not a publication generation.  The
target `pfnJitCode` can be cleared during invalidation while the array remains
allocated for the existing hazard/reaper lifetime.

The replacement imported-array layout is:

```text
[reloc slot 0 ... reloc slot N-1, exact published table index]
```

The last word is written with `SEQ_CST` before publishing the same table index
to `DecodedOp::pfnJitCode`.  Generated MT direct tails now require all of:

```text
targetReloc[0] == liveTarget
atomic(targetReloc[targetRelocCount]) == atomic(liveTarget->pfnJitCode)
cpu->yield == 0
```

Cyclic tails additionally require `!cpu->wasmJitBailout` and direct-chain
depth below 8.  Both loads use Wasm `i32.atomic.load` with 4-byte alignment.
The narrow invalidate-after-check execution race is the same active-call
hazard model already used by the normal MT dispatcher; this change removes the
deterministic stale-slot acceptance that existed before the check.

Exact runtime ABI, extracted from the built Wasm exports:

```text
offsetof(DecodedOp, pfnJitCode) = 12
offsetof(CPU, wasmJitDirectChainDepth) = 1660
offsetof(CPU, wasmJitBailout) = 132
```

The grouped manifest records these constants, and the page refuses a direct
cache before registration when the manifest field, runtime getter, alignment,
or token-word count is absent or mismatched.

## 2. Build and artifacts

Runtime:

```text
tools/boxedwine_local/assets_d3d9web/boxedwine.upstreamjit55pubguard1.js
SHA-256 F16DE1E6C6C884CEC16B8362B1B86D9461507CD31BBF8A7CBCAF7BCABEFA25AF

tools/boxedwine_local/assets_d3d9web/boxedwine.upstreamjit55pubguard1.wasm
SHA-256 3AA5752D474DE66E3F0C4E126772960E57A33CD3875E7A162FBEBF7771FC7B18
```

Safe acyclic A:

```text
tools/boxedwine_local/profiles/azrok-jit-grouped-hotnext12-pubguard1.zip
SHA-256 6330D14A486FB06C12C0C48C35AFF3BBF394D544A3A44874F5314CAB17917816
groups 134; entries 41,625; rewrites 10,813; patches 32,439
```

Bounded cyclic8 B:

```text
tools/boxedwine_local/profiles/azrok-jit-grouped-hotnext12-cyclic8-pubguard1.zip
SHA-256 64D0DC958A690622BEFEEC787598A9A0ABA3CEFFDE7C62D3623EE12C65882BE0
groups 134; entries 41,625; rewrites 15,108; cyclic guards 4,295;
patches 45,324
```

Both ZIPs passed `WebAssembly.validate` for 134/134 group modules.  Patch count
is exactly `rewrites * 3`; manifest publication ABI is 12.  B additionally
records depth 1660, bailout 132, and limit 8.

The Emscripten `testMultiThreadedJit` target initially exposed an unrelated
missing browser-socket preprocessor guard in `ksocket.cpp`; the call now uses
the same `__EMSCRIPTEN__ && BOXEDWINE_EMSCRIPTEN_SOCKETS` guard as the other
call sites and the target links.  The focused Node broker test still fails at
its pre-existing worker publication barrier before reaching the new token
assertion, so a standalone generated-guard execution unit remains
**NOT VERIFIED**.  Static instruction validation and the live browser path are
verified.

## 3. Browser correctness and protocol gate

Both A and B registered before `main()` with their exact patch counts and live
ABI values.  Each fresh one-tab run naturally reached the existing auto-select
threshold, and the server directly logged:

```text
C2S 0x0005
S2C 0x0003 Data\Space\PatHouse
S2C 0x0007 + 0x0005 + 0x000A + 0x000B
C2S 0x0017 + 0x0017 + 0x0008
```

The accepted 1024x768-display PatHouse reference remained intact in all four
runs: carpet mip chain, walls, furniture, character face/body, Korean text,
alpha, and culling.  Every measured async-ring report had zero gaps, reorders,
and errors.  The page stayed `visible`; no sample was discarded.  The existing
44.1 kHz BGM root and audio path were unchanged.

## 4. Adaptive real-environment A-B-A-B

Foreground changes were recorded, not used as rejection criteria.  In this
run every one-second covariate sample was `WindowsTerminal`; the browser was
never brought to the foreground by automation.

| Order | Cache | Exact Present window | FPS | renderer CPU ms/Present | Foreground | Visibility |
|---|---|---:|---:|---:|---|---|
| A1 | safe acyclic | 1,080 / 29.193 s | 36.995 | 58.975 | WindowsTerminal 35/35 | visible |
| B1 | safe cyclic8 | 1,320 / 33.383 s | 39.541 | 50.847 | WindowsTerminal 35/35 | visible |
| A2 | safe acyclic | 1,200 / 30.818 s | 38.938 | 52.615 | WindowsTerminal 35/35 | visible |
| B2 | safe cyclic8 | 1,200 / 32.082 s | 37.404 | 56.083 | WindowsTerminal 35/35 | visible |

A drifted +5.252%, beyond the approximate 3% noise threshold, so the run was
correctly extended from A-B-A to A-B-A-B.  The adjacent effects then had
opposite signs.  Mean A is 37.967 FPS and mean B is 38.473 FPS (+1.332%).  This
does not justify the additional 4,295 cyclic tails.

## 5. Deployment and next gate

`index_d3d9web_pathouse.html` now selects the publication-safe acyclic ZIP only
for `boxedwine.upstreamjit55pubguard1` when `jitCacheUrl` is omitted and record
mode is off.  The old stem51 implicit cache default was removed.  Explicit old
2-patch direct caches fail closed because they lack `runtimePublication`.

The final visible browser session is returned to stem55 + safe acyclic cache.
Performance remains about 37--39 FPS in static PatHouse, below the 50 FPS goal.
The next optimization gate must target a different remaining cost rather than
expand cyclic direct chaining further.
