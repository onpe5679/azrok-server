# 413 -- Gate 6 logical-composite32 R2 offset witness and immutable record (2026-07-26)

## Status

**VERIFIED R2 private build, cache-OFF live-layout witness, and fresh raw
record.  Grouped transform/replay and FPS remain open.**

The first private build (R1) exported only the logical-composite ABI getter.
A direct dynamic audit found that a replay manifest would also need the live
`CPU::result` and `CPU::lazyFlagType` layout witnesses.  R1's raw record is
therefore preserved as historical evidence only and is **ineligible** for
transform or replay.

R2 exports all three required functions from the same isolated private target:

```text
wasm_jit_get_runtime_logic_composite32_abi_version
wasm_jit_get_cpu_result_offset
wasm_jit_get_cpu_lazy_flag_type_offset
```

The real build completed (only pre-existing source/Emscripten warnings) and
the target bytes staged to the private served stem matched the build bytes:

```text
JS   11a3eef5c01f2fbd7c1224f2f79069e37e811991bf0f4075d2d186c5090d6afb
Wasm 3652e93ab717c70b315a5894f72a0baa26ab2bb2f38c38aea38dda48f7691c2a
```

On the sole visible CDP page, R2 cache-OFF directly reported ABI `1` and live
offsets `result=108`, `lazyFlagType=328`, entered first JIT, and rendered at
1024x768.  Its final observed async-ring window was 120 submitted/120 reaped
with zero errors.  This is render integrity, not a timed FPS row.

The same R2 private URL then made a fresh record.  The page's own completion
state said `JIT record saved: 30061 blocks, 37840834 bytes`.  The immutable
copy and exact raw-manifest digest are:

```text
archive: profiles/azrok-jit-record-logiccomposite321-r2-raw.zip
archive SHA-256: 3533dfb2b2b6a18f029065e2dcdec3a14f6c25ccedcc68208dfd51a64f32f165
boxedwine-jit-manifest.json SHA-256 (raw ZIP entry bytes):
  a0f062874bc2b7005ad2ed47689f5e87c1977349eecc9d812b93a9489f62a901
```

The raw-entry digest is calculated from the ZIP entry bytes via the same
decoder as the transform pipeline.  A Git `sha256sum` pipe was rejected as
non-authoritative here because its Windows text-mode path changes newline
bytes; it yielded a different digest and correctly failed the pipeline's
exact-input gate.

Before transformation, the page replay gate was strengthened to require the
two layout exports and compare their live values with the grouped manifest
descriptor.  This closes the previously missing live-layout equality proof;
pre-transform replay remains fail-closed because all final archive pins are
still null.

The first transform invocation stopped before writing output because the raw
record does not serialize MT direct-stitch publication fields.  On the same
visible R2 cache-OFF/record runtime, the existing exported getters directly
reported `CPU::nextOp=740` and `DecodedOp::pfnJitCode=12`.  These are therefore
verified exact-runtime overrides for the grouped transform, not inherited
assumptions from another stem.

## Boundary

This record is private to
`boxedwine.upstreamjit64fn6inlineabi2logiccomposite321`.  No accepted,
parity, MOVSD, fixture, or census cache is changed or eligible.  No grouped
cache, replay-render proof, 30-second Present capture, or performance
adoption/rejection has occurred.

## Next gate

Transform only the immutable R2 raw archive with its exact raw-manifest
digest and the verified `108/328` layout values.  Pin the resulting archive
and grouped-manifest hashes, mutation-test the loader, and prove pinned
replay render before any A-B-A.
