# 622 — Current Acknex transform island rediscovered after ASLR/load-base correction

Date: 2026-08-31 KST

## Conclusion

- **VERIFIED correction:** #605's eleven zero counters did not prove that the
  historical transform island stopped executing. They instrumented historical
  absolute EIPs while the current `acknex.dll` load base had moved by
  `+0x40000`.
- **VERIFIED current execution:** after resolving the current owner CPU and
  module base directly, the same RVAs are ranks 9–17 of the current B owner
  entry census. Five transform-loop entries each execute `2,533,560` times in
  the 20-second window; four indirect thunk/transform entries each execute
  `2,616,120` times.
- **VERIFIED loop ratio twice:** the owner census inferred **99.94908%** from
  entry counts. A later exact exit-site window independently measured
  `3,148,652` back edges and `1,604` fallthroughs from `3,150,256` decisions,
  or **99.949084% taken**.
- **SUPERSEDES 605:** the old document is retained in `archive/` with a banner.
  Its artifact/counter mechanics remain valid, but its current-workload
  rejection and scene-change explanation are invalid.
- **VERIFIED current tier-2 input:** the rebuilt B plan selects 10 multi-block
  regions / 91 blocks / 1,398 ops and covers
  `66,648,837 / 214,767,422 = 31.0330%` of current owner entries. The primary
  transform island is one exact 4-block region and the second thunk/transform
  pair is another exact region.
- **NOT VERIFIED speedup:** no fused mega-function or actual PatHouse A/B has
  run yet. Entry hotness is not CPU time; the 10% frame-time gate still applies.

## Root cause of the false zero

Historical targeted EIPs assumed:

```text
acknex base 0x7F360000
absolute 0x7F3A9650 -> RVA +0x49650
```

The current direct resolver measured:

```text
acknex base 0x7F3A0000
RVA +0x49650 -> absolute 0x7F3E9650
```

The targeted cache in #605 continued counting `0x7F3A9650`, which is
`acknex+0x09650` under the current mapping, not `acknex+0x49650`. The complete
`+0x40000` displacement explains all eleven zeros without invoking a scene,
camera, runtime or workload change.

## Current exact counts

Source: current B owner-anchored 44,395-entry census, actual PatHouse window.

| Role | RVA | Current EIP | Hits |
|---|---:|---:|---:|
| loop header | `+49650` | `7F3E9650` | 2,533,560 |
| loop branch | `+49659` | `7F3E9659` | 2,533,560 |
| loop exit | `+4966D` | `7F3E966D` | 1,290 |
| transform dispatch | `+46760` | `7F3E6760` | 2,533,560 |
| transform continuation | `+46798` | `7F3E6798` | 2,533,560 |
| transform continuation | `+467A6` | `7F3E67A6` | 2,533,560 |
| unused historical row | `+467AA` | `7F3E67AA` | 0 |
| indirect thunk 1 | `+84364` | `7F424364` | 2,616,120 |
| indirect thunk 2 | `+84477` | `7F424477` | 2,616,120 |
| transform target 1 | `+1041D7` | `7F4A41D7` | 2,616,120 |
| transform target 2 | `+1042A3` | `7F4A42A3` | 2,616,120 |

Loop-back inference:

```text
taken = hits(+49659) - hits(+4966D)
      = 2,533,560 - 1,290
      = 2,532,270

taken ratio = 2,532,270 / 2,533,560
            = 99.94908%
```

This agrees with #273's historical control-flow reconstruction:

```text
+49650 CALL +46760 -> indirect transform -> RET
       -> second indirect transform -> RET -> +49659
+49659 JL +49650 (99.949% taken) / fall through +4966D
```

## Exact current exit-site confirmation

The separately selected 91-block/234-exit probe ran for 20.006765 seconds in
actual PatHouse on one anchor-captured game CPU (`0x23265320`). Unlike the
owner-entry subtraction above, both branch counters survived and were read
directly:

```text
transform region observed exits  9,450,768
entry decisions                   3,150,256
loop back edge                    3,148,652
loop fallthrough                  1,604
taken ratio                       99.949084%
```

All 63 exits eliminated by Binaryen were independently classified as
deterministic zero, all four control words were zero after cleanup, and both
screenshots were visually confirmed as the real PatHouse room. This completes
the old step-1 measurement gate; it does not by itself prove speedup.

