# 309 Runtime-lazy S/NS helper scope

## Status

**VERIFIED static; exact runtime coverage NOT VERIFIED.** This is an
independent post-301 candidate-discovery measurement. It does not alter the
accepted ABI2 runtime, cache or FPS baseline.

## Static evidence

`JitWasmCodeGen::getCondition` already emits pure Wasm S/NS when
`currentLazyFlags` is any result-based b8/b16/b32 flag producer: it loads
`CPU::result.u32`, masks the sign bit, and returns nonzero (S) or zero (NS).
This covers ADD/OR/ADC/SBB/AND/SUB/XOR/INC/DEC/SHL/SHR/SAR/CMP/TEST/NEG at b8;
the corresponding b16 forms plus DSHL/DSHR; and the corresponding b32 forms
plus DSHL/DSHR. No C++ helper or generic all-GP sync is emitted in that branch.

The retained helper table slots are `fn_20` (S) and `fn_21` (NS), directly
calling `CPU::getSF()` / its negation and writing only `CPU::tmpReg`. Current
accepted grouped-cache static inspection reports three S and 52 NS helper
imports (55 sites total across 39 groups). These are therefore unknown or
non-result lazy-state paths, not a safe compile-known producer set that can be
removed by another local pattern match.

## Required next evidence

Build a private accepted-ABI2-shaped, cache-off diagnostic with two relaxed
atomic U64 counters at the actual `wasmHelper_cond_S` / `wasmHelper_cond_NS`
entries and a distinct snapshot ABI. It must prove exact `0/0` or nonzero
process-lifetime helper entries after normal visible PatHouse selection pulses
and an uninterrupted scene interval. The counter artifact must not produce an
FPS sample. Only a nonzero result can justify considering a runtime-lazy S/NS
implementation; zero coverage rejects the card before candidate code/cache
generation.

## Diagnostic implementation (2026-07-24)

**VERIFIED static/build/browser; S/NS candidate NOT ADVANCED.** A new private
`Fn6InlineAbiFreezeSnsCounters` target derives its normal exports from the
accepted ABI2 freeze list and adds exactly two S/NS snapshot exports. Its
separate `BOXEDWINE_WASM_JIT_RUNTIME_SNS_COUNTERS` macro only replaces the
actual `fn_20`/`fn_21` helper bodies with semantically identical bodies that
relaxed-atomically increment U64 counters before the original lazy-flag read
and `tmpReg` write. The page requires the explicit
`runtimeLazySNSCounters=1` URL switch to match runtime ABI version 1; a
counter runtime without that switch, or the switch with a normal runtime, is
rejected before guest startup. The reader is explicit-refresh only, so its
host reads are not part of an FPS measurement.

`verify-runtime-lazy-sns-counter-loader-gate.mjs` passed five positive and
negative URL/runtime/export cases plus static source and makefile fragment
checks. The low-priority two-job rebuild completed and produced private stem
`boxedwine.upstreamjit64fn6inlineabi2snscounters1` (JS SHA-256
`7D074ECADE80982E37DDAAC90A45B516BE4A81FF7A529D3A22DD8DB804FB248D`, 327,254
B; Wasm SHA-256
`439F6F252CD500AD735785377BC051F8B776FEA4FFA59D3D4BAA21842DC77DAA`,
3,048,557 B). The Wasm validates with 56 exports; glue exposes both counter
functions and exposes none of the three dual-entry public bindings. No
browser cache or FPS result is claimed yet.

## Exact dynamic helper-entry coverage (2026-07-24)

**VERIFIED dynamic.** The private counter runtime booted only with
`runtimeLazySNSCounters=1`, reported counter ABI 1, and reached the normal
visible 1024x768 PatHouse 3D scene after the usual `(100,500,140 ms)` then
`(90,722,140 ms)` selection pulses. The page refresh control is explicit
(there is no counter polling): its first post-scene snapshot was exact
`fn_20(S)=0`, `fn_21(NS)=200,587`. After a further uninterrupted 15-second
visible PatHouse interval, a second explicit snapshot was `0,200,607`.

Thus S has zero observed coverage and is excluded from any candidate. NS is
nonzero over process lifetime but increased by only 20 during the 15-second
steady 3D interval (1.33 calls/s). This proves a NS-only runtime fallback is
the sole possible follow-up scope. It does **not** establish a measurable FPS
benefit in the scoring scene, so this card is not advanced to candidate/cache/
FPS work. The diagnostic runtime, including its atomic helper boundaries and
UI refreshes, is not a performance artifact.
