# 300 — Runtime-lazy Z/NZ exact helper-counter diagnostic

## Status

**VERIFIED static/build/browser-record/replay; helper fallback gate PASSED.**

This is a diagnostic-only artifact.  It is never a performance sample and cannot
change the accepted `boxedwine.upstreamjit64fn6inlineabi2` path.

## Purpose

Documents 296--299 established that the release Z/NZ candidate is loader-valid,
replays a reference-correct PatHouse, and has no exact measurement of the two
remaining fallback helpers.  The diagnostic answers only this question after a
fresh replay:

```
did wasmHelper_cond_Z (fn16) or wasmHelper_cond_NZ (fn17) execute?
```

## Static and build evidence — VERIFIED

- `BOXEDWINE_WASM_JIT_RUNTIME_ZNZ_COUNTERS` is a separate compile flag.  It
  increments relaxed atomic `U64` counters at the actual entry of
  `wasmHelper_cond_Z` (fn16) and `wasmHelper_cond_NZ` (fn17), before their
  existing helper body.
- The exported snapshot is two process-lifetime counters at byte offsets 0 and
  8 (16 bytes total).  The page reads the four `u32` words as `BigInt`; no
  JavaScript `Number` truncation is permitted.
- Diagnostic stem assets are
  `boxedwine.upstreamjit68runtimeznzdiag1.js` SHA-256
  `7771600257699BD778BF16885CAE53408D4921196806BDA6972EB92DA9ED2FE7` and
  `boxedwine.upstreamjit68runtimeznzdiag1.wasm` SHA-256
  `FE0F12BD6900DB9D2BD4473966CC89CDE4EDBD0FA1762EC02D6EE3FA0BE2FD86`.
- The diagnostic cache schema requires
  `cpu-runtime-lazy-znz-helper-counters-v1`, ABI 1, snapshot 16 bytes, helper
  indices `[16,17]`, and `exact-host-helper-invocations-since-process-start`.
  Page loading rejects either counter manifest/runtime direction mismatch and
  missing counter exports before group registration.
- `verify-runtime-lazy-znz-loader-gate.mjs` passed 20 cases with 12 required
  static fragments.

## Fresh diagnostic record — VERIFIED

The dedicated cache-OFF diagnostic stem was visibly driven through the normal
`512,384,140 ms` and `90,722,140 ms` selection pulses.  It produced continuous
1024x768 output and the record action saved **34,311** blocks,
**45,392,801 bytes**.  The observed async-ring windows were ordered with zero
errors and zero gaps/reorders; this is an integrity observation, not an FPS
measurement.

The resulting raw is isolated as
`profiles/azrok-jit-record-runtimeznzdiag1.zip`:

- 45,392,801 bytes
- SHA-256 `82594C14FD15688754BF07EFEA045CA42C7A912702F8EDD7B6E095DF8B044E7E`

Immediately after isolation, the canonical raw was restored from its pre-diag
backup.  Both the restored canonical raw and backup are 46,217,305 bytes with
SHA-256 `0734050303F25C0BA7B9927B46A1475A428CD4E219370D58AA324F635DB67C31`.

## Diagnostic replay and counter result — VERIFIED

The isolated pipeline completed with 34,311/34,311 input modules optimized into
110 groups and 28,041 patches.  Output is
`profiles/azrok-jit-grouped-commonfast64-depthlocal-inlinefetch-runtimeznzdiag1.zip`:

- 5,506,760 bytes
- SHA-256 `54DFC4BCCFA29865A740B35B1D928642976C61C6A86F5CE98A4CA68E5F11266B`
- all 110 grouped Wasm payloads passed `WebAssembly.validate`

Visible diagnostic replay registered exactly 110 groups, 34,311 entries and
28,041 patches.  Its live layout gate was `1:96:108:328:329:64`, counter ABI
was 1, and counter snapshots were `0:0` immediately after registration, after
both normal selection pulses, and again after a separate uninterrupted visible
PatHouse interval.  The latter retained continuous ordered 120-Present ring
windows with zero gap/reorder/error reports.  Thus neither fn16 nor fn17 was
entered in the exercised fresh replay workload.

This clears the required helper-fallback proof for the *uninstrumented* Z/NZ
release candidate only.  The diagnostic artifact remains excluded from all FPS
measurement.  The next operation is an isolated release-cache A-B-A against
the accepted ABI2 stem; parity and diagnostic code must not be mixed into that
comparison.
