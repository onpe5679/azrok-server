# Gate 6 MRGF3 direct browser closure (2026-07-25)

Status: **VERIFIED direct browser runtime / static provenance; unpublished**

## Direct evidence

This result was read directly, not inferred from a report. `http://127.0.0.1:9222/json/list` exposed exactly one `page` target, ID `E57B4901B2A146CCF5D20DCF45009B44`, at the exact private URL:

`http://127.0.0.1:8765/bwujit_threaded_abi/project/emscripten/Build/MRGF3/boxedwine.html?388&1&1`

Using `CdpPresent.psm1`'s `Get-CdpPageTarget`, `Connect-Cdp`, and `Invoke-CdpCommand`, filtered to the returned `ClientWebSocket`, a read-only `Runtime.evaluate` fetched `document.querySelector('textarea#output').value`. The page was `visible`; no CDP Page command, navigation, tab close, or browser launch was issued. The textarea directly contained:

```text
Running 1 Test tests with 1 threads starting at 388
[WASM JIT] first JIT block executed, tableIdx: 8178
[WASM JIT] direct chain ABI depthOffset=1660 bailoutOffset=132
Movsd runtime-zero partial-fault MRG DF0 frame-sig=11/2/F000A000 eip=00000000 flags=000008D7 ecx=00000001 esi=F0008004 edi=F000A000 throw=1 reached=1 handler=1 bailout=0
Movsd runtime-zero partial-fault MRG DF0 generated-slow-write=1
Movsd runtime-zero partial-fault MRG DF1 frame-sig=11/2/F000AFFC eip=00000000 flags=00000CD7 ecx=00000001 esi=F0008000 edi=F000AFFC throw=1 reached=1 handler=1 bailout=0
Movsd runtime-zero partial-fault MRG DF1 generated-slow-write=1
Movsd runtime-zero source-only same-entry partial-fault matrix ... OK
Movsd runtime-zero source-only same-entry page-cross matrix ... OK
Movsd runtime-zero ECX boundary matrix ... OK
Test Movsd runtime-zero guard ... OK
0 tests FAILED in 0s
```

Therefore **VERIFIED:** the MRGF3 candidate, not MRGF2, executed entry 388; both DF partial-fault rows retained saved EIP `0` (not `2`), reached and ran the handler, had no bailout, and used exactly one generated scalar slow write. The source-only same-entry partial-fault, page-cross, and ECX matrices also passed in that same direct run.

## Fresh-path/provenance boundary

The served MRGF3 artifacts remain the isolated 24-Jul build: `boxedwine.wasm` is 2,436,113 bytes, SHA-256 `B3A75FEB32A6D21B7757A195E5A96B29B4635DB02F753D81824FB69363699EB4`; JS SHA-256 is `5D00FBD483749FBC01EBED62CEDD9961AE6FA9F657B013498EFC32BFEB949869`. Their timestamps are 18:14:45--18:14:49. The direct browser launch used a new isolated profile; its 8765 requests returned HTML/JS/Wasm 200 at 05:38:19--20, so the witness did not rely on a prior HTTP cache entry.

This is a private functional fixture, not a 1024x768 PatHouse measurement. The observed shell canvas was 300x150, so it provides no FPS evidence.

## Consequence and remaining MOVSD order

This closes only 324's MRGF3 browser gate. It does not publish MRG1, MRG2, cache/replay, or FPS work. Per 323, the next MOVSD-first gate is a separate macro-gated warmed compiled SMC invalidation/bailout and re-decode fixture; only after that row and the distinct EA16/worker-table scope decisions may a private MRG2 counter diagnostic open. MOVSB/MBS1 remains independent and deferred: MRGF3's MOVSD proof is not MOVSB coverage evidence.
