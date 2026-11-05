# 608 — Current PatHouse owner-process and hot-module resolution

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED visual/browser:** the resolver was attached only after both CDP
  screenshots showed the actual PatHouse room, furniture, rug, player Azron,
  and HUD.  The before/after images remained in that scene.
- **VERIFIED owner process:** the anchored CPU was `0x2733CBE0`, owned by PID
  71.  Its command line contains the Wine loader, `Azrok.exe`, and the actual
  launch arguments.  The executable field is the Wine preloader; the process
  name field `mpegaudioparse3:` is thread-like and is not sufficient by itself
  to reject the command-line/process identity.
- **VERIFIED resolution:** all requested top 100 current game-CPU EIPs resolved
  and returned 64 original guest bytes each.  Their modules are 40
  `Azrok.exe`, 35 Wine `ntdll.so`, 24 `/lib/libc.so.6`, and one unmapped
  thunk.
- **VERIFIED current top family:** ranks 1–3 are Wine `ntdll.so` offsets
  `0x15F1F`, `0x7B70`, and `0x15FAA`.  Rank 4 is the exact unmapped x86 thunk
  beginning `55 8B EC ... CD 9A ...`, with 354,543 anchored entries in the
  accepted census.  Ranks 5–13 alternate between libc and ntdll paths.
- **VERIFIED Azrok anchor:** `0059207C` resolves to the shipped `Azrok.exe` at
  file offset `0x000BC07C`; its 64 bytes reproduce the 300-record scan already
  confirmed statically and dynamically.
- **VERIFIED cleanup:** counter publication was detached before readout; owner,
  getter, pointer, count, and configured-word state were all zero after the
  quiescence interval and the dynamic buffer was freed.
- **NOT VERIFIED in this document:** the semantic function names of the ntdll
  and libc offsets.  Those require ELF program-header translation plus symbol,
  disassembly, and Wine-source correlation.  Module identity is not yet a
  license to replace the code.

## Resolver artifact identity

The immutable resolver runtime is:

```text
stem   boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2anchoredmap1
JS     331685 bytes
SHA256 f918c7fd685fddc9cdd11e18c10a8fc3099e0ae1e5a42558e8f8adaf69e2be0d
Wasm   3057265 bytes
SHA256 953608e849a33b05b0b91b30921b9ba707fa9ba5d63c2c443feb3c9393e2bc12
```

Its paired cache is:

```text
name   azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-anchoredmap1.zip
bytes  4956506
SHA256 2622dcdc12d6f063d25d36df43e6737f009d69f75aff59d88398c1a3115ff299
groups 94
entries 30550
patches 28944
```

The local files and HTTP responses matched byte-for-byte.  Cache regeneration
and both the original anchored-census verifier and resolver verifier passed.

The extracted module witnesses are:

```text
ntdll_current_wine11.so 578920 bytes
SHA256 3a03b005d9311f521ee26c49dd395850f9a379ba0d0195559bb383309eec88b7

libc_current.so.6       1655568 bytes
SHA256 141319771edb3c2ffbd91d7617dc133bc70eafa3bf718defa60d11ba5a729d7d
```

## ABI-drift rejection and fix

Adding resolver-only strings initially shifted the naturally linked data
layout by 64 bytes.  The first build therefore exposed relocation-map base
`12968472`, not the cache contract `12968408`.  That build was rejected before
browser execution.

The resolver-only reserve was reduced from 64 to 48 U32 words, and control
indices were moved from `60/62/63` to `44/46/47`.  This preserved the absolute
addresses:

```text
owner CPU      12968392
counter ptr    12968400
counter count  12968404
reloc map      12968408 / 262144
```

This compensation is resolver-local.  It does not alter the production
runtime or the earlier 64-word anchored-census contract.

## Read-only resolver contract

The runtime exposes only bounded diagnostic reads:

1. the anchored process identity (`pid`, CPU, memory, executable, process-name
   field, and command line);
2. `KProcess::getModuleName` and `KProcess::getModuleEip` for a supplied EIP;
3. at most 256 original guest bytes, copied only after
   `KMemory::canRead(address, length)` succeeds.

`getModuleEip` uses the mapped-file relationship
`eip - mappedFile.address + mappedFile.offset`.  The accepted run requested 64
bytes per EIP and returned all 100 rows without a short or failed copy.

