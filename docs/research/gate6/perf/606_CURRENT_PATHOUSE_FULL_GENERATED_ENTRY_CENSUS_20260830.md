# 606 — Current PatHouse full generated-entry census

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED visual/browser:** launch and full-census before/after PNG pairs all
  show the actual PatHouse room, pink Azron, furniture, rug, HUD, and lower
  status panel.
- **VERIFIED cache/runtime:** a snapshot-only runtime publishes a caller-owned
  30,550-U32 buffer through currentabi1 reserve words 62/63.  A separate cache
  instruments every merged function body while preserving all existing local
  indices, 94 groups, 30,550 entries, and 28,944 relocation patches.
- **VERIFIED dynamic:** the accepted 20.016932-second window observed
  33,370,115 generated-Wasm function entries across 3,612 nonzero cache keys,
  or 1,667,094.39 entries/s and 63,805.19 entries/Present.
- **VERIFIED distribution:** top 1 / 10 / 100 entries account for 1.7593% /
  12.2547% / 44.8893% of all generated entries.  There is no single magic
  entry; a useful region must cover a family.
- **VERIFIED current-game path:** keys that statically match `Azrok.exe`
  include a 300-record stride scan rooted at `00592060` and the MSVC
  `_LocaleUpdate` / `__isleadbyte_l` chain.  The old 605 acknex transform
  family remains absent.
- **NOT VERIFIED:** which aggregate top entries run on the actual Azrok main
  CPU.  EIP alone is process-local, so the global top list may include Wine or
  helper processes.  The next gate filters all entries to the CPU that executes
  the verified Azrok `0059207C` scan block.

## Full-entry instrumentation contract

The immutable runtime is:

```text
stem   boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2fullentrycensus1
JS     330678 bytes
SHA256 ebe8c66094a66dda679bf53d422a4ef7ec394431b54f2f86b3c820368e1e3f09
Wasm   3056569 bytes
SHA256 62b027aeb1013bb12e9729464b112390194b3d8159eed914d678fa77c0299528
```

The runtime adds no C++ hot-path counter.  It exposes:

```text
reloc map                 12968408 / 262144
counter-buffer pointer    reserve word 62 @ 12968400
configured counter count reserve word 63 @ 12968404
ABI                       1
```

The measurement allocates 30,550 U32 words with `_malloc`, zeroes them, and
publishes the exact pointer/count only for the timing interval.  Every merged
entry does an atomic pointer load; a zero pointer skips the write.  With a
configured pointer it increments the counter whose index is the existing
manifest group order followed by entry order.  Clearing word 62 stops new
writes before the 30,550-word snapshot is copied and freed.

The immutable cache is:

```text
name   azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-fullentrycensus1.zip
bytes  4942382
SHA256 86711cb390a9eb12973f43cd7810044b93eda40b0339baec345f3bdbc0d9a840
source b007fa84ac483360389d136fa45682ef774b8a7b19f8cbf214cef1d4a389035a
```

It appends one i32 local to each selected body; the observed appended index
range is 5..18, while every pre-existing local index remains unchanged.  The
94 groups gain 975,890 uncompressed Wasm bytes.  The postprocessor re-finds all
28,944 unique padded relocation markers and rewrites their absolute offsets.
Fixture and actual-artifact byte reproduction, WebAssembly validation 94/94,
wrong-hash/ABI/mapping rejection, pointer-zero no-write, and direct/indirect
entry tests all pass.

## Visual and timing acceptance

The fresh launch used CDP 9348, a fresh Edge profile, current fastboot4 app,
current Korean root, 180 seconds of post-readiness settling, and 15 seconds of
warmup.  Both launch screenshots show PatHouse.  Its diagnostic timing was 745
Presents / 30.009775 s = 24.8252 FPS.

The attached full-entry window also captured PatHouse before and after.  It
measured 523 Presents / 20.016932 s = 26.1279 FPS.  This is profiler liveness,
not a candidate/control FPS result: every generated entry executes an extra
pointer guard, and counted entries additionally perform an atomic increment.

