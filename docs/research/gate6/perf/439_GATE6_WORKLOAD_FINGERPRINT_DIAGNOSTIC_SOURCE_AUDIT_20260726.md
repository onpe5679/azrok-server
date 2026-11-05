# 439. Role-neutral workload-fingerprint diagnostic source audit

Date: 2026-07-26  
Status: **VERIFIED static source gate; runtime diagnostic remains NOT VERIFIED**

## Scope

437 is performance-inconclusive and 438 proves that existing lean exports do
not identify the guest workload. This card adds no Wasm/C++ build and no FPS
path. A URL-gated `workloadFingerprint=1` observer in
`index_d3d9web_pathouse.html` wraps only the existing
`D3D9WebRuntime.dispatchBatch` after exact replay registration. It parses the
already-delivered raw D3D batch records, retaining 120 terminal-Present batch
windows of command id/count/byte-count/order hash in a status dataset.

The observer is role-neutral: accepted and INT9A private replay are allowed;
the implementation never branches on stem, cache contents, or candidate mode.
Its output is an admission diagnostic only and must never be collected by, or
used as, a 30-second FPS leg.

## Fail-closed static checks

- Replay must already be registered, a nonempty non-`off` cache URL must be
  present, and `lean=1` is required before wrapper installation.
- Record, capture, cache-OFF, all private censuses, nosound, and known
  renderer/host profiling query modes are rejected by the diagnostic URL.
- The attached FPS sampler explicitly rejects any `workloadFingerprint` query,
  preventing diagnostic overhead from contaminating a performance row.
- Every raw record is bounds-checked as `[u32 length][record]`, requires a
  command record of at least four bytes, remaining-buffer containment, and a
  known command slot. A batch seals only when its final command is Present
  (`11`). Production transport flushes on Present and the async submitter
  requires terminal opcode 11, so this is the exact terminal-batch boundary.
- Host `dispatchBatch` success is `RESULT_OK=0x6001`, not zero. Static review
  caught an initial zero-success P0 before any browser run; the corrected
  wrapper commits only `0x6001` and records any other result as rejected.
- Snapshot readers must require `frames=120`, `invalidBatches=0`, and
  `rejectedBatches=0`; no incomplete or malformed window is admissible.

The function extraction compiles with Node, the host runtime syntax check
passes, and the static reviewer found no remaining P0 after the RESULT_OK and
replay/FPS-isolation repairs.

## Explicit limit

The FNV-style value covers command id, packet length, and ordering; it does
not hash command payload. It is therefore a **command-shape/workload proxy**,
not a cryptographic room, camera, map, or animation identity. Runtime must
first determine whether consecutive fresh accepted controls have a stable
diagnostic tuple. Only then can a future measurement contract decide whether
it is strong enough to admit another performance A-B-A(B).
