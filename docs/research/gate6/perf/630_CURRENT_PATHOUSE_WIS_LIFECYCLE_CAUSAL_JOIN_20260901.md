# 630 — Current PatHouse WIS lifecycle causal join

Date: 2026-09-01 KST

## Conclusion

- **VERIFIED dynamic:** final `causalwisjoin1` joined `720` actual-PatHouse Presents over `14,335,000 us` to exactly `720` complete WIS lifecycles. Every frame performed one WIS load consisting of `6` reads and `130,580` bytes; all `26,640` backend accesses were cache hits, with zero direct/ZIP/host backend calls and zero cache misses.
- **VERIFIED causal join:** each load had the same `KThread`, Wine user handle, Linux fd, `KObject`, and `.wis` path across adjacent Wine 11 `create_file(44) -> get_handle_fd(48) -> close_handle(21)`. Each request occurred `720` times and their directly joined union was `891,330 us`.
- **VERIFIED 10% surface:** candidate-specific clock-tax subtraction gives `outer wait + joined handles = 1,462,935 us`, or `10.205337%` of wall. A full WIS-lifecycle HLE boundary gives `1,522,255 us`, or `10.619149%` (`2.114243 ms/frame`), only `88,755 us` above the 10% requirement. This admits implementation and actual A/B; it is not a measured speedup.
- **VERIFIED correction:** the `1,738,475 us` aggregate Wine publish-to-client-return value from `causalstage1` is a residency upper bound, not wholly removable time. It must not be added to WIS time. Only the exact three-request join above is causal evidence.
- **VERIFIED/REJECTED remains:** #629's cached-ZIP mutex bypass achieved only `5.3707%` frame-time reduction and remains rejected. The new surface comes from eliminating the complete open/read/close lifecycle, not from retrying that mutex-only candidate.
- **PRODUCTION/REMOTE UNCHANGED:** both runtimes and caches are local diagnostics. No normal launcher or remote asset was changed.

## Actual runtime identity and visual admission

The final direct-join run used:

```text
runtime stem  boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1causalwisjoin1
JS SHA-256    7d6b6c95b919498cc1414bc314bb979d176bc360fcdcdb647f80b85f9274f4dd
Wasm SHA-256  c1fb4b5198b544d032bf6f2941bd6ea3e0101825a64dbe31e3547cac79d2677b
cache         azrok-jit-grouped-multidirectloops1-currentabi1-causalwisjoin1-map12993112-20260901.zip
cache SHA-256 435cf0991aac963c1f152c598f8a5549015ece5d5a4adbdbede90347d84eaf61
JIT replay    143 groups / 44,395 entries / 33,912 patches
```

The page remained visible in the actual PatHouse room with rug, blue character, HUD, and quest panel. Before/after PNG SHA-256 values were `6b48cf0e...b2da5` and `c3c7751e...b03d1`.

The shared seqlock publisher was ABI 1, shared memory true, capacity `65,536`, heap bytes `1,476,919,296`, and addresses `seq=1,396,021,112`, `bytes=1,396,021,116`, `data=1,396,021,120`. Sequence 2 was discarded; sequences `4,6,8,10,12,14` were accepted with no validation error.

## Exact WIS and Wine totals

```text
wall                         14,335,000 us / 720 Presents
technical FPS                50.2267
frame time                   19.9097 ms
WIS syscalls                 4,320 = 6/frame
WIS bytes                    94,017,600 = 130,580/frame
WIS syscall residence        695,725 us
outer mutex wait             636,405 us
cache backend/hits           26,640 / 26,640
cache misses                 0
direct/ZIP/host backends     0 / 0 / 0

create_file(44)              720 calls / 601,630 us
get_handle_fd(48)            720 calls / 160,190 us
close_handle(21)             720 calls / 129,510 us
joined three-request union   891,330 us
```

All join failure counters were zero: ambiguous, unmatched, timeout, interleaved, handle-parse failure, shape mismatch, and cross-window. All causal-stage mismatch/overflow/outstanding counters were also zero.

Wine 11's exact parsed layout was generic request header `id +0 / request_size +4 / reply_size +8`, `get_handle_fd` and `close_handle` request handle at `+12`, and `create_file` reply status at `+0` with returned handle at `+8`. Admission required a valid user handle `0x20..0xffef`, same thread/object/path, adjacent request order, exact six reads/130,580 bytes, and completion within two seconds; every mismatch failed closed.

## Candidate-specific clock-tax arithmetic

The final window's maximum clock-probe cost was applied only to intervals used by each candidate:

```text
outer raw                         636,405 us
outer targeted tax upper          43,200 us
joined-handle raw                 891,330 us
joined targeted tax upper         21,600 us
outer + joined lower            1,462,935 us = 10.205337%

full WIS syscall + joined raw   1,587,055 us
combined targeted tax upper       64,800 us
full HLE semantic lower         1,522,255 us = 10.619149%
10% required                   1,433,500 us
full-HLE margin                   88,755 us
```

The `852,000 us` all-clock upper from `causalstage1` covers all probed intervals and is not a valid deduction from one candidate. Likewise its total Wine `1,738,475 us` is residency, not causal removability.

## Static boundary and next implementation

- **VERIFIED static salvage/current bytes:** the upper face-resource function at `0x00550e00` constructs a path, obtains a descriptor through the loader rooted at `0x005127e0`, then copies `0x20000` bytes from descriptor payload `[EAX+0x24]` into a new BMAP and performs the existing purge/destructor sequence. The loader reads a five-dword WIS header, allocates `0x20000`, and reads the declared `0x1fe00` payload. All 113 shipped `Data/Texture/HP_*.wis` files are 130,580 bytes with header `[2,256,255,0,0x1fe00]`.
- **INFERRED implementation boundary 1:** at lookup block `0x00551198`, key `v5-00551198-ad10896f` in group 0082, an exact-path immutable decoded-WIS hit may bypass the loader's Wine open/read/close lifecycle.
- **INFERRED implementation boundary 2:** at return/capture block `0x005511b1`, key `v5-005511b1-6262cfd0` in group 0140, original results can capture and validate `[descriptor+0x24]` before enabling hits. Miss, mismatch, unsupported shape, or re-entry must execute the original path.
- **NOT VERIFIED:** no live Ghidra MCP instance re-decompiled this function in the final run. The current statement is cross-checked from preserved salvage plus current executable bytes/group manifest. The `0x20000 - 0x1fe00 = 512` byte descriptor tail is not proven stable or renderer-irrelevant; the candidate must require matching original captures before activation.

Only an actual adjacent PatHouse A/B showing at least 10% frame-time reduction can accept this HLE.

## Evidence

- `artifacts/performance/causalstage1_actual_pathouse_analysis_20260901.json`
- `artifacts/performance/causalwisjoin1_actual_pathouse_analysis_20260901.json`
- `artifacts/performance/causalwisjoin1_actual_pathouse_shared_snapshots_20260901.json`
- `artifacts/performance/causalwisjoin1_actual_pathouse_{before,after}_20260901.png`
- `tools/boxedwine_local/bwujit_threaded_abi/source/kernel/syscall.cpp`
- `tools/browser_diagnostics/analyze_azrok_causal_wis_handle_join.py`

