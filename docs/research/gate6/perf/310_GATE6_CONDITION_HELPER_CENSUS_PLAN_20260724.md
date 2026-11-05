# 310 Condition-helper exact census plan

## Status

**VERIFIED static/build; runtime measurement NOT VERIFIED.**

## Motivation

The accepted runtime still has sixteen condition helper entries (`fn_12` through
`fn_27`). Prior cards independently settled P/NP, Z/NZ, B/NB and now S/NS,
but import-table membership is not an execution count: every grouped module
imports the common helper table. Therefore a new candidate may not be selected
from static import presence or from sampled profile output.

## Planned measurement

Build one private accepted-ABI2-shaped cache-off diagnostic that increments one
relaxed atomic U64 at every actual `wasmHelper_cond_*` entry and exports a
128-byte snapshot only under a dedicated macro and URL gate. It will use the
same visible PatHouse selection pulses and two explicit snapshot reads separated
by an uninterrupted scene interval. The artifact is coverage-only and cannot
be used for FPS.

Any follow-up requires all of:

1. nonzero **steady-scene** entry density for one condition family;
2. a direct static proof of a strictly smaller safe runtime-lazy subset; and
3. a fresh, separately documented fail-closed candidate contract.

The census must not reopen rejected parity, Z/NZ, B/NB, S/NS or dual-entry
cards merely because their helpers are present in the common table.

## Build isolation (2026-07-24)

The private ABI2-freeze-derived `ConditionCensus` runtime completed with
`-DBOXEDWINE_WASM_JIT_CONDITION_HELPER_CENSUS`. It adds exactly two snapshot
exports to the accepted ABI2 legacy set, validates with 56 Wasm exports, and
has no dual-entry glue binding. Private asset SHA-256 values are JS
`AE09D9351C5BB45CFF7449B998E15DCB673B9B0252B2C8F700631FE1109AEA03` and Wasm
`50A42A7C93726EEAF3D2A7F92AE54F828409BE18CD308B36BD32803C1DD61B2D`.

The page reader/URL fail-closed gate and browser measurement were initially
NOT VERIFIED; they are completed below.

## Exact dynamic helper census (2026-07-24)

**VERIFIED dynamic.** The condition-census runtime passed its explicit URL/
runtime ABI-1 gate, rendered visible PatHouse after the normal selection
pulses, and exposed only explicit snapshot refresh (no polling and no FPS
score). Counters are ordered `O,NO,B,NB,Z,NZ,BE,NBE,S,NS,P,NP,L,NL,LE,NLE`.

| condition | first snapshot | +15 s steady PatHouse |
| --- | ---: | ---: |
| O / NO | 9,514 / 4,235 | +1,339 / +780 |
| B / NB | 5,127,313 / 4,197,320 | +640,715 / +603,320 |
| Z / NZ | 21,048,304 / 616,355 | +9,000,882 / +177,342 |
| BE / NBE | 95,010 / 366,061 | +2,369 / +103,886 |
| S / NS | 0 / 200,576 | +0 / +10 |
| P / NP | 13,798,962 / 20,378,631 | +6,154,186 / +5,709,089 |
| L / NL | 797,569 / 454,109 | +88,700 / +70,015 |
| LE / NLE | 1,291,019 / 451,405 | +241,115 / +6,275 |

This is direct coverage evidence, not timing. Z/NZ and P/NP remain closed:
their separate candidates already removed these entries and were not adopted
by strict performance gates. B/NB likewise remains closed because its only
proved-safe zero-CF subset had exact zero dynamic coverage. The next static
audit is therefore limited to BE/NBE and L/NL/LE/NLE runtime-lazy contracts;
no candidate has been selected or built.
