# 614 — Current PatHouse NtCurrentTeb selective original-region reject

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED static/build:** the selective cache redirects only 17 of the 39
  dispatcher sites in the ten-entry `NtCurrentTeb -> pthread_getspecific`
  chain: static-normal 9 plus all 8 sites in the four dynamic-normal source
  functions. The other 22 static side exits keep the original dispatcher.
- **VERIFIED static/build:** 94 groups, 30,550 registered original exports,
  9 internal routers, 9 region publication patches and 28,932 total patches
  validate. The 93 non-host groups are byte-identical to control; the host
  differs at exactly 17 dispatcher-to-router callee ULEBs.
- **VERIFIED visual/browser:** all ten before/after screenshots in the fresh
  A-B-A-B-A run visibly show the actual PatHouse room: the player Azron,
  orange rug, furniture, left status HUD and right clock are present. The
  empty `캐릭터를 생성해주세요` labels are room-HUD slots, not a character
  selection screen.
- **VERIFIED dynamic:** control A measured 30.5080 / 29.0847 / 28.1727 FPS;
  selective B measured 28.0624 / 27.5712 FPS. Condition means were
  29.255133 and 27.816800 FPS, or **-4.9165%** for B.
- **VERIFIED dynamic:** the four adjacent B/A effects were -8.0163%,
  -3.5149%, -5.2038% and -2.1350%; median **-4.3593%**. Interpolating each B
  against its two neighboring controls gives -5.8193% and -3.6938%, mean
  **-4.7566%**.
- **VERIFIED drift boundary:** A drifted -7.6547% from A1 to A3, exceeding the
  usual 3% stability gate; B drifted -1.7504%. Therefore the precise slowdown
  magnitude is not promoted as a stable production number.
- **REJECTED / NOT ADOPTED:** every selective row was below both neighboring
  controls, and there is no positive performance evidence. The selective
  cache and zero-reloc runtime remain diagnostic artifacts only. Production
  defaults remain unchanged.
- **INFERRED:** per-edge publication/EIP/yield/bailout/depth guards cost more
  than the dispatcher work removed on these sites. Static semantics and the
  negative A/B result are verified; attribution of the cost needs a dedicated
  router-hit/time census.

## Candidate identity

Runtime:

```text
stem  boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2zeroreloctoken1
JS    2a4aff3dd4e1ad0922456c3652919cc2f2b68f4dcfe155620662d0f3cbebdf06
Wasm  cdc93a884f7724d5713030b414f9f7187258fa2ec732a5905409c739064b565a
```

Control:

```text
azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-originalregion-control1.zip
archive SHA  7dd66a6347b910333cea01b4a9a614759aa5c7ec85b3edd4f2c646101e03efde
manifest SHA 9b3bd59325a5479c6c6174094cb14c7346fe599c7c11bb99304df505b94a6aa1
```

Selective:

```text
azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-originalregion-selective1.zip
bytes         4,806,509
archive SHA   bc07ea2efcd37ef558aa71687c22e2d89b5ac0b10d1a65c9648664710dfb2807
manifest SHA  bb72e9ff2ec96f86842d61f1e7adf5a1424f0bba35e6cf82b6b2cce0266e74ad
raw input SHA 176cdd642acc52c501b417dbd44a46bfb71ba704feca2d2e28f529cfe6fa38b0
```

The page pins the selective archive and grouped-manifest hashes and accepts
`originalRegion=selective` only with the exact runtime stem, cache URL,
manifest region contract and zero-reloc publication ABI 1. Wrong mode,
runtime, archive, grouped manifest or ABI fails before group registration.

## Static and semantic verification

The independent verifier confirmed:

```text
redirects                 17
  static-normal            9
  dynamic-source-all       8
retained dispatcher       22
normal target routes      13
router residual fallback   4
routers / region patches   9 / 9
```

Function-level redirect/retained counts are:

```text
2/3, 2/0, 2/3, 2/0, 2/5, 2/0, 1/4, 2/7, 2/0
```

The fixture admits zero-reloc, positive-reloc and needs-fetch success paths.
Null pfn, publication-token mismatch, EIP mismatch, yield, bailout, depth
limit, positive-reloc identity mismatch, cycle and terminal epilogue all use
the original generic fallback. PC-thunk RET, PLT/GOT, libc conditional exits
and initialization/signal boundaries remain reachable with original
semantics.

## Actual PatHouse A-B-A-B-A

Each leg used a fresh Edge profile, Default V8 mode, CSS 1024x768, backing
640x480, 180-second scene settle, 20-second warmup and a direct 45-second
Present window.

| Order | Arm | Presents / wall | FPS | Visual decision |
|---:|---|---:|---:|---|
| 1 | control A1 | 1373 / 45.004545 s | 30.5080 | actual PatHouse |
| 2 | selective B1 | 1263 / 45.006903 s | 28.0624 | actual PatHouse |
| 3 | control A2 | 1309 / 45.006459 s | 29.0847 | actual PatHouse |
| 4 | selective B2 | 1241 / 45.010734 s | 27.5712 | actual PatHouse |
| 5 | control A3 | 1268 / 45.008043 s | 28.1727 | actual PatHouse |

The control trend shows substantial long-run drift, so the condition mean is
not enough by itself. However both B values are below both adjacent controls,
and both local interpolated effects are negative. This is sufficient to reject
the candidate as an improvement, but not to claim a precise universal
slowdown percentage.

## Diagnostic startup boundary

Before the accepted five rows, two attempts produced no CSV row because the
managed local services had exited. The retained failure page directly showed
`ERR_CONNECTION_REFUSED` for port 8765. After restarting the managed core,
bridge and HTTP service, all four required listeners (8765, 9200, 9201, 9300)
and HTTP 200 were verified before A1.

`CdpPresent.psm1` now reacquires the exact expected page while Edge's runtime
context is transiently `about:blank`, but it never admits another URL.
`chrome-error://chromewebdata/` still fails closed, as observed. Recovery from
a real successful target-replacement race remains **NOT VERIFIED**; the
accepted measurements did not need that fallback once the services were live.

## Artifacts

- `artifacts/performance/regional_ntteb_region_selective_aba_actual_pathouse_20260830.csv`
- `artifacts/performance/regional_ntteb_region_selective_aba_actual_pathouse_visual-review.csv`
- ten PNGs named in the visual-review CSV

## Next gate

1. Do not spend more time on guarded `NtCurrentTeb` edge routing: broad was
   neutral and selective was negative.
2. Move to the measured Wine `hash_short_file_name` / `readdir64` family and
   determine whether repeated inputs can be cached with directory-mutation
   invalidation, or whether a guard-free internal region clone can remove the
   hot loop dispatches.
3. Keep the already positive PIC-thunk clone (+3.15%) experimental until its
   runtime text-identity gate is strengthened; do not silently promote it.
