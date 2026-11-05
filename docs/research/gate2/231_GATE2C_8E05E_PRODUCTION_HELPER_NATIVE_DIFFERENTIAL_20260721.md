# 231 Gate 2c 8E05E production helper native differential

Date: 2026-07-21

## Scope

The full one-iteration oracle from document 228 is now implemented as the
production `d3d9WebRunMaterialScan` helper in `hotAotMaterialScan.{h,cpp}`.
The helper is connected to relocated acknex.dll RVA `0x0008E05E` behind
`BOXEDWINE_D3D9WEB_MATERIAL_SCAN_AOT`.

No Emscripten or browser build was performed in this step.

## VERIFIED -- bounded production transaction

The production helper covers exactly the three call-free path families from
documents 225 and 228:

1. A+B+latch for equal material IDs;
2. A+C+E+latch for mismatch with unsigned `counter <= EBX`;
3. A+C to the pre-PUSH successor at `entry+0x18` for `counter > EBX`.

It never enters the indirect D3D call block. A write-bearing path prepares a
`WasmMemoryWrite32Plan`, buffers the counter write, forwards overlapping bytes
into the later latch count read, validates the plan, and commits through
`wasmMemoryCommitWrite32` before publishing EAX/EDI/flags/EIP.

Because the soft MMU has no mapping generation, production acquires one outer
recursive `KMemory::mutex` before the exact guard. The same lock remains held
through all DS/SS reads, write preparation, alias forwarding, Write32 commit,
CPU-state commit, and successor decode. This closes the unmap/remap ABA window
identified by document 230. The benchmark-only unlocked control uses the
identical body but omits only this outer lock; it is not dispatchable.

## VERIFIED -- exact fail-closed code guard

One guard is evaluated per helper hit while the outer memory mutex is held:

- exact 24 bytes at A+B+C (`entry+0x00..0x17`), split 16+8 for the
  allocation-free matcher;
- exact 12 bytes at E+latch (`entry+0x3F..0x4A`);
- excluded-call start `FF 75 08 8B` at `entry+0x18`;
- complete indirect CALL `FF 92 48 01 00 00` at `entry+0x39`;
- containing-function anchors at `entry-0x101` and `entry+0x76`.

Representative mutations in A, B, C, E, latch, both call anchors (including
the CALL displacement bytes at `+0x3D/+0x3E`), and both containing-function
anchors all reject with complete CPU/data no-commit. A second guard before
commit is unnecessary: CodePage mutation/removal uses the same mutex, which
remains held until CPU commit.

The dispatcher resolves RVA `0x0008E05E` in the already memory-keyed acknex
module path. A compile-time error prevents simultaneous enablement of
`BOXEDWINE_D3D9WEB_MATERIAL_SCAN_AOT` and the standalone
`BOXEDWINE_D3D9WEB_MATERIAL_LATCH_AOT`, because the fused helper already
executes the latch.

## VERIFIED -- differential and rejection fixtures

The relocated NormalCPU reference and production helper match complete
GPR/lazy-flag/segment/x87/SIMD/MXCSR state, successor presence, and 16 KiB data
memory for the existing eight full-iteration cases:

- equal taken/fallthrough and counter wrap;
- mismatch counter `<`, `==`, and `>` EBX;
- independent nonzero DS/SS/CS;
- both latch successors;
- exact counter/latch aliases on increment and reset.

Two additional partial aliases pass: write starts one byte before the latch
read, and one byte after it. Forwarding uses unsigned offset comparison
`(address-writeAddress)<4`, avoiding an overflowing `writeAddress+4` bound.

The production helper also rejects cross-page dword writes, read-only Ram, and
COW targets with complete CPU/data no-commit. The standalone document-229
fixture continues to cover lazy-zero, Code, invalid, permission/type/remap
staleness, and offsets `0xFFD..0xFFF` directly at the Write32Plan API.

A successful near-`UINT32_MAX` trace fixture is not representable: the trace
must read `[EBP+0x0C]` before writing `[EBP+8]`, so a counter at
`0xFFFFFFFC` already makes the parameter address wrap. Production's
conservative `addNoWrap` therefore side-exits before any commit.

## VERIFIED -- native lock-inclusive cost

The benchmark times one equal/taken iteration with setup and snapshots outside
the timer. Each of five independent Test/x64 processes used 257 warm-up and
4,097 measured triplets. The three timed variants are three NormalCPU blocks,
the identical production body with commit lock only, and production with the
continuous outer lock plus recursive Commit lock.

```text
process             1    2    3    4    5    median
NormalCPU ns       460  460  440  460  530      460
commit-only ns     130  120  120  120  130      120
outer-lock ns      130  120  120  130  130      130
```

The median production speedup is `460/130 = 3.538x`. The per-process outer
versus commit-only ratio is `1.000x..1.083x`, with median `1.000x` at this
timer resolution. These numbers include one exact guard, the outer mutex, the
recursive Write32 commit lock, reads, forwarding, write, state commit, and
successor decode. They are native steady-cache evidence, not browser FPS.

## Verification

```text
MSBuild BoxedWine.vcxproj /m:1 /p:Configuration=Test /p:Platform=x64
BoxedWine.vcxproj -> ...\x64\Test\BoxedWine.exe

BoxedWine.exe 13 1 1
Test D3D9Web Hot AOT Scan Body Fixture ... OK
0 tests FAILED

BoxedWine.exe 14 1 1  # repeated in five independent processes
Benchmark D3D9Web Hot AOT Material Scan ... OK
0 tests FAILED

BoxedWine.exe 0 16 1
...
Test D3D9Web Hot AOT Scan Body Fixture ... OK
Benchmark D3D9Web Hot AOT Material Scan ... OK
Test WASM Write32 Tier ... OK
0 tests FAILED
```

## Status

- **VERIFIED native production helper:** full bounded semantics, exact guard,
  Write32Plan integration, alias forwarding, rejection/no-commit, dispatcher
  RVA, macro exclusion, and outer-lock cost.
- **NOT VERIFIED browser/Emscripten:** no browser asset was built or run, so
  visual equivalence, live acceptance rate, multiplayer behavior, and FPS are
  unchanged and unverified.
- **NOT VERIFIED concurrent mutation fixture:** the outer-lock correctness
  follows the mutex discipline established in document 230; an adversarial
  two-host-thread blocking test was not added here.

