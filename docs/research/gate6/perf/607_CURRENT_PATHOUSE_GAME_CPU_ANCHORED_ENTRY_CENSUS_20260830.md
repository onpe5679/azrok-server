# 607 — Current PatHouse game-CPU anchored generated-entry census

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED visual/browser:** both launch and measurement before/after pairs
  show the actual PatHouse room for the complete intervals.
- **VERIFIED CPU ownership:** the first CPU executing Ghidra-confirmed
  `Azrok.exe` block `v5-0059207c-3c3f909d` was captured once with atomic
  compare-exchange as `0x27A6F1A0`.  All 30,550 entry counters then required
  function parameter 0 to equal that exact CPU pointer.
- **VERIFIED dynamic:** the accepted 20.008940-second window observed
  20,242,521 generated entries on that one CPU, across 2,471 nonzero keys:
  1,011,673.83 entries/s and 42,977.75 entries/Present.
- **VERIFIED distribution:** the top 1 / 10 / 100 keys account for 2.1700% /
  16.4418% / 58.7325% of the game-CPU entry count.
- **VERIFIED current hot family:** aggregate leaders `10635F1F`, `10627B70`,
  `10635FAA`, `7BDD1130`, and the equal-count `104F0Dxx/10627A60/106791xx`
  chain remain leaders after unrelated CPUs are removed.  They are on the
  frame-producing game CPU, not merely background Wine workers.
- **VERIFIED anchor cadence:** `0059207C` recorded 141,298 entries for 471
  Presents, almost exactly 300 entries/Present, matching the decompiled
  300-record loop.  Its latch `005920AF` recorded 141,297.
- **NOT VERIFIED:** the mapped module/file and original bytes behind the
  `10635xxx` leaders.  A read-only KProcess mapping resolver is the next gate;
  numeric EIP alone is still insufficient for semantic replacement.

## Anchored cache/runtime contract

The snapshot-only runtime is:

```text
stem   boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2anchoredfullentrycensus1
JS     331289 bytes
SHA256 6b1f8fa245c228e3a559d995d7081fe6a17a6b07e117a446e751d29cc7995569
Wasm   3056624 bytes
SHA256 303e65ebdd637222f593951052eb350ba4f01348f048ee5a909fd6819e8275ee
```

Its reserve ABI is:

```text
owner CPU word 60 @ 12968392
counter pointer 62 @ 12968400
counter count   63 @ 12968404
reloc map          @ 12968408 / 262144
```

The immutable cache is:

```text
name   azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-anchoredfullentrycensus1.zip
bytes  4956516
SHA256 feaf3b1f7c4652dde73676b11db7b39c6e7396d3b3587c736f4dbc5b3b4328dd
anchor v5-0059207c-3c3f909d / global index 29858
```

Every generated body first checks the counter pointer.  When inactive it does
not capture an owner and performs no counter write.  With the buffer active,
the anchor loads word 60 and performs `cmpxchg(0,cpu)` only while it remains
zero.  Every entry then requires nonzero owner and `cpu == owner` before its
atomic increment.  Internal direct and generic indirect tails enter the same
instrumented body, so filtering does not lose those paths.

The candidate changes all 94 groups, appends one i32 local without shifting
existing indices, adds 1,586,995 uncompressed Wasm bytes, and revalidates all
28,944 relocation patch offsets.  A two-CPU fixture proves stable first-owner
capture, owner-only exported/direct/indirect counting, pointer-zero no-write,
and no ownership theft.  Artifact regeneration is byte exact and all 94 Wasm
modules validate.

## Visual and timing acceptance

The fresh launch on CDP 9349 used 180 seconds post-readiness settle and 15
seconds warmup.  Both launch screenshots show PatHouse.  Its diagnostic timing
was 704 Presents / 30.011127 s = 23.4580 FPS.

The attached owner-filter window captured another PatHouse before/after pair
and measured 471 Presents / 20.008940 s = 23.5395 FPS.  The FPS is only a live
timing witness; the extra guard/atomic instrumentation excludes candidate vs
control performance comparison.