## Aggregate current top entries

| Rank | Hits | EIP | Ops / bytes | Group |
|---:|---:|---|---:|---:|
| 1 | 587,080 | `10627B70` | 2 / 4 | 69 |
| 2 | 539,493 | `10635F1F` | 167 / 520 | 86 |
| 3 | 500,036 | `10635FAA` | 118 / 381 | 87 |
| 4 | 393,824 | `7BDD1130` | 20 / 36 | 74 |
| 5 | 354,126 | `1059200C` | 2 / 4 | 48 |
| 6–13 | 342,967 each | eight-entry `104F0Dxx/10627A60/106791xx` family | mixed | 10/11/20/21/69/88/93 |

The two large `10635F1F/10635FAA` blocks overlap in guest address range and
carry many internal side exits.  Their process/module owner is **NOT
VERIFIED**.  Treating the numeric range as a particular DLL without the CPU or
memory owner would repeat the indirect-evidence error this investigation was
designed to avoid.

## Statically identified Azrok.exe work

The fastboot4 package's `Azrok.exe` PE image is `00400000..006F5000`.  The
full snapshot contains 7,262,968 hits across 1,183 nonzero entries in that
numeric range.  More importantly, the highest keys match exact Ghidra functions
from the same executable:

### 1. 300-record stride scan

```c
for (i = 0; i < 300; ++i)
    if (*(char *)(base + 0x9360 + i * 0xa9) != 0) count++;
```

`0059207C` and its latch `005920AF` each recorded 156,898 entries.  This is a
verified current main-game anchor and a possible small loop-fusion target, but
its whole-program coverage is not yet enough to claim a material FPS gain.

### 2. MSVC locale / lead-byte chain

The current top sequence includes:

```text
004DC546 / 006512FE  _LocaleUpdate
004DB9B6 / 00667CB0  __isleadbyte_l
00667CC1 / 00667CE4  interior/exit blocks
00651370              _LocaleUpdate continuation
```

Counts are 155,608 for the LocaleUpdate pair and 147,176 for the lead-byte
family in the same window.  Static decompilation shows the usual thread-locale
refresh checks followed by a ctype-table lookup and `0x8000` mask.  This makes
locale/CP949 specialization a plausible reusable legacy-game optimization,
but no CPU-time or safe fast-path guard has yet been proved.

## Why CPU ownership is the next gate

The cache is shared across Wine processes and guest CPUs.  Numeric EIP ranges
alone do not identify a process, and even the same EIP can have multiple cache
keys distinguished by decoded-op hash.  A global high count can therefore be
irrelevant to the frame-producing CPU.

The next candidate captures the first CPU pointer that executes the verified
`v5-0059207c-3c3f909d` game anchor in reserve word 60, then counts all 30,550
entries only when function parameter 0 equals that pointer.  This retains
internal direct/generic-tail coverage while removing unrelated CPU noise.

## Artifacts

- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/boxedwine-wasm-jit-cache-full-entry-census.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-full-entry-census-cache.mjs`
- `tools/boxedwine_local/profiles/azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-fullentrycensus1.zip`
- `artifacts/performance/regional_full_entry_launch_present_20260830.csv`
- `artifacts/performance/20260829T174913859Z_edge_default_cdp9348_pid49208.before.png`
- `artifacts/performance/20260829T174913859Z_edge_default_cdp9348_pid49208.after.png`
- `artifacts/performance/regional_full_entry_actual_pathouse_20260830.csv`
- `artifacts/performance/regional_full_entry_actual_pathouse_20260830.raw.json`
- `artifacts/performance/regional_full_entry_actual_pathouse_20260830.top.csv`
- `artifacts/performance/regional_full_entry_actual_pathouse_20260830.visual-review.csv`
- `artifacts/performance/full_entry_20260830_025525_before.png`
- `artifacts/performance/full_entry_20260830_025525_after.png`

