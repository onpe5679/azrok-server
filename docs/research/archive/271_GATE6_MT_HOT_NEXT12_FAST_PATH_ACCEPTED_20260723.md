# 271 - MT hot `next1` + `next2` fast-path stitch

> **SUPERSEDED by 272.** The measured uplift remains historical evidence, but
> the 2-patch artifact's relocation identity check did not prove current JIT
> publication after invalidation.  Document 272 replaces it with a 3-patch
> publication-safe artifact and re-evaluates the cyclic extension.

Date: 2026-07-23 KST

## Result

- **VERIFIED static/build:** the strict guarded fast-success matcher was
  extended from `next2` to both Binaryen shapes observed for persistence-mode
  `next1`.  The 41,625-block corpus rewrote 10,813 live fast arms, rewrote zero
  helper fallbacks, and emitted exactly 21,626 relocation patches.
- **VERIFIED browser correctness:** explicit replay and the parameter-free
  default path both registered 134 groups, 41,625 entries, and 21,626 patches
  before `main()`.  PatHouse retained the reference carpet, walls, furniture,
  character face/body, Korean text, alpha, and culling.  Async-ring gaps,
  reorders, and errors remained zero.
- **VERIFIED adaptive A-B-A / ACCEPTED:** no-replay A1, combined replay B1,
  and no-replay A2 measured 37.802 / 39.502 / 36.753 FPS.  A drift was -2.775%,
  so the default A-B-A rule stopped without a fourth swap.  Adjacent B effects
  were +4.497% and +7.479%, median **+5.988%**.  The combined cache is adopted
  for the accepted stem51 runtime.
- **VERIFIED deployment:** omitting `jitCacheUrl` now selects the accepted
  combined ZIP only for `boxedwine.upstreamjit51readhotrelease1` and only when
  not recording.  `jitCacheUrl=off` keeps an immediate no-replay rollback path.

## 1. Strict `next1` extension

Changed source:

```text
C:\bwujit\project\emscripten\boxedwine-wasm-jit-cache-pipeline.mjs
```

`blockNext1` resolves a live target through:

```text
relocBase -> nextJump cache-slot pointer -> live target
```

Binaryen emitted two exact forms in the recorded Azrok corpus:

1. `local.get relocBase; local.tee target; if; load(target, slot)`
2. `local.get relocBase; if; load(relocBase, slot); local.tee target`

Only these two structured shapes are accepted.  Both retain the original live
target guards and `cpu->nextOp` store.  The direct tail executes only when:

```text
targetReloc[0] == liveTarget && cpu->yield == 0
```

All pattern misses, missing-reloc targets, cyclic edges, unresolved or
cross-group targets, helper fallbacks, and generic jumps remain on the original
dispatcher return.

## 2. Corpus and graph gate

Canonical artifact:

- path: `tools/boxedwine_local/profiles/azrok-jit-grouped-hotnext12.zip`
- bytes: 6,561,534
- SHA-256: `AC5D7EB291738F6A9233E41D74157D99B520D2575E04C31EC1AF4883667617AF`
- groups / entries: 134 / 41,625
- `next1`: eligible 8,919; no-reloc 2,494; rewritten 7,931;
  strict misses 988
- `next1` matched shapes: tee-base 4,309; direct-base 3,622
- `next2`: eligible 4,483; no-reloc 339; rewritten 2,882;
  strict misses 1,601
- total rewritten: 10,813
- helper fallback rewritten: 0
- patches: 21,626 = 2 x rewritten

**VERIFIED:** ZIP CRC passed, `WebAssembly.validate` passed for 134/134 group
modules, and patch offset/opcode/cross-group/duplicate checks all reported zero.
Group membership stayed identical to the earlier hot-`next2` artifact.

The full graph has 4,747 cyclic keys, all excluded.  The eligible combined DAG
has 13,402 edges and a maximum path of 41 blocks.  Every emitted tail retains
the yield guard.

## 3. Offline pipeline cost fix

The old patch locator scanned every group WASM once per marker, making the
combined build O(patches x bytes).  It now recognizes the exact
`i32.const + 5-byte padded SLEB` marker form in one linear module scan, maps the
numeric marker to its expected site, and retains fatal zero-hit or duplicate-hit
checks.

Two complete builds produced byte-identical ZIPs and the same SHA-256.  In the
observed run, wall time fell from about 18m44s to 7m52s (about 2.4x faster).
This changes offline build cost only, not game runtime.

## 4. Adaptive real-environment comparison

No foreground application change was used as a discard criterion.  All windows
stayed visible and all FIFO reports had zero errors.

| Order | Condition | FPS | renderer CPU ms/Present | Foreground covariate | Visibility |
|---|---|---:|---:|---|---|
| A1 | accepted runtime, `jitCacheUrl=off` equivalent | 37.802 | 56.72 | WindowsTerminal 30 | visible |
| B1 | guarded hot-`next1+next2` replay | 39.502 | 55.12 | WindowsTerminal 30 | visible |
| A2 | accepted runtime, `jitCacheUrl=off` equivalent | 36.753 | 61.83 | Notion 29; ChatGPT 1 | visible |

Exact endpoints:

- A1: 1,200 Presents / 31.744 s = 37.8024 FPS
- B1: 1,200 Presents / 30.378 s = 39.5023 FPS
- A2: 1,080 Presents / 29.385 s = 36.7534 FPS

The two controls differ by -2.775%, within the approximately 3% noise band.
Adjacent B effects are +4.497% and +7.479%; their median is **+5.988%**.
Both effects have the same sign and clear the noise band, so A-B-A is complete
and no A-B-A-B extension is required.

## 5. Default deployment and rollback

Changed page:

```text
tools/boxedwine_local/index_d3d9web_pathouse.html
```

Default replay is narrowly scoped:

- accepted runtime stem51 + no `jitCacheUrl`: load the combined ZIP;
- explicit `jitCacheUrl=off`: no replay;
- `jit-record=true`: do not inject the default cache;
- any other runtime stem: preserve the previous no-default behavior.

A parameter-free default smoke directly logged:

```text
AZROK_JIT_REPLAY_REGISTERED groups=134 entries=41625 patches=21626
```

It then reached the intact reference PatHouse scene and continued with zero
async-ring gaps, reorders, or errors.

## 6. Remaining performance gap

The accepted median uplift is about 6%, but the measured PatHouse result remains
below the 50 FPS target.  Further work must target a different remaining cost;
repeating broader unsafe direct-tail rewrites is not justified by this result.
