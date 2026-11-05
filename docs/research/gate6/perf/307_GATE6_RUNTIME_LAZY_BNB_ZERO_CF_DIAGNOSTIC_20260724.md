# Gate 6 - runtime-lazy B/NB zero-CF diagnostic gate

Date: 2026-07-24

## VERIFIED static candidate boundary

The accepted inlinefetch2 replay contains 643 static condition-helper call
sites for B/NB: 100 `fn_14(B)` and 543 `fn_15(NB)` sites, spread across
66 of 134 grouped modules (43,762,106 bytes total Wasm). This is a smaller,
separate condition family than the already rejected P/NP and Z/NZ cards.
Static site count is not execution frequency and is not performance evidence.

`getCondition()` can already resolve compile-known conditions, but a block
entry/merge/bailout may carry `FLAGS_NULL`, where B/NB remains a helper call.
The only proposed safe producer subset is the 12 forms that architecturally
set CF to zero: OR, AND, XOR, and TEST at b8/b16/b32 width. SAR is excluded:
its CF is the shifted-out source bit, not a constant. For these
only, a later pure-Wasm value may be 0/1 without consulting a lazy helper.
All remaining CF enum cases (including ADC/SBB, nonzero/unknown shifts, old-CF
and CFOF paths) must keep the existing `fn_14`/`fn_15` helper fallback.

## VERIFIED decision: measurement-only gate first

No B/NB inlining, ABI export, manifest feature, cache artifact, or browser
FPS candidate is introduced by this document. The next permissible change is
an exact U64 diagnostic that separately counts B/NB helper executions and
the 12 zero-CF producer opportunities during a normal cache-off/replay
PatHouse run. It must not alter the accepted runtime path.

Only if direct dynamic counts establish material coverage may a later
implementation add a separately named manifest/runtime feature with loader
fail-closed rejection on mismatch, followed by static audit, regression,
cache-off integrity, fresh replay and A-B-A. Full-CF-family inlining is not a
safe follow-on from this evidence.

## IN PROGRESS diagnostic implementation

A separately named freeze B/NB-counter target and private four-U64 snapshot
API have been added in the working tree. It counts exact B, NB, B-zero-CF and
NB-zero-CF helper entries; the latter two admit only lazy types OR/AND/XOR/
TEST at all three widths. This is diagnostic code only and does not alter
the accepted target or exports.

The first build launch through plain Windows `make.exe` was rejected before
compilation because that shell lacked the makefile's required `grep` command.
A Git-Bash retry reached compilation but was stopped before artifact creation
after static audit found two defects: SAR was incorrectly treated as constant
CF=0, and the Windows recursive target failed to pass its target-specific
variables to the inner make. Both defects were corrected before a new build
was permitted.

## VERIFIED diagnostic build and static gate

The corrected Git-Bash single-job build completed successfully with only
pre-existing warnings. The private diagnostic artifact is valid Wasm
(`3,048,766` bytes); its Emscripten glue exposes exactly the accepted 33
public bindings plus the two named B/NB counter exports (35 total), with all
three forbidden dual-entry exports absent. The snapshot ABI is four U64
fields (`B`, `NB`, `B-zero-CF`, `NB-zero-CF`) at offsets 0/8/16/24.

The diagnostic reader was exercised cache-off only. Its ABI reports v1 and
rejects a partial export pair; the accepted stem reports v0 and never loads
the diagnostic artifact. The first in-app tab disappearing supplied no
browser-console, HTTP-server, compiler, or source-level causal evidence and
the immediately repeated run reached stable 1024x768 PatHouse, so it is not
attributed to the counter build.

## VERIFIED dynamic result: REJECTED before candidate implementation

Visible cache-off PatHouse reached a CSS 1024x768 main canvas after the normal
selection pulse sequence `(100,500)` then `(90,722)`. The B/NB counters were
read from the page-owned snapshot after scene stabilization and after both
pulses:

| observation | B | NB | B zero-CF | NB zero-CF |
| --- | ---: | ---: | ---: | ---: |
| stable scene before selection | 607,743 | 2,153,974 | 0 | 0 |
| after `(100,500)` | 630,059 | 2,218,938 | 0 | 0 |
| after `(90,722)` / PatHouse | 4,915,067 | 2,937,537 | 0 | 0 |

Thus the tested run executes at least 7,852,604 B/NB helper entries but none
of the exact 12 architecturally-zero-CF producer forms. The dynamic coverage
of the only safe B/NB inline subset is exactly zero, so no pure-Wasm B/NB
candidate, manifest feature, cache, replay, or A-B-A is warranted. This card
is **REJECTED by zero applicable executions**, not by a performance result.

The counter target and page reader were removed from the accepted path after
recording this result. The private built binary remains as an unreferenced
local artifact because the environment rejected its deletion; no page, target
or accepted manifest can load it.
