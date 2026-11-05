# 365 -- FISTP FQF1 NormalCPU fault fixture (2026-07-25)

Status: **VERIFIED -- private NormalCPU fault oracle; FQ1 outcome census may reopen**

## Purpose

364 proved that a generic `wasmHelper_emulateSingleOp` catch cannot classify
the NormalCPU FISTP destination-write fault: `CPU::runNextSingleOp` owns and
absorbs that throw.  FQF1 is a separate private test-only path to witness the
actual `FNINIT -> FILD m64 -> FISTP m64` store fault, signal frame and no-FPOP
state before designing an FQ1 outcome counter.

## Implementation and build evidence

- **VERIFIED static:** FQF1 uses `BOXEDWINE_DIRECT_NORMAL_DISPATCH` plus
  `BOXEDWINE_FISTP_QWORD_FAULT_ORACLE`, a distinct `Build/FQF1` test target,
  Wasm exceptions, and a NormalCPU route.  It is not an Azrok runtime stem,
  exports no census ABI and cannot create/replay a cache.
- **VERIFIED build:** the private Wasm/JS/HTML linked successfully once
  (Wasm SHA-256 `C0168645D955665F32AB2310F03B476AE8ADB98F1C80FB3D09E535D41C3AAA0E`).
  Existing warnings are only the known unused lambda captures and
  `pthread + ALLOW_MEMORY_GROWTH` warning.
- **VERIFIED direct browser / rejected fixture row:** the sole CDP page was
  navigated to the served FQF1 file and executed exactly one test.  It failed
  at `fistp qword fault oracle decode`, not at a guest fault or FPU assertion.
  The first fixture incorrectly assumed its first decoded op was FILD, while
  the intentionally emitted `FNINIT` precedes it.  No FISTP outcome is
  published from this failed row.

## Corrections and final private artifact

The fixture now requires the exact decoded chain
`FNINIT -> FILD_QWORD_INTEGER -> FISTP_QWORD_INTEGER`, pins all three to
NormalCPU dispatch, and sets saved-EIP expectation to the sum of FNINIT and
FILD lengths.

- **VERIFIED static P0 repair:** the first corrected rebuild was stopped
  before use after review found that `emitMemModRM` consumes a DS-relative
  displacement, while the fixture had supplied a linear `TEST_HEAP_ADDRESS +
  0xa000`.  The final source emits `destinationOffset=0xa000`, derives
  `destinationLinear=addressOf(destinationOffset)` exactly once, and uses
  that linear address for `mprotect` and `siginfo` comparison.  It also
  preloads and post-checks an independent qword guard, so a failed store must
  leave the destination unchanged.  This repair is test-macro-only.
- **VERIFIED build/served bytes:** a fresh nice-19, one-job rebuild completed
  with only the existing unused-capture and pthread-memory-growth warnings.
  Current FQF1 HTML/JS/Wasm are 200 from 8765 and byte-identical to disk;
  their SHA-256 values are respectively
  `D9A124FF9ABFB0F8D7F0F6539B043ECB9F6E64DEED9FFBE7D1BAC3A04FDCF12E`,
  `A584417F85BCC3ACCACEB6B34A8B49CE6E990B7E19CE57C64FDE6FE0559A9B46`,
  and `1AAC93E5B9A58D1084CD5C86CA1D3AEFD353095EFFFDAA1D0B7162048DEBB639`.

## Direct browser closure

- **VERIFIED direct browser:** the sole existing CDP page was forced to
  reload FQF1 with cache bypass; `document.visibilityState` was `visible`.
  Direct `textarea#output` evidence is:

  ```text
  FISTP qword NormalCPU write-PF eip=00000008 expected=00000008 top=7 tag=0 throw=1 handler=1
  Test FISTP qword fault oracle ... OK
  0 tests FAILED in 0s
  ```

  The passing oracle internally requires `SIGSEGV`, `SEGV_ACCERR` (code 2),
  the exact linear destination address, saved EIP 8, NormalCPU throw 1,
  handler completion, a nonempty ST0 before handler execution, and the
  unchanged destination guard.  It therefore closes only the required
  NormalCPU write-page-fault / store-before-pop boundary from 364.

FQ1 may now be redesigned to capture outcomes at this proven fault-delivery
boundary.  It remains a private diagnostic: cache creation/replay and FPS are
still forbidden until its own ABI, static audit and visible cache-OFF runtime
gate pass.
