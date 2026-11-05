# 270 - MT hot `next2` fast-path stitch

Date: 2026-07-23 KST

## Result

- **VERIFIED static:** the previous upstream grouped-JIT experiment rewrote only
  the cold `fetchNextOp(cpu); return` fallback.  The normal persistence path
  instead validates a live `DecodedOp::next`, stores it in `cpu->nextOp`, and
  returns to the dispatcher.  This experiment preserves that live validation
  and conditionally replaces only the final return of the successful `next2`
  arm.
- **VERIFIED implementation/build:** a strict structured-WASM matcher rewrote
  2,882 resolved, same-group, acyclic `next2` success arms.  A direct tail is
  taken only when the target relocation array exists, its slot 0 still equals
  the live target accepted by the original arm, and `cpu->yield == 0`.
  Otherwise the original dispatcher return remains.  `next1`, helper fallback,
  cross-group, unresolved, cyclic, and pattern-miss paths are unchanged.
- **VERIFIED browser correctness:** both replay sessions registered exactly 134
  groups, 41,625 entries, and 5,764 relocation patches before `main()`.  PatHouse
  retained the reference carpet, walls, furniture, character face/body, Korean
  text, alpha, and culling.  Every measured async-ring endpoint reported zero
  gaps, reorders, and errors.
- **VERIFIED adaptive A-B-A-B / NOT ADOPTED:** the four visible real-environment
  windows measured 39.337 / 40.556 / 34.578 / 34.991 FPS.  Adjacent B effects
  were +3.10%, +17.29%, and +1.19%; median +3.10%.  The two A controls drifted
  -12.10%, and the nearest-load A2-to-B2 result was inside the established 3%
  noise band.  This is not strong enough for default adoption.  The artifact is
  retained as a safe diagnostic candidate.

## 1. Safe fast-arm rewrite

Changed source:

```text
C:\bwujit\project\emscripten\boxedwine-wasm-jit-cache-pipeline.mjs
```

The matcher anchors on the exact persistence-mode `next2` sequence after the
local Binaryen optimization pass:

```text
relocBase -> reloc slot -> live op->next
cpu->nextOp = liveTarget
return
```

The store is preserved.  Immediately after it, the added tail performs:

```text
targetReloc[0] == liveTarget && cpu->yield == 0
    ? return_call target(cpu, targetReloc)
    : original return
```

The target function ABI remains `(i32 cpu, i32 relocBase) -> void`.  Both
relocation placeholders at each rewritten site are patched to the same target
array.  The runtime therefore registered 5,764 patches for 2,882 sites.

## 2. Whole-corpus structural gate

Output artifact:

- path: `tools/boxedwine_local/profiles/azrok-jit-grouped-hotnext2.zip`
- bytes: 6,346,482
- SHA-256: `F591C02E6F4693993AE4B8B3AAAEC38D1383DD835E0DE52D40A501C52B3616D2`
- groups / entries: 134 / 41,625
- eligible `next2` edges: 4,483
- target-without-reloc exclusions: 339
- rewritten / strict pattern misses: 2,882 / 1,601
- fallback rewrites: 0
- relocation patches: 5,764

**VERIFIED:** `node --check` passed, `WebAssembly.validate` passed for 134/134
group modules, ZIP CRC passed, and patch-range/opcode/target-group/duplicate
checks all reported zero failures.  Group paths and entry membership exactly
match the no-direct grouped control.

The 1,601 strict misses are intentionally preserved.  A sampled miss had a
manifest `next2` target that Binaryen DCE had removed from the body, so there
was no live fast-success arm to rewrite.

The full resolved transition graph contains 47,701 edges.  Tarjan analysis
identified the same 4,747 cyclic keys as the pipeline.  After the same-group,
acyclic, target-reloc filters, the `next2`-only DAG has a maximum path of 16
blocks; only 28 starting nodes reach depth 10 or greater.

## 3. Adaptive real-environment comparison

The game tab stayed visible in every window.  Foreground application changes
were retained as covariates.  No sample was discarded for a foreground change.
The default A-B-A was extended to A-B-A-B because A1 and A2 did not approximate
one another.

| Order | Condition | FPS | renderer CPU ms/Present | Foreground covariate | Visibility |
|---|---|---:|---:|---|---|
| A1 | accepted runtime, no grouped replay | 39.337 | 56.07 | Acrobat 18; Bandizip 11; AfterFX 1 | visible |
| B1 | guarded hot-`next2` replay | 40.556 | 52.72 | Hwp 30 | visible |
| A2 | accepted runtime, no grouped replay | 34.578 | 71.39 | Comet 18; WindowsTerminal 4; AfterFX 4; Explorer 3; Discord 1 | visible |
| B2 | guarded hot-`next2` replay | 34.991 | 74.07 | AfterFX 30 | visible |

Exact Present/timestamp endpoints:

- A1: 1,200 Presents / 30.506 s = 39.3365 FPS
- B1: 1,200 Presents / 29.589 s = 40.5556 FPS
- A2: 960 Presents / 27.763 s = 34.5784 FPS
- B2: 960 Presents / 27.436 s = 34.9905 FPS

Adjacent effects:

- B1 vs A1: +3.099%
- B1 vs A2: +17.286%
- B2 vs A2: +1.192%
- median: **+3.099%**

The controls' -12.096% drift and the +1.192% nearest-load result prevent an
acceptance claim.  No additional swaps are made: the requested adaptive rule
ends ambiguous comparisons after A-B-A-B.

## 4. Next gate

The current record's transition sidecar contains aggregate `fetchNext`
classification, not per-edge weights, so it cannot prove whether the 2,882
rewritten arms cover the hot transitions.  Before broadening the rewrite, the
next static/dynamic gate is to measure or safely derive executed edge coverage,
then assess a correspondingly guarded `next1` success-arm stitch.  The current
hot-`next2` ZIP remains opt-in and the accepted default remains the no-replay
runtime.
