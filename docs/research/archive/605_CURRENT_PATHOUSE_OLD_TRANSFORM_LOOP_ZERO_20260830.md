# 605 — Current PatHouse rejects the old +49650 transform-loop region

> **SUPERSEDED by 622.** The counters were attached to historical absolute
> EIPs. Current `acknex.dll` moved by `+0x40000`; the same RVAs are current
> owner ranks 9–17 and the `+49659 -> +49650` loop is 99.94908% taken.

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED visual/browser:** all four launch/census screenshots show the
  actual PatHouse room before and after timing.  They are not the character
  selection or transition screen rejected by 603.
- **VERIFIED cache instrumentation:** an immutable postprocessor inserted one
  `i32.atomic.rmw.add` at the first instruction of each of 11 selected merged
  Wasm function bodies.  The same body is reached by exported dispatch,
  intra-group direct tails, and common generic indirect tails, so those routes
  cannot bypass the counter.
- **VERIFIED static/artifact:** the candidate changes 11 functions in six of
  94 groups, adds 132 merged-Wasm bytes, retains 30,550 entries and all 28,944
  relocation patches, and validates all 94 modules.  It is byte-reproducible
  from currentabi1.
- **VERIFIED dynamic:** in a visually accepted 30.006583-second current
  PatHouse window, all 11 exact-entry deltas were **zero**.  Reserve words
  11..63 also remained zero.
- **REJECTED for the current workload:** the historical `+49650 -> +46760 ->
  two transforms -> +49659` loop is not the first fused regional AOT target
  for this current PatHouse scene.  Implementing it now would optimize an
  unexecuted path.
- **NOT VERIFIED:** the current hot EIP family.  A full 30,550-entry dynamic
  buffer census is the next gate; the broad 604 census already proves that
  control-flow/helper crossings remain frequent.

## Why this is stronger than the old entry probe

The current accepted cache rewrites both static and dynamic tails inside
merged Wasm.  A C++ dispatcher probe can therefore miss an entry reached
without returning to C++.  This candidate instruments the selected merged
function body itself, after all grouping and tail rewriting.  The fixture
executes the same instrumented target three ways:

1. exported function call;
2. an internal direct `call`;
3. `call_indirect` through the shared table.

Each route increments the same reserved counter exactly once.  An unselected
function and every other reserve word stay zero.  Wrong relocation base,
source hash, duplicate word, and missing EIP are fail-closed.

The actual candidate also re-finds the unique padded relocation marker after
body insertion and updates every absolute offset.  The general ABI verifier
then confirms:

```text
groups         94
entries        30550
patches        28944
wasm validated 94
reloc map base 12968408
counter base   12968152
```

## Immutable artifacts

Runtime:

```text
stem   boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2targetedentrycensus1
JS     330314 bytes
SHA256 034e921ccfae19bbaf50be5ace3afd94e71be086b07a8ec5a664951c54910bc6
Wasm   3057264 bytes
SHA256 089fe67e3a227499cbe97f852ea98732b6eb4faf0cf69aff7f6c0e5e1caad4b8
ABI    targeted entry 1 / reserve 64 / reloc 12968408:262144
```

Cache:

```text
name   azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-targetedentrycensus1.zip
bytes  4805180
SHA256 467b725f5fbe39a32f93aaf9c03c10cceb72a6286ab7bbf8689535d0af580b46
source b007fa84ac483360389d136fa45682ef774b8a7b19f8cbf214cef1d4a389035a
manifest source e0e63b45a20bf533332e8faf13b7660391e830be1235518a12e1383683b62696
```

The 11 counter words are:

| Word | EIP | Key/group |
|---:|---|---|
| 0 | `7F3A9650` | `v5-7f3a9650-70968b10`, group 28 |
| 1 | `7F3A9659` | `v5-7f3a9659-b126b300`, group 28 |
| 2 | `7F3A966D` | `v5-7f3a966d-b54f9582`, group 28 |
| 3 | `7F3A6760` | `v5-7f3a6760-9dec29df`, group 13 |
| 4 | `7F3A67AA` | `v5-7f3a67aa-efcdef46`, group 13 |
| 5 | `7F3A6798` | `v5-7f3a6798-53479fb1`, group 82 |
| 6 | `7F3A67A6` | `v5-7f3a67a6-c7871786`, group 11 |
| 7 | `7F3E4364` | `v5-7f3e4364-cfd34830`, group 8 |
| 8 | `7F3E4477` | `v5-7f3e4477-95f798a0`, group 82 |
| 9 | `7F4641D7` | `v5-7f4641d7-5f31f58a`, group 27 |
| 10 | `7F4642A3` | `v5-7f4642a3-524c7882`, group 27 |

## Dynamic acceptance and result

The final launch used the stable candidate cache HTTP bytes, a fresh Edge
profile, CDP 9347, 180 seconds of post-readiness settling, and 15 seconds of
warmup.  Its before/after PNGs both show PatHouse.  The launch timing was 717
Presents / 30.016356 s = 23.8870 FPS.

The attached exact-entry window then captured a second PatHouse before/after
pair and measured 719 Presents / 30.006583 s = 23.9614 FPS.  Its complete
counter result is:

```text
7F3A9650 0    7F3A9659 0    7F3A966D 0
7F3A6760 0    7F3A67AA 0    7F3A6798 0    7F3A67A6 0
7F3E4364 0    7F3E4477 0
7F4641D7 0    7F4642A3 0
unused reserve words 11..63: all zero
```

The FPS is diagnostic-only.  It is not an optimization comparison and does
not support a regression claim.  The acceptance claim is only that real
PatHouse stayed live while exact entries remained zero.

## Reconciliation with historical evidence

Documents 213, 219, and 244 measured the same binary and established that this
loop was hot in an older PatHouse run.  That evidence remains historically
valid.  It cannot be promoted to the current fastboot4/currentabi1 scene: the
new generated-Wasm entry counters cover the bypass routes that a dispatcher
probe misses and still report zero.

Possible causes such as scene state, camera state, animation path, or older
runtime workload differences are **NOT VERIFIED**.  They are unnecessary for
the current decision.  The current decision is simply that a zero-entry region
cannot improve this measured PatHouse window.

## Artifacts

- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/boxedwine-wasm-jit-cache-targeted-entry-census.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-targeted-entry-census-cache.mjs`
- `tools/boxedwine_local/profiles/azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-targetedentrycensus1.zip`
- `artifacts/performance/regional_targeted_entry_launch_present_20260830.csv`
- `artifacts/performance/20260829T173048050Z_edge_default_cdp9347_pid96216.before.png`
- `artifacts/performance/20260829T173048050Z_edge_default_cdp9347_pid96216.after.png`
- `artifacts/performance/regional_targeted_entry_actual_pathouse_20260830.csv`
- `artifacts/performance/regional_targeted_entry_actual_pathouse_20260830.raw.json`
- `artifacts/performance/regional_targeted_entry_actual_pathouse_20260830.visual-review.csv`
- `artifacts/performance/targeted_entry_20260830_023633_before.png`
- `artifacts/performance/targeted_entry_20260830_023633_after.png`

## Next gate

Instrument all 30,550 current compiled entry bodies against a dynamically
allocated U32 array.  A fixed pointer in reserve word 62 keeps the cache ABI
generic without consuming 30,550 static words; reserve word 63 records the
configured count.  Rank current EIPs by hits per second/frame, then build a
region only from the actually observed current path.
