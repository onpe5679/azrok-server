# 318 — `Movsd` `fn_8` fallback shape census

Status: **VERIFIED static/build/browser cache-OFF shape census; direct candidate not yet opened**

## Why this card exists

317 measured string `Movsd` (A5, enum 402) as 2,337,560 of 6,965,027 exact
`fn_8` entries in 22.337 seconds (33.56%).  This is coverage, not time or FPS.

## Direct static boundary

`dynamic_movsd_op` already emits non-REP 16/32-bit `movs` and flat 32-bit REP
`movsr`.  The remaining interpreter fallback is exactly:

1. EA16 with either REP prefix;
2. EA32 REP whose ES or source-base has the compile-time segment-address path;
3. EA32 flat REP `runCount==0`, which deliberately creates the traced stub and
   falls back as part of cache policy.

DF is not a fallback discriminator: both generated paths retain DF0/DF1
loops.  Page crossing and memory faults use memory helpers/write checks, not
this fallback.  The existing `movsd32r` helper is unused by emitted Wasm and
cannot replace `fn_8`: it lacks NormalCPU tracing, EIP/NEXT, decoded-op and
exception/SMC semantics.

## Exact private EOC2 design

The MT-only, profile/EOC-mutually-exclusive diagnostic has 16 exact buckets
over `{REP, EA16, segAddressPath, DF}`.  It records requested dwords separately
(single=1; REP=CX for EA16 or ECX for EA32) before interpreter execution.  The
snapshot is 35 U64 / 280 bytes:

```
fn8Total, otherOpcode, invalidTag, calls[16], requestedDwords[16]
```

Its mandatory invariant is `fn8Total == otherOpcode + invalidTag + sum(calls)`.
`segAddressPath` means the compile-time `hasSetSeg` address path, not proof
that the runtime segment base is nonzero. Requested work is pre-call request,
not completed work after a fault/COW path.

The reader must fail closed unless its distinct stem and exactly
`movsdShapeCensus=1`, `jitCacheUrl=off`, no `jit-record`, no old EOC flag and
no present capture are present.  It may never record/replay or produce FPS.

## Browser measurement (private diagnostic only)

The repaired private reader was started cache-OFF with its exact distinct stem,
no record/replay, no old EOC flag, and no Present capture.  The loader published
ABI `1` and bucket count `16` before the guest start.  The visible 1024x768
PatHouse scene then completed normally with no browser warning/error.  The
refresh control was initially appended to the hidden pre-start control row;
that was repaired to the existing visible diagnostic-controls row and the
measurement was restarted from a fresh tab.  The refresh action was a visible
page control, not a console call.

The two exact snapshots, taken around a stable visible-room interval (nominal
25 seconds), were:

```
S0 17026505:12956551:0:0:73224:0:0:0:3996730:0:0:0:0:0:0:0:0:0:0:0:588932:0:0:0:103791590:0:0:0:0:0:0:0:0:0:0
S1 24929393:18193133:0:0:82442:0:0:0:6653818:0:0:0:0:0:0:0:0:0:0:0:661167:0:0:0:222460124:0:0:0:0:0:0:0:0:0:0
Δ  7902888:5236582:0:0:9218:0:0:0:2657088:0:0:0:0:0:0:0:0:0:0:0:72235:0:0:0:118668534:0:0:0:0:0:0:0:0:0:0
```

The `fn_8` partition held exactly: `7,902,888 = 5,236,582 other opcode + 0
invalid tag + 2,666,306 Movsd buckets`.  Only two of the sixteen shapes were
nonzero:

| bucket | shape | calls | requested dwords |
|---:|---|---:|---:|
| 1 | REP, EA32, no compile-time segment-address path, DF0 | 9,218 | 72,235 |
| 5 | REP, EA32, compile-time segment-address path, DF0 | 2,657,088 | 118,668,534 |

Thus bucket 5 is 99.654% of observed `Movsd` fallback calls and 99.939% of the
recorded pre-call requested dwords.  It only means the decoded ES or source-base
address uses `hasSetSeg`; it does **not** establish a nonzero runtime segment
base, completed copy length, CPU time, or FPS impact.  DF1, EA16 and non-REP
forms were zero in this interval.

## Status

- **VERIFIED static:** all fallback forms, NormalCPU handlers and dedicated
  helper non-overlap above.
- **VERIFIED build:** short-path `Build/MOC1` completed at low priority with
  only existing compiler warnings; private JS/Wasm hashes are
  `B6D69636D0D78330F18FD1F26A15A0F5E8D064FC2D7933CE1C88BA82747B376E` and
  `52CA724CB8E36A09A6CB76806A47D82BC3C04F77E4BD519800FB314E8F7B6F00`.
- **VERIFIED loader repair:** The reader now publishes ABI/count immediately,
  guards duplicate preparation, and exposes its refresh through a visible
  diagnostic control.  The earlier hidden-row placement was fixed before the
  accepted run.
- **VERIFIED browser coverage:** The exact visible cache-OFF interval and
  partition above pass.  This mutex/layout-changing diagnostic remains
  forbidden from replay and FPS use.
- **NOT VERIFIED:** Bucket 5's runtime segment identity/base and a semantics-
  preserving generated-Wasm route.  Open that as a separate card; do not infer
  that `hasSetSeg` is a removable runtime no-op.