## Accepted process witness

```text
pid     71
cpu     0x2733CBE0
memory  0x278333F0
exe     /opt/wine/lib/wine/i386-unix/wine-preloader
name    mpegaudioparse3:
command /opt/wine/lib/wine/i386-unix/wine-preloader ... wine Azrok.exe
        -NX 200 -PL player -DIR localauth -IP 127.0.0.1:9201
```

The raw command string in the JSON is delimiter-free because it is a compact
diagnostic export; the presence and order of the launcher components are
directly recorded.  The `name` field can describe a current thread and is not
used as the semantic process name.

## Current top mappings

| Rank | Anchored hits | Guest EIP | Module | File offset | First bytes / role |
|---:|---:|---|---|---:|---|
| 1 | 439,255 | `10635F1F` | `ntdll.so` | `0x15F1F` | `89 C1 66 C1 E9 05 ...` |
| 2 | 425,011 | `10627B70` | `ntdll.so` | `0x07B70` | `8B 1C 24 C3` tiny return path |
| 3 | 407,129 | `10635FAA` | `ntdll.so` | `0x15FAA` | overlaps the rank-1 region |
| 4 | 354,543 | unmapped | `Unknown` | — | `55 8B EC ... CD 9A ... C3` Unix-call thunk |
| 5 | 286,960 | `1059200C` | `libc.so.6` | `0x11200C` | `8B 1C 24 C3` tiny return path |
| 6 | 283,067 | `104F0E11` | `libc.so.6` | `0x70E11` | end/return of same libc family |
| 7 | 283,067 | `104F0DBD` | `libc.so.6` | `0x70DBD` | libc family body |
| 8 | 283,067 | `104F0DF8` | `libc.so.6` | `0x70DF8` | libc family continuation |
| 9 | 283,067 | `10627A60` | `ntdll.so` | `0x07A60` | ntdll table/thunk path |
| 10–13 | 283,067 each | `1067918D/184/1A1`, `104F0DB0` | ntdll/libc | `0x5918D/184/1A1`, `0x70DB0` | equal-count call chain |

The exact rank-4 guest bytes are:

```text
55 8B EC 51 53 56 57 33 C0 FF 75 10 FF 75 0C FF
75 08 CD 9A 83 C4 0C 89 45 FC 8B 45 FC 5F 5E 5B
8B E5 5D C3
```

This verifies that the current PatHouse game CPU repeatedly crosses the Wine
Unix bridge.  It does not yet prove that all rank-1/3 ntdll work belongs to the
same semantic operation or that a previously built specialized helper is
faster in the current corpus.

## Visual and measurement limits

The resolver launch diagnostic observed 804 Presents / 30.007918 seconds =
26.7929 FPS, but the resolver and full-entry counters add atomics and guards.
That value is a liveness/scene witness only and is not comparable to the
production baseline or a candidate.

The earlier character-selection/transition-screen 69–72 FPS rows remain
rejected by #603.  Nothing in this resolver result re-admits them.

## Next gate

Translate the recorded file offsets through each ELF's actual `PT_LOAD`
segments, identify the containing functions with symbols and disassembly, and
correlate ntdll results with the exact Wine 11 source.  If the leading family
is the Unix-call/dispatch path, construct a current-corpus candidate in which
the 94 groups, 30,550 entries, 28,944 patches, app/root, and all non-target
runtime bytes remain fixed.  Only a real-PatHouse visual A-B-A may decide
adoption.

## Artifacts

- `tools/browser_diagnostics/Invoke-AzrokAnchoredMapResolve.ps1`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/boxedwine-wasm-jit-cache-anchored-full-entry-census.mjs`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-anchored-full-entry-census-cache.mjs`
- `tools/boxedwine_local/profiles/azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-anchoredmap1.zip`
- `artifacts/performance/regional_anchored_map_actual_pathouse_20260830.json`
- `artifacts/performance/regional_anchored_map_actual_pathouse_20260830.rows.csv`
- `artifacts/performance/anchored_map_resolve_20260830_035546_before.png`
- `artifacts/performance/anchored_map_resolve_20260830_035546_after.png`
- `artifacts/performance/ntdll_current_wine11.so`
- `artifacts/performance/libc_current.so.6`