Artifacts:

- `artifacts/performance/b_current_exit_histogram_20260831.csv`
- `artifacts/performance/b_current_exit_histogram_20260831.raw.json`
- `artifacts/performance/b_current_exit_histogram_20260831.top.csv`

## Current plan and content identity

The new resolver maps the current top-100 (+ anchor) to exact guest bytes:

```text
acknex.dll       80 rows
ntdll.so          5
kernelbase.dll.so 4
ntdll.dll.so      4
kernel32.dll.so   3
win32u.so         1
Azrok.exe         1 anchor
Unknown           3
```

Exact `acknex.dll` app-archive identity:

```text
bytes   2,682,880
SHA-256 876f6870f6858c3829c0830415bf30cf7dd375590810eef231a7e6b1a68eedc6
```

Current plan:

```text
path     artifacts/performance/hqemu_tier2_hot_regions_b_current_20260831.json
SHA-256  8e537ab4337fc8ce9cdec994d01dc7831bd6275619127af74c852d32b3387c7f
regions  10 multi-block
blocks   91
ops      1,398
internal 114
side     159
coverage 66,648,837 / 214,767,422 = 31.0330% owner entries
```

The four-block transform region contains current `+49659`, `+49650`, `+46760`
and `+4966D`; a second region contains `+46798` and indirect thunk `+84477`.
The marker corpus has a different global keyspace, so only the exact 91 selected
block projections are rebased for probing; no old/full coverage claim is
carried over.

## Ghidra direct decompilation

Headless Ghidra 12 analyzed the exact `acknex.dll` SHA above at preferred image
base `0x10000000`. The current runtime EIPs map to the following image VAs.

`FUN_10049630` is the outer strided loop:

```c
FUN_10047b40();
for (i = 0; i < *(int *)(DAT_102ff4cc + 0x28); i++) {
    FUN_10046760();
    // destination and source pointers both advance by 0x2c bytes
}
```

The disassembly confirms register arguments and exact loop mechanics:

```text
10049650 MOV EDX,EBX
10049652 MOV ECX,EDI
10049654 CALL 10046760
10049659 MOV ECX,[102FF4CC]
1004965F ADD ESI,1
10049662 ADD EDI,2C
10049665 ADD EBX,2C
10049668 CMP ESI,[ECX+28]
1004966B JL  10049650
```

`FUN_10046760(dest ECX, source EDX)`:

```c
record = *(DAT_10304c40 + 0x4f8) + source[8] * 0x94;
if (source[8] >= 0 && record != 0 && *(record + 4) == 3) {
    thunk_FUN_10084351(dest,     source,     record + 0x14);
    thunk_FUN_10084464(dest + 3, source + 3, record + 0x14);
} else {
    copy 24 bytes source -> dest;
}
```

The two live thunks dispatch through `_DAT_10252150` and `_DAT_10252140`.
Their current targets decompile as:

- `FUN_101041D7`: 3x3 matrix transform of a three-float vector;
- `FUN_101042A3`: homogeneous 4x4 point transform followed by reciprocal-W
  normalization using SSE `rcpps` plus one Newton refinement.

This proves the hot island is a batched pair of vector transforms, not a generic
Wine hash/helper path. A future HLE must validate the live thunk targets and
preserve the approximate reciprocal/f32 behavior or fall back; replacing it
with unconstrained host `1.0f / w` is not yet accepted.

## Artifacts

- `artifacts/performance/b5_samewindow_owner_census_20260831.raw.json`
- `artifacts/performance/b_current_module_map2_20260831.json`
- `artifacts/performance/b_current_module_map2_20260831.rows.csv`
- `artifacts/performance/hqemu_tier2_hot_regions_b_current_20260831.json`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/hqemu-tier2-module-content-map-b-20260831.json`
- `artifacts/performance/exit_histogram_probe_selection_b_current_rebased_20260831.json`

## Next gate

1. use the completed 91-block/234-site owner-filtered taken-edge window;
2. admit the exact hot transform/thunk edges instead of absolute-address
   guesses;
3. co-locate and fuse the transform island into one bounded Wasm body that
   retains GP/lazy flags/x87 state;
4. run fresh-process actual-PatHouse A/B and reject unless frame time improves
   by at least 10%.
