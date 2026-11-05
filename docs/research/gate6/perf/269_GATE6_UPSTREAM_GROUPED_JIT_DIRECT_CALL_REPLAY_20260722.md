# 269 — Upstream grouped WASM JIT direct-call replay

Date: 2026-07-22 KST

## Result

- **VERIFIED static/build:** a clean PatHouse recording from the accepted
  `boxedwine.upstreamjit51readhotrelease1` runtime exported 41,625 v5 blocks and
  exactly 41,625 manifest rows.  The official upstream BoxedWine pipeline
  optimized all blocks, merged them into 134 MT groups, and rewrote 13,788
  `next1`/`next2` exits as direct tail calls.
- **VERIFIED implementation/runtime:** the local page now records MT JIT caches
  and can stage/register official grouped-MT pipeline output before `main()`.
  Dynamic registration reported 134 groups, 41,625 entries, and 13,788 relocation
  patches.  The call order and ABI match upstream: persistence, group, entries,
  then patches.
- **VERIFIED browser correctness:** both grouped replay smoke sessions and every
  comparison run reached PatHouse with the reference carpet, walls, furniture,
  character face/body, Korean text, alpha, and culling.  Async-ring gaps,
  reorders, and errors remained zero.
- **VERIFIED adaptive A-B-A-B / optimization REJECTED:** grouped direct-call
  replay measured 35.048 and 36.657 FPS, while the adjacent no-replay controls
  measured 36.243 and 39.203 FPS.  The three adjacent B-vs-A effects were
  -3.30%, -10.60%, and -6.50%; median **-6.50%**.  Grouped direct-call replay is
  therefore not adopted.

## 1. Raw recording

The record latch was installed after WASM exports existed and before the first
guest block compiled.  MT export first called
`_wasm_jit_mt_prepare_export()` so worker-owned bytes, block metadata, and the
transition profile were mirrored to the page.

Raw ZIP:

- path: `tools/boxedwine_local/profiles/azrok-jit-record-raw.zip`
- bytes: 62,168,408
- SHA-256: `54726B40CF15C2CBE23132CE4A42D203D5A7F8C18A218906AE2C2A855FB0CB7E`
- ZIP entries: 41,627
- v5 WASM entries: 41,625
- manifest rows: 41,625
- cache/runtime version: v5 / 1
- transition profile sidecar: present

## 2. Official pipeline output

The exact upstream command used the current `C:\bwujit` pipeline and bundled
Binaryen:

```text
node C:\bwujit\project\emscripten\boxedwine-wasm-jit-cache-pipeline.mjs \
  --binaryen-js C:\bwujit\project\emscripten\binaryen_js.js \
  azrok-jit-record-raw.zip azrok-jit-grouped-direct.zip
```

Verified output:

- path: `tools/boxedwine_local/profiles/azrok-jit-grouped-direct.zip`
- bytes: 6,477,239
- SHA-256: `94982B43D4F14575FB6F6F618F06B44E0386DFF4F71CEE73C29845227A431520`
- format/version/cache/shape: `boxedwine-wasm-jit-grouped-cache` / 2 / v5 / MT
- groups: 134 in both ZIP and manifest
- entries: 41,625
- direct-call relocation patches: 13,788
- optimized modules: 41,625 / 41,625
- merged WASM bytes: 320,967,119 -> 70,157,228 (-78.14%)
- estimated function imports: 1,498,500 -> 4,824
- ZIP bytes: 62,168,408 -> 6,477,239

Static review found no P0 mismatch in the minimal loader.  It fetches and
decompresses the grouped ZIP before appending the runtime script, then registers
the staged groups synchronously from `onRuntimeInitialized`, after exports are
installed and before `main()`.

## 3. Adaptive comparison with covariates

The user foreground was never taken.  Foreground changes are covariates, not
rejection criteria.  Only hidden or fully throttled page windows are discarded.
All four windows stayed `document.visibilityState=visible`; all 30 foreground
samples in each window were `WindowsTerminal`.

The default A-B-A was extended to A-B-A-B because the two controls differed by
8.17%, so drift control was not established after the first three runs.

| Order | Condition | FPS | renderer CPU ms/Present | Foreground | Visibility |
|---|---|---:|---:|---|---|
| A1 | no grouped replay | 36.243 | 61.91 | WindowsTerminal 30 | visible |
| B1 | grouped direct calls | 35.048 | 64.00 | WindowsTerminal 30 | visible |
| A2 | no grouped replay | 39.203 | 56.23 | WindowsTerminal 30 | visible |
| B2 | grouped direct calls | 36.657 | 57.03 | WindowsTerminal 30 | visible |

Each FPS value uses adjacent `D3D9WEB_ASYNC_RING_MAIN` sequence/timestamp
endpoints inside a 30-second OS accounting window.  The three adjacent relative
effects are:

- B1 vs A1: -3.30%
- B1 vs A2: -10.60%
- B2 vs A2: -6.50%
- median: **-6.50%**

The grouped/direct-call cache is retained only as a diagnostic artifact and is
not the default URL.  The next isolation gate is a grouped pipeline output with
`--no-direct-calls`: if that is neutral, the regression belongs to direct-call
tails; if it also regresses, group registration/instantiation is the cause.

## 4. No-direct-call grouped isolation

The official pipeline was rerun with `--no-direct-calls` against the same raw
record.  It produced the same 134 groups and 41,625 entries with zero patches:

- path: `tools/boxedwine_local/profiles/azrok-jit-grouped-nodirect.zip`
- bytes: 6,246,148
- SHA-256: `D21CD1B124AE9E537DF59E611054F4D65D651C52455E5555892079FF4BA4A848`
- groups / entries / patches: 134 / 41,625 / 0

Smoke registration and the PatHouse visual gate passed.  The adaptive comparison
was extended to A-B-A-B because the first B effect overlapped the +/-3% noise
band.  No sample was discarded for foreground changes:

| Order | Condition | FPS | renderer CPU ms/Present | Foreground | Visibility |
|---|---|---:|---:|---|---|
| A1 | no grouped replay | 37.451 | 56.97 | Termius 22; AfterFX 5; WindowsTerminal 3 | visible |
| B1 | grouped, no direct calls | 37.073 | 56.11 | AfterFX 30 | visible |
| A2 | no grouped replay | 38.295 | 53.97 | AfterFX 20; WindowsTerminal 10 | visible |
| B2 | grouped, no direct calls | 28.561 | 81.89 | AfterFX 19; explorer 8; Comet 3 | visible |

The A drift was +2.26%.  Adjacent B effects were -1.01%, -3.19%, and
-25.42%; their robust median was **-3.19%**.  B2 coincided with large renderer
CPU/resource contention, but it is retained as required and the median limits
its influence.  Grouping alone is not an optimization and remains disabled.

**VERIFIED static root cause:** the upstream direct-call pipeline recognizes and
rewrites only the `fetchNextOp(cpu); return` fallback tail.  Persistent blocks
normally take an earlier reloc fast path that writes `cpu->nextOp` and returns,
so the 13,788 rewritten tails do not remove the common dispatcher boundary.
They add a large cross-function call graph without touching the hot edge.  The
next useful implementation gate must expose/rewrite the normal reloc fast path;
further next1/next2 subset permutations of the existing fallback rewrite are not
expected to improve steady-state PatHouse FPS.
