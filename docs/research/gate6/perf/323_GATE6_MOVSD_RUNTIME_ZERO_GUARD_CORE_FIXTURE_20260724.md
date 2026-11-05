# 323 — MRG core differential fixture: compiled zero-base route

Date: 2026-07-24

## Scope and result

**VERIFIED (private test build + browser):** the macro-gated MRG fixture
`testMultiThreadedJitMovsdRuntimeZeroGuard` compiled and its one selected
browser entry passed.  This is a narrow architectural-integrity gate only. It
does not publish MRG1, create a cache, enter replay, or permit an FPS sample.

Latest private browser witness (page-cross extension):

- `Build/TestMultiThreadedJitMovsdRuntimeZeroGuard1/boxedwine.html`
- Browser result: `Running 1 Test tests with 1 threads starting at 388`;
  `Movsd runtime-zero source-only same-entry page-cross matrix ... OK`;
  `Movsd runtime-zero ECX boundary matrix ... OK`;
  `Test Movsd runtime-zero guard ... OK`; `0 tests FAILED in 0s`.

The start index is runtime-build specific: source-array index 395 loses seven
conditional entries in this MT/Wasm test configuration, so the run-time index
was proven by the test name, not inferred from source numbering. The generated
Emscripten JS overwrites shell `Module.arguments` from the raw query string;
the working private URL form is therefore `?388&1&1`, not `?testArgs=...`.

## What the passing fixture proves

**VERIFIED:** `testMovsdRuntimeZeroGuard` creates the observed MOC3 source-only
B5 condition before compilation: DS is made sticky with a nonzero `setSeg`,
then returned to zero; ES has never been made sticky. The instruction is direct
`F3 A5` (EA32 REP MOVSD), and the test asserts the resulting compiled entry
exists before the transition sequence.

**VERIFIED:** the same compiled entry is exercised through live-base profiles:
both bases zero; DS nonzero; return to both zero; ES nonzero; both nonzero; and
return to both zero. It covers DF=0/DF=1 and overlapping/non-overlapping
buffers. Every invocation checks all eight GP registers, the copied region,
flags, `nextOp`, EIP, no bailout, and pre/post `pfnJitCode` identity. Thus the
warm zero arm and the nonzero exact-emulate arm do not silently replace the
published block in this core matrix.

**VERIFIED (second private browser run):** the fixture expanded its guarded
region to 4096 bytes and emitted the explicit browser witness `Movsd
runtime-zero ECX boundary matrix ... OK` before the final zero-failure line.
The same entry passed zero-base DF=0/DF=1 counts `0,1,255,256,300` and
nonzero-DS representatives `1,300`; every row retains the full architectural
and entry-identity checks above. The count-zero DF=1 start offset is explicitly
inert, avoiding fixture underflow.

**VERIFIED (latest private browser run):** before any ES-sticky profile is
installed, the same compiled source-only-sticky-DS entry executes a valid
page-cross matrix. It asserts `hasSetSeg[DS]` and `!hasSetSeg[ES]`, with live
DS/ES bases both zero, and copies three dwords across source/destination page
boundaries at `0x3fff`/`0x5fff`. Both forward REP and backward REP pass: the
forward case crosses in its first dword and the backward case crosses within
the REP on its final dword. The ordinary full-register, bytes, flags, EIP,
next-op, no-bailout and compiled-entry-identity checks remain active. This
closes valid page crossing for the narrow EA32 source-only MOC3 route.

**VERIFIED static:** the cold arm sets `OP_FLAG2_TRACED_STUB` before exact
emulation; warm runtime bases are loaded and OR-tested; only zero/zero calls
the existing `movsr`, while either nonzero uses `emulateSingleOp`. Scratch
registers are distinct and released on the structured branch exit. The private
build retains the legacy 54-export ABI and is not served as the accepted asset.

## Explicit limits

**NOT VERIFIED:** this is not yet a full same-block differential. It does not
cover address-size-16 CX high-half preservation or the `0x10000` wrap boundary,
protected-page partial fault, or self-modifying-code invalidation. Entry
identity is a strong correctness gate, but a worker-local Wasm-table dispatch
witness is still absent. It also does not provide MRG2 arm counters, cache-OFF
game integrity, record, replay, or any performance evidence.

The next fixture extension must remain macro-gated and fail closed:

1. Establish a NormalCPU oracle for the protected-page partial-fault row, then
   compare signal info, completed bytes, ESI/EDI/ECX, EIP and flags. Install
   any signal handler before B5 compilation and restore protection/action on
   all exits.
2. Add a warmed compiled SMC row that proves stale-entry invalidation/bailout
   and the subsequent re-decoded architectural result.
3. Treat a future address-size-16 or worker-table-dispatch proof as a distinct
   scope expansion; neither can be inferred from this EA32 core.

Only after all three rows pass may a separate private MRG2 counter diagnostic
open. MRG1 remains unpublished and FPS work remains forbidden.
