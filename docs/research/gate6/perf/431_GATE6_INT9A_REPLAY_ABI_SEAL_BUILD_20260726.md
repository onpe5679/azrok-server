# 431. INT 0x9A specialized helper: replay ABI seal and rebuilt artifact

Date: 2026-07-26  
Status: **VERIFIED static/build/stage/HTTP identity; new-byte cache-OFF render NOT VERIFIED**

## Why 429 is not enough for replay

429 rendered the earlier private artifact.  A replayable cache also needs a runtime-owned ABI witness and a manifest identity that ties the grouped archive to exactly one raw record.  The prior counter getter alone did not give the loader a versioned runtime contract.  This card adds that contract rather than allowing replay from an unpinned private ZIP.

## Fail-closed replay contract

The private runtime now exports `wasmJitInt9ASpecializedGetAbiVersion() == 1` alongside the existing three-counter getter.  The page requires both exports and ABI 1 before running the private guest.

The grouped-cache pipeline has two new paired options:

```text
--int9a-specialized-runtime-stem boxedwine.upstreamjit64fn6inlineabi2int9aspecialized1
--int9a-specialized-raw-manifest-sha256 <64 lowercase hex>
```

They are mutually exclusive with MRG/parity/logical-composite identities.  They reject any input whose raw manifest does not contain exactly:

```json
{"kind":"int9a-specialized","stem":"boxedwine.upstreamjit64fn6inlineabi2int9aspecialized1","abi":1}
```

The grouped manifest will carry `azrok-int9a-specialized-v1`, the exact raw-manifest SHA and required ABI 1.  Replay is locked to `/profiles/azrok-jit-grouped-int9aspecialized1.zip`; before a fresh transform writes the three SHA pins, the loader deliberately rejects it as `int9a-specialized-pins-unset`.  After transformation it must verify raw-manifest, archive and grouped-manifest SHA-256 before module registration, then recheck runtime ABI 1 and both exports.

## Rebuild and served bytes

The exact private target was rebuilt after adding the ABI getter.  The first invocation failed before compilation because this agent shell lacked Git's `usr/bin` (`grep` not found); rerunning with that utility path completed successfully with only pre-existing compiler warnings.  `make -q` is clean.

| artifact | SHA-256 | result |
|---|---|---|
| build/staged JS | `D72C4DB519C86DD7D0887B5497EBCC2477FE6311BFC5334C91E41F8CADCCE278` | exact match |
| build/staged Wasm | `37217EB72506D7984103C0C63067EBE0AA04BE50350CF810C031925D7389C159` | exact match; magic `00 61 73 6D` |
| HTTP JS | same, 327,152 bytes | exact served match |
| HTTP Wasm | same, 3,049,359 bytes | exact served match |

The no-store served page contains the replay gate and ABI getter requirement; both executable inline scripts parse.  The currently live 8765 process still predates the separate upload-route source change from 430, so this does not authorize record yet.

## Decision

The new artifact is statically sealed for a future private record/replay.  Because its bytes differ from 429, it must first repeat a fresh cache-OFF real-game render-integrity gate with ABI getter 1 before any record.  Then, only after the user-owned 8765 reload from 430 is directly verified, may the private record/transform/replay sequence start.  No replay or FPS result is claimed.
