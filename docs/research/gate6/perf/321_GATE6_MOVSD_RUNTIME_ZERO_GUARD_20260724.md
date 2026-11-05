# 321 Runtime-zero-guarded flat MOVSD route

Status: **VERIFIED static/dynamic design; implementation NOT VERIFIED**

320 measured every B5 entry as DS source-only with live ES and DS bases both
zero. The proposed narrow candidate is Wasm-only and macro-gated:

    EA32 REP hasSetSeg-route:
      if runCount == 0: keep existing emulate/traced-stub policy
      load CPU.seg[ES].address and CPU.seg[op->base].address each invocation
      if either nonzero: existing emulateSingleOp
      else: existing movsr(b32,4,b32)

This must not reinterpret sticky process hasSetSeg as a live address. The zero
arm reuses movsr's REP/DF/ESI/EDI/ECX loop, partial failure sync and existing
write/SMC paths. The nonzero arm keeps exact fn8 EIP/NEXT/interpreter semantics.
Direct movsd32r helper replacement remains rejected.

The guard must use the Wasm structured branch so dirty GP state is safely
flushed/invalidated at arm boundaries; no manual merge. Required regression
matrix covers B5 zero/nonzero flips, ES/source/both route causes, base=ES/DS,
runCount cold/warm, DF, ECX including MOC3-overflow class, overlap,
cross-page/read-write partial fault, CodePage SMC bailout and post-join
GP/EIP/nextOp. After static regression, only a private cache-OFF no-FPS
guard-counter integrity build may run before candidate cache/replay/A-B-A.
