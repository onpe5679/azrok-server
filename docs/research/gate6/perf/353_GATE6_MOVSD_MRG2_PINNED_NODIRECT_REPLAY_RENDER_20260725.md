# 353 — MOVSD MRG2: pinned no-direct replay and render integrity (2026-07-25)

## Scope

This closes the identity/replay-render gate left BLOCKED by 352. It is not a
performance result and does not reopen dual-entry R2, parity, Z/NZ, MBS1, or
PGO work.

## VERIFIED — isolated runtime and raw record

The first attempted product directory name `Build/MRG2` collided with the
already VERIFIED cross-worker fixture directory (350). Its original
2,446,276-byte wasm was restored before continuing; the product build was
renamed to `Build/MRGR2`. The product MRG2 stem is
`boxedwine.upstreamjit64fn6inlineabi2movsdruntimezero2`; its staged JS/Wasm
does not overwrite MRG1 or accepted ABI2.

The sole CDP tab was moved (no new tab) to this stem with `jitCacheUrl=off`
and `jit-record=true`. It directly reached live PatHouse after the normal two
input pulses. The output shows first JIT block, the established direct-chain
layout `depthOffset=1660 bailoutOffset=132`, D3D9 FFP initialization, and
continuous Present windows. The new immutable raw artifact is:

| artifact | entries | bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `azrok-jit-record-movsdruntimezero2-20260725-095210.zip` | 30,636 | 39,216,871 | `77301AF4C6DEEF30BDE8DA2A9E14A7CF3E2B750A5F6D30450DB29FC8520BD58E` |

Its uncompressed raw manifest is 14,443,260 bytes with SHA-256
`888d091828d93842caafaf7226ef2c5cfae1791a653faf85678597275ab972cd`.
The upload's mutable generic alias was immediately restored to the preserved
R2 source (`6BD19F...4AFF`).

## VERIFIED — fail-closed private identity

Legacy v2 cannot self-identify an MRG wrapper corpus. The no-direct pipeline
therefore accepts only a paired private stem plus exact raw-manifest SHA, and
writes this structured identity into the grouped manifest:

```json
{"kind":"azrok-mrg1-movsd-runtime-zero-v1","runtimeStem":"boxedwine.upstreamjit64fn6inlineabi2movsdruntimezero2","rawManifestSha256":"888d...972cd","requiredGuardAbiVersion":1}
```

The page accepts the identity only on its exact stem and URL, with three
independent pins before registration: raw manifest SHA, whole archive SHA,
and uncompressed grouped-manifest SHA. It also requires the live private
guard getter to return 1. Any non-MRG stem carrying private identity, generic
URL, wrong SHA, missing identity, or missing/zero getter rejects. The ordinary
identity-less accepted ABI2 legacy path remains `not-mrg`.

`verify-mrg-replay-identity-gate.mjs` passed 11 cases (including wrong raw,
archive, grouped-manifest, and runtime ABI rows); the existing pair loader
gate passed 12 cases. The live MRG2 guard export was directly observed as a
function and returned 1 after startup.

## VERIFIED — no-direct transform and browser replay render

The pipeline used `--no-direct-calls` with Binaryen and the paired raw SHA.
It produced 95 groups from all 30,636 modules, rewrote zero tail sites, and
emitted legacy one-token publication metadata (`pfnJitCodeOffset=0`,
`tokenWords=1`) without requiring unavailable direct-tail offsets.

| artifact | bytes | SHA-256 |
| --- | ---: | --- |
| `azrok-jit-grouped-movsdruntimezero2.zip` | 4,446,291 | `1da2727d97d01e80a74a6d6a4abd2e9df3c33304a4994ca4cf20d5dd57e8e1c2` |

The grouped manifest is 10,250,489 bytes, SHA-256
`732c90260f71bda86dd8cb7becdb0a00d5c9fcaca344d50110b25a047d50d3c4`.

On the sole visible CDP tab, the exact pinned replay URL registered
`95 groups, 30636 blocks`; the live guard was 1. After the same two pulses,
direct D3D9Web Present count reached 1,609 with no registration/replay error.
This is a replay render-integrity proof, not an FPS sample.

## Status

MRG no-direct replay is now VERIFIED and isolated from accepted ABI2. The
candidate still needs the prescribed visible 30-second A-B-A performance
measurement before any performance verdict. Cache/build CPU was inactive when
that future measurement may start.
