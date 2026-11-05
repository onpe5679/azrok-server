# 430. INT 0x9A specialized helper: private record identity route

Date: 2026-07-26  
Status: **VERIFIED static/private serving identity; live record/replay/FPS NOT VERIFIED**

## Scope

429 closed only the private cache-OFF real-game render gate.  A fresh record must never overwrite the active generic raw archive (`profiles/azrok-jit-record-raw.zip`) or become replayable under a different runtime stem.  This card adds the minimum separate identity route before any record attempt.

## Verified static and served-page contract

When `int9aSpecialized=1`, the PatHouse page now:

1. requires both `boxedwineStem` and `runtimeStem` to equal `boxedwine.upstreamjit64fn6inlineabi2int9aspecialized1`;
2. rejects either a private stem without the flag or the flag without both stems;
3. permits only cache-OFF record/no-replay (and no capture/census/nosound conflict);
4. writes a private manifest declaration:

   ```json
   {"kind":"int9a-specialized","stem":"boxedwine.upstreamjit64fn6inlineabi2int9aspecialized1","abi":1}
   ```

5. attaches `X-Azrok-Jit-Record-Name: azrok-jit-record-int9aspecialized1` to the export POST.

The HTTP page response was directly fetched as `200`, `Cache-Control: no-store`, 109,518 bytes and contains all three guards/header strings.  The private staged JS fetched as `200`, 327,010 bytes, SHA-256 `35C3DE289BFA9D580D1A4284B328A8360E5C9E315CAE7558DF49EFBC8FA1B3ED`, exactly matching the build output.  All executable inline page scripts parse with Node; the import map was separately excluded as JSON.

`server.py` accepts only `azrok-jit-record-raw` and `azrok-jit-record-int9aspecialized1` and maps the latter atomically to:

```text
profiles/azrok-jit-record-int9aspecialized1.zip
```

The Python AST parses successfully.  Any other record name is a 400 rejection.  This is a fail-closed upload identity boundary, not evidence that the running process has loaded it.

## Running-service boundary

At this audit the live 8765 Python process is PID 66804, started 2026-07-25 06:03:15, while `server.py` was changed 2026-07-26 05:48:42.  Its bytecode timestamp is 2026-07-23.  It therefore predates the new header allowlist and cannot be used to produce the private record.  A direct attempt to stop that child was access-denied; the detached user-owned service loop remains intact.

No POST was sent: under the pre-change process it could silently write the generic raw path.  This is an intentional safety hold, not a card rejection or a browser/service outage.  A user-owned 8765 service-loop restart (or an equivalent verified reload) is required before the record leg.  After reload, the first record must directly prove the returned private path, archive manifest/stem, and an unchanged generic raw archive before any transform/replay action.

## Decision

Private source/page identity is ready and generic raw is protected at the source level.  Live private record, transform, replay render and any A-B-A performance decision remain **NOT VERIFIED**.
