# 409 -- Gate 6 logical-composite32 production extraction static audit (2026-07-26)

## Status

**VERIFIED static audit. Production implementation is authorized only as a
new private, fail-closed candidate; no build, cache, render, replay or FPS
sample has occurred.**

## Fixture is not the production implementation

The passing 408 fixture deliberately synchronizes dirty GP registers, uses
test-only `CPU` witness counters, admits solely from the runtime enum, and
invalidates the GP cache after its generated `if`.  Those choices are valid
for an oracle but must not be copied to a production path.

The production candidate must instead use a distinct
`BOXEDWINE_WASM_JIT_INLINE_RUNTIME_LOGIC_COMPOSITE32` macro and leave the
fixture macro/code/CPU layout untouched.  It may enter only when compile-time
`currentLazyFlags == FLAGS_NULL`, the condition is exactly
`{BE,NBE,L,NL,LE,NLE}`, and runtime `lazyFlagType` is exactly one of
`{FLAGS_OR32(6), FLAGS_AND32(15), FLAGS_XOR32(21), FLAGS_TEST32(42)}`.  TEST
currently decodes to AND32 (408); keeping TEST32 in the exact whitelist is
safe but is not an observed additional lane.

The candidate emits only the 408-proven `result.u32` formulas.  Every other
condition, compile-time state, width, enum and CFOF state reaches the
unchanged generic helper after the candidate block.

## GP-state boundary

The non-admitted branch may call its exact per-condition helper and read
`tmpReg` without a GP synchronization or GP-cache invalidation.  This is
bounded by direct source inspection: `wasmHelper_cond_*` reads lazy
flags/result/architectural flags and writes only `CPU::tmpReg`.  It matches
the existing runtime-Z/NZ fallback pattern.  Thus neither branch touches GP
architectural state and the generated join preserves the local GP cache.

This is intentionally different from the fixture's test-only host sync.  No
shared counter-parameterized emitter is allowed, because that could make a
production module depend on the fixture-only `CPU` layout.

## Required fail-closed identity

The candidate needs a module getter returning ABI 1 only under the new macro,
an exact manifest descriptor (kind, ABI, result/type offsets, exact four
types, six conditions, `FLAGS_NULL_ONLY`, helper fallback), and URL/page
mode separate from the census mode.  The loader must require that descriptor,
getter and current offset exports before guest start; accepted/candidate
runtime-cache cross-pairs and every missing/mutated field must reject.

It must use a new private stem and fresh cache-OFF record, transform, pins and
replay proof.  Census, fixture, accepted and previous candidate artifacts are
not reusable.  The production macro must compile-fail when combined with
tests, fixture, census/profile/helper/opcode/MOVSD/MOVSB/FISTP/ZNZ/SNS
candidates or censuses, sticky/eager/merge GP and IF-cache modes, threaded
body/tail ABI, parity or fallback stats.

## Route audit

**VERIFIED source route audit:** the private page can prove cache-OFF render
before replay by validating a dedicated `logicComposite32=1` mode/stem before
record/replay preparation, then requiring the new getter to return 1 during
runtime initialization.  `jitCacheUrl=off` returns before registration, so
that gate needs no cache artifact.

Replay needs a third explicit identity branch in both the page and cache
pipeline; the current generic private-identity validator intentionally accepts
only MRG and parity.  Its final identity must pin kind, stem, raw-manifest,
archive and grouped-manifest hashes and reject candidate/accepted cross-pairs
before registration.  The existing Present sampler has no appropriate role
yet and must not be changed until a pinned replay exists; cache-OFF render is
its preceding gate.

## Consequence

407 remains unchanged: the available 0.32755% cross-diagnostic entry-rate
proxy is **not** an execution-time Amdahl bound, so it cannot close this card
before a safe private candidate exists.  408 has closed semantic fixture
coverage; 409 closes only the extraction design.  The next gate is source and
loader implementation followed by static regression before any build.
