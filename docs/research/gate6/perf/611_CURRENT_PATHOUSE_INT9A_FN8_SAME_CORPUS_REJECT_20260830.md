# 611 — Current PatHouse INT9A `fn_8` same-corpus candidate: reject

Date: 2026-08-30 KST

## Conclusion

- **VERIFIED implementation:** a current Touch2 sibling changes only the
  decoded `Int9A` dispatch inside the existing `helpers.fn_8` envelope from
  `NormalCPU::getFunctionForOp(op)` plus indirect call to direct
  `normal_int9A()`.  Every non-Int9A opcode retains the original route.
- **VERIFIED same corpus:** A and B load the byte-identical current cache
  `b007fa84...9035a`, 94 groups / 30,550 entries / 28,944 patches, relocation
  map `12968408 / 262144`.  The historical 154-group INT9A cache and `fn_36`
  helper are not used.
- **VERIFIED semantics:** the dedicated browser fixture covers direct INT9A,
  ordinary `fn_8` fallback, GP/segment/lazy-flag successor state, same-length
  SMC re-decode, and faults at all three stack arguments.  It reports zero
  failures.
- **VERIFIED visual:** every retained B1-A2-B2-A3-B3 measurement has a manually
  reviewed before/after pair showing the actual PatHouse room, rug, furniture,
  pink Azron, and HUD.  No transition/character-selection sample is included.
- **VERIFIED performance result:** retained control mean is 32.8667 FPS and
  candidate mean 32.4893 FPS, candidate/control = **-1.1484%**.  Four adjacent
  candidate effects are `+3.8236%, +5.8217%, -6.2463%, -6.0920%`; their median
  is **-1.1342%**.
- **REJECTED / NOT ADOPTED:** B is stable but does not follow the later control
  improvement.  It is neither a reproducible gain nor an epoch-making change.
  Production remains the original Touch2 runtime and currentabi1 cache.
- **NOT VERIFIED slowdown:** the signed adjacent median `-1.1342%` is inside
  the established ±3% noise band.  This rejects the candidate as an
  improvement; it does not prove a real performance regression.

## Why the historical candidate could not answer this question

The old `BOXEDWINE_WASM_JIT_INT9A_SPECIALIZED_HELPER` appends helper `fn_36`.
Only modules generated under that macro call it.  Its private cache has 154
groups / 48,902 entries / 41,721 patches, whereas every current group imports
exactly `fn_0..fn_35`.

The current hot block `v5-7bdd1130-98ec82c1` is in group 74 and contains one
`call helpers.fn_8` at guest `CD 9A`.  Merely loading the old runtime with the
current cache would therefore leave the hot call unchanged and would not be a
candidate test.

## Current-corpus implementation

Opt-in macro:

```text
BOXEDWINE_WASM_JIT_INT9A_FN8_DIRECT_DISPATCH
```

Inside the existing `CPU::runNextSingleOp()` decoded-op copy/catch envelope:

```cpp
if (op->inst == Int9A)
    normal_int9A(this, &o);
else
{
    o.pfn = NormalCPU::getFunctionForOp(op);
    o.pfn(this, &o);
}
```

This preserves the generated EIP write, dirty GP/segment synchronization, SMC
arm, normal exception catch, active-block write check, bailout, and lazy-flag
invalidation already surrounding `fn_8`.  It deliberately does not import the
historical `fn_36`, override `dynamic_int9A`, use bailout marker 2, or add a
production counter.

Candidate runtime:

```text
stem   boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2int9afn8direct1
JS     329817 bytes
SHA256 f9e52e6d03c33557999fbd5ee9c9bbd6f793563117f0b32bbaf69db1dee2b710
Wasm   3056455 bytes
SHA256 ffe65be2a442f23f0777ec5607571a7cd8902750b2427ff3a82f077ff7039af1
```

Build, staged, and HTTP bytes match.  Linked getters report:

```text
candidate ABI 1
map/cap       12968408 / 262144
next/depth    740 / 1660
bailout/pfn   132 / 12
```

The accepted runtime remains byte-identical:

```text
JS   329600 / 3396bf98e087d8190c120e204bf2e33a96ca68ccc5dd1eb39d14db49712c5ca6
Wasm 3056422 / d717235bce2663585291246ddc4528b5c2a609c704b3135f3244e60741efea96
```

## Fixture

The dedicated current-envelope fixture reports:

```text
Running 1 Test tests with 1 threads starting at 646
INT9A fn8 direct/generic/successor/SMC/fault OK
0 tests FAILED in 0s
```

Coverage includes:

1. direct INT9A state and host return value;
2. AAD as an ordinary non-Int9A `fn_8` user;
3. GP, DS segment, and lazy-ZF state consumed after INT9A;
4. live same-length `CD 9A -> MOV EAX,EAX` mutation and generic re-decode;
5. NormalCPU equivalence for `peek32(0..2)` protected-stack faults.

## Measurement identity

All retained rows use:

```text
app    Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts2_startersplash1_fastboot4
root   TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1-acp949-xim25koreanlocale2
cache  azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-currentabi1.zip
Edge   Default, fresh profile/process, visible, non-minimized, non-cloaked
scene  180 s settle + 20 s warmup + 45 s exact Present window
```

The first A1 row did show real PatHouse, but two Emscripten builds were active
during its 23.8622 FPS window.  It is retained only as a visual/function
witness and excluded from performance statistics.

## Retained B-A-B-A-B result

| Order | Condition | Presents / wall | FPS | Visual |
|---:|---|---:|---:|---|
| 1 | B1 fn8 direct | 1,443 / 45.009313 s | 32.0600 | PatHouse before/after |
| 2 | A2 control | 1,390 / 45.014032 s | 30.8793 | PatHouse before/after |
| 3 | B2 fn8 direct | 1,471 / 45.016382 s | 32.6770 | PatHouse before/after |
| 4 | A3 control | 1,569 / 45.016229 s | 34.8541 | PatHouse before/after |
| 5 | B3 fn8 direct | 1,473 / 45.003508 s | 32.7308 | PatHouse before/after |

Control drift is `+12.8721%`; candidate drift from B1 to B3 is only
`+2.0923%`.  The candidate first appears positive against the lower A2 but is
negative against the later A3.  Condition means and adjacent median both land
near -1.1%, within the existing ±3% noise band.  The correct decision is no
adoption rather than attributing the early pair to the code; a genuine
slowdown is not established.

## Next gate

Move to the independent i386 PIC-thunk caller-group clone candidate.  It
targets a larger current surface (1,209,674 owner-CPU entries, 5.9759%) and is
architecture-reusable.  Keep this INT9A candidate only as a verified negative
artifact; do not combine it with future candidates.

## Artifacts

- `tools/boxedwine_local/bwujit_threaded_abi/source/emulation/cpu/common/cpu.cpp`
- `tools/boxedwine_local/bwujit_threaded_abi/source/emulation/cpu/common/cpu.h`
- `tools/boxedwine_local/bwujit_threaded_abi/source/test/cpu/testCPU.cpp`
- `tools/boxedwine_local/bwujit_threaded_abi/source/test/testMain.cpp`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/makefile`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/verify-int9a-fn8-current-candidate.mjs`
- `tools/browser_diagnostics/Invoke-AzrokInt9AFn8Fixture.ps1`
- `artifacts/performance/regional_int9afn8_aba_actual_pathouse_20260830.csv`
- `artifacts/performance/regional_int9afn8_aba_actual_pathouse_visual-review.csv`
