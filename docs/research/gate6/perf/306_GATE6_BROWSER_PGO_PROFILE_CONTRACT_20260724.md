# Gate 6 - browser PGO profile contract

Date: 2026-07-24

## VERIFIED static environment and flag route

The installed Emscripten toolchain is 6.0.3 with LLVM 23
(`<home>\emsdk\upstream\bin\llvm-profdata.exe`). Its Clang supports
both `-fprofile-instr-generate` and `-fprofile-instr-use=<path>`.

The Emscripten makefile routes `OPTIMIZATION_FLAGS` into both compilation
(`CPPFLAGS`, line 469) and final link (`LDFLAGS`, line 472). Therefore a
separate ABI2-freeze PGO generation/use pair could keep the intended flag
contract isolated in separate build directories. This is only a possible
build route; it does not prove a valid profile exists.

## VERIFIED missing browser profile lifecycle

No current PGO target, `__llvm_profile*` export, profile flush/write bridge,
raw-profile download/retention manifest, or profraw-to-profdata merge script
exists in the makefile, page, shell, or runtime sources. The current link
configuration exposes `FORCE_FILESYSTEM`, `-lidbfs.js`, and `FS`, but has no
`syncfs` or profile-specific bridge. The existing Emscripten coverage-test
reference writes `default.profraw` under `NODERAWFS` plus `EXIT_RUNTIME`; that
is not a valid contract for this persistent browser 32-pthread game runtime.

The SDK does contain `__llvm_profile_reset_counters`,
`__llvm_profile_get_size_for_buffer`, and `__llvm_profile_write_buffer`, so a
buffer-based export route is technically available. It has not been connected
or dynamically tested here.

## VERIFIED decision: compiler PGO NOT READY; no build started

Starting a profile-generation build now would produce a profile that cannot
be recovered, attributed, hash-identified, merged, or proven to correspond
to the intended executable. That violates the compiler-card isolation and
fail-closed rules. No PGO build, served asset, cache, browser run, or FPS
sample was started.

The required pre-card sequence is:

1. A separately named ABI2-freeze PGO-generation target, low-priority
   single-job rebuild, and generated-glue verifier.
2. A C-exported buffer bridge with known length/capacity/status and a JS-side
   raw SHA-256/size manifest. File-exit behavior is not accepted as a
   substitute.
3. A dynamic safe checkpoint that quiesces the 32 worker threads before
   capture. The requirement follows because concurrent counter snapshot
   consistency is **INFERRED**, not established by the SDK symbol existence.
4. Immutable raw inputs followed by exact `llvm-profdata merge -sparse`,
   non-empty/show verification, input-list manifest, and profdata SHA-256.
5. A separate PGO-use target that applies the immutable profile to both
   compile and link, rejects profile-out-of-date/unprofiled diagnostics, then
   passes the ordinary ABI2 glue -> cache-off -> fresh record -> replay ->
   visible PatHouse -> A-B-A gates.

Until steps 1--4 receive static and dynamic proof, compiler PGO remains
**NOT READY** and must not consume the overnight browser measurement slot.

## Evidence-scope update (2026-07-25)

See 328 for the direct tool audit. LLVM instrumentation plus sparse merge is
source-verified; Emscripten `-sPGO` is explicitly unsupported. A successful
local `-fprofile-instr-use` compilation remains **NOT VERIFIED**, so do not
state profile-use support as a completed toolchain fact. The PGO-not-ready
decision is unchanged.