The owner word, getter, configured pointer/count, anchor counter, and cleanup
state all agreed.  Pointer/count publication was cleared before a 100-ms
quiescence window; the owner was reset and the dynamic buffer freed only after
the snapshot.

## Current game-CPU ranking

| Rank | Hits | Hits/Present | EIP | Ops / bytes |
|---:|---:|---:|---|---:|
| 1 | 439,255 | 932.60 | `10635F1F` | 167 / 520 |
| 2 | 425,011 | 902.36 | `10627B70` | 2 / 4 |
| 3 | 407,129 | 864.39 | `10635FAA` | 118 / 381 |
| 4 | 354,543 | 752.75 | `7BDD1130` | 20 / 36 |
| 5 | 286,960 | 609.26 | `1059200C` | 2 / 4 |
| 6–13 | 283,067 each | 600.99 | `104F0DB0/DBD/DF8/E11`, `10627A60`, `10679184/18D/1A1` | mixed |
| 16 | 141,298 | 300.00 | `0059207C` | 22 / 63 |
| 17 | 141,297 | 299.99 | `005920AF` | 1 / 2 |

`10635F1F` spans 520 guest bytes with 167 decoded ops and 22 relocation
slots.  `10635FAA` begins inside that guest range and independently records
407,129 entries.  This overlap and the high equal-count chain are strong
regional-AOT signals, but their module/semantic identity and exact side-exit
ratios remain unproved.

## Verified Azrok.exe families on the same CPU

### 300-record scan

`FUN_00592060` scans 300 records at stride `0xA9`, testing one byte at
`base+0x9360+i*0xA9`.  Entry and latch counts reproduce the loop bound almost
exactly per Present.  This is safe as a current-game anchor and a possible
small fused loop; it is not large enough by itself to justify an
"epoch-making" claim.

### Locale / lead-byte chain

The owner-filtered counts remain high:

| Family | Hits |
|---|---:|
| `004DC546 -> 006512FE` LocaleUpdate | 140,066 each |
| `004DB9B6 -> 00667CB0/CC1/CE4` lead-byte path | 132,478 each |
| `00651370` LocaleUpdate continuation | 132,478 |

This corresponds to roughly 281–297 invocations per Present.  A guarded
locale/CP949 fast path could be reusable across MSVC-era games, but it must be
judged against the larger `10635xxx` family after the latter is mapped.

## Next gate

Build a resolver-only sibling runtime with the same owner/filter ABI and three
read-only exports:

1. owner process identity (`pid`, command line, executable, memory pointer);
2. `KProcess::getModuleName/getModuleEip` for current hot EIPs;
3. up to 256 original guest bytes after `KMemory::canRead` validation.

The paired cache remains anchored to `0059207C`.  Mapping evidence decides
whether the first real candidate is an engine region, a Wine/codec kernel, or
the generic MSVC locale path.

## Artifacts

- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/boxedwine-wasm-jit-cache-anchored-full-entry-census.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-anchored-full-entry-census-cache.mjs`
- `tools/boxedwine_local/profiles/azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-anchoredfullentrycensus1.zip`
- `artifacts/performance/regional_anchored_full_entry_launch_present_20260830.csv`
- `artifacts/performance/20260829T181636868Z_edge_default_cdp9349_pid85312.before.png`
- `artifacts/performance/20260829T181636868Z_edge_default_cdp9349_pid85312.after.png`
- `artifacts/performance/regional_anchored_full_entry_actual_pathouse_20260830.csv`
- `artifacts/performance/regional_anchored_full_entry_actual_pathouse_20260830.raw.json`
- `artifacts/performance/regional_anchored_full_entry_actual_pathouse_20260830.top.csv`
- `artifacts/performance/regional_anchored_full_entry_actual_pathouse_20260830.visual-review.csv`
- `artifacts/performance/anchored_full_entry_20260830_032226_before.png`
- `artifacts/performance/anchored_full_entry_20260830_032226_after.png`

