# 352 Gate 6 MOVSD MRG raw record and replay identity gate

## Status

**VERIFIED browser record/filesystem/static audit; replay BLOCKED fail-closed.
No grouped cache, replay or FPS measurement was produced.**

## Private raw record

The single existing CDP tab was navigated to the already cache-off-rendered
MRG1 stem in explicit record mode. After the normal selection pulses it
reached the live 1024x768 scene. `wasm_jit_mt_prepare_export()` then directly
reported 35,762 blocks and matching metadata before the page-owned record save
completed with 35,804 entries / 46,869,040 bytes. This is a record artifact,
not a timing sample.

The upload endpoint reused the generic `azrok-jit-record-raw.zip` name. That
temporarily replaced the known six-short R2 census alias. The new bytes were
first copied to the immutable name below, then the generic alias was restored
from the retained R2 census source and verified byte-for-byte:

| artifact | bytes | SHA-256 |
| --- | ---: | --- |
| `azrok-jit-record-movsdruntimezero1-20260725-092900.zip` | 46,869,040 | `7171DAD68AF1A1EB6D5EE32B164E5AA25A6CBDDE8139FE88C52531ED7CAD885B` |
| restored generic R2 alias | 50,714,251 | `6BD19F44148B8BE19BA51F6C6AB4CDAB011FF02350A41F478F3221729F304AFF` |

Thus 308/325's blocked R2 evidence was preserved; the new MRG raw is never
to be written through that generic name again.

## Static replay boundary

The MRG raw has exactly 35,804 `v5` modules, each with one defined function
and one code body. It is a legacy wrapper-only corpus: no dual entry exists,
and MRG1 itself uses the ABI2 legacy export set with only
`BOXEDWINE_WASM_JIT_MOVSD_RUNTIME_ZERO_GUARD` added. Its recorded runtime
fields are block-instruction/yield/direct-depth/bailout `624/628/1660/132`;
it does not carry `CPU::nextOp` or `DecodedOp::pfnJitCode` values.

The ordinary MT direct pipeline correctly rejected this raw because those
direct-tail layout fields are absent. A short retry supplied live getter
values, but static audit established that this would make an identity-free
legacy direct cache: the existing legacy loader accepts it as `legacy-cache`
and cannot distinguish MRG1 from accepted ABI2. The process was stopped before
any output archive existed. Do not resume this override route.

`--no-direct-calls` can make a legacy grouped artifact without dual-entry
mixing, but it is still unsafe to publish until a candidate-only identity gate
is present. Required P0: a dedicated MRG1 runtime/stem identity and a
manifest-SHA binding that rejects this archive on the accepted ABI2 URL before
any registration. Only after that static gate, a fresh no-direct transformation,
cache-off/replay render integrity and then A-B-A may be considered.
