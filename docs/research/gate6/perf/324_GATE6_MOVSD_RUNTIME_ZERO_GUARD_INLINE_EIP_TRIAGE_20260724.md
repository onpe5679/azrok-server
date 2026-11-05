# 324 — Runtime-zero MOVSD: generated-inline witness and EIP triage

## Status

> **PARTIALLY SUPERSEDED by 339.** The 24-Jul MRGF3 browser block below is historical. Its direct browser gate closed on 25-Jul; remaining SMC/EA16/worker-table/MRG2 restrictions are unchanged.

**VERIFIED browser/static:** MRGF3 directly executed the intended generated zero-base scalar path and the candidate-gated normal-completion EIP repair. Both DF partial-fault rows retained saved EIP 0; the complete fixture matrix passed. The candidate remains unpublished; no cache, replay, or FPS run is permitted.

**VERIFIED direct browser (2026-07-25):** see 339 for the direct CDP textarea witness, exact target, fresh-profile HTTP path and artifact provenance.

### 2026-07-24 late execution status (historical; runtime block superseded by 339)

**VERIFIED build only:** isolated `Build/MRGF3` was force-rebuilt at 18:14:45--18:14:49 (HTML/JS/Wasm fresh). The browser execution gate did not run: after the local 8765 runtime service was restored, this automation session's browser URL policy rejected re-entry to the private test URL. The independent dynamic audit also verified that `emrun --no-browser` is only an HTTP server and that no native/Node/wasmtime runner can replace the browser pthread/broker test. Therefore there is **no MRGF3 runtime line** for DF0/DF1, EIP, generated-slow-write, or the full matrix.

**Historical NOT VERIFIED / fail-closed:** do not infer the staged EIP repair from the fresh artifact. This was resolved by the 25-Jul direct MRGF3 run in 339; publication/cache/replay/FPS remain forbidden for the separate remaining MOVSD scopes.

**VERIFIED late static audit:** `writeEip(B5+2)` is immediately after zero-arm `movsr`, while the faulting helper synchronizes B5 first and its Wasm exception cannot reach that store; `preCompile` still holds B5 until `postCompile`. Thus success is structurally B5+2 and a fault structurally retains B5. The fixture counter/layout is isolated to MRGF3. This is not emitted-Wasm proof. Normal MRG1 must remain unbuilt until MRGF3 browser proof; moreover, when its turn comes, MRG1 needs a force/clean link or its own broker-JS prerequisite because its incremental broker freshness is not yet explicit.

## Measurement first

The prior MRG core fixture was already measured in 323, so this card did not repeat its completed transition, ECX, or page-cross claims. It measured the missing generated-inline witness only.

Private target: testMultiThreadedJitMovsdRuntimeZeroGuardFixtureCensus; build directory Build/MRGF2; test entry 388; single worker.

The test-only BOXEDWINE_WASM_JIT_MOVSD_MRG_FIXTURE_CENSUS adds a CPU-local counter only to the generated non-custom slow-write arm for REP MOVSD. It is absent from ordinary guard and accepted builds.

## Direct browser result

The fresh-path MRGF2 browser run printed both required partial-fault rows:

- DF0: frame 11/2/F000A000, saved EIP 00000000, flags 000008D7, ECX 1, ESI F0008004, EDI F000A000, throw 1, handler reached/executed 1/1, bailout 0, generated slow write 1.
- DF1: frame 11/2/F000AFFC, saved EIP 00000000, flags 00000CD7, ECX 1, ESI F0008000, EDI F000AFFC, throw 1, handler reached/executed 1/1, bailout 0, generated slow write 1.

**VERIFIED:** each direction completed exactly one writable dword, faulted at the protected second destination, preserved the NormalCPU oracle signal frame and GP state, reached and ran the guest handler, and took exactly one CPU-local generated scalar slow-write arm. This excludes the earlier trace-stub/interpreter-only explanation for those rows.

## Defect found

The same MRGF2 run failed all successful both-zero EIP checks and both page-cross control-flow checks. The observed pattern was nextOp TestEnd with EIP still 0; memory, GPs, flags, entry identity, and no-bailout assertions did not fail.

**VERIFIED static cause:** generated inline movsr completes without interpreter NEXT. JitWasmCodeGen TestEnd installs nextOp and returns but does not write EIP, unlike the base JIT test endpoint. The prior emulate path advanced EIP to the B5-next boundary, hiding the defect.

## Staged fail-closed repair

The candidate-only implementation now:

1. assigns currentOp = op during JitWasmCodeGen preCompile only when BOXEDWINE_WASM_JIT_MOVSD_RUNTIME_ZERO_GUARD is enabled, so the shared scalar-string emitter receives decoded metadata;
2. keeps production cold traced-stub policy; only __TEST temporarily makes the first-hit MRG fixture compile the warm scalar body;
3. writes currentEip + op length - CSbase immediately after successful movsr inside the zero-base arm only.

Static audit confirms this placement is after successful inline completion, before TestEnd/direct exit, and outside the nonzero exact-emulate arm. A fault must transfer before the new EIP write; the next browser run must prove that condition with the existing DF0/DF1 frame checks.

**VERIFIED static build freshness repair:** Build/MRGF3 now explicitly depends on boxedwine-wasm-jit-module-broker.js. The earlier fixture-census build-directory name was the only listed broker prerequisite, so the new isolated target could otherwise relink stale pre-JS after a broker change.

### 2026-07-25 late static artifact and evidence separation audit

**VERIFIED static:** the fresh isolated MRGF3 artifact is
`boxedwine.wasm` SHA-256
`B3A75FEB32A6D21B7757A195E5A96B29B4635DB02F753D81824FB69363699EB4`
(2,436,113 bytes) and `boxedwine.js` SHA-256
`5D00FBD483749FBC01EBED62CEDD9961AE6FA9F657B013498EFC32BFEB949869`.
`WebAssembly.validate` accepts the Wasm. The exact target binds
`Build/MRGF3`, `__TEST`, MT/Wasm JIT, runtime-zero guard and the fixture census
(`project/emscripten/makefile:98-101`); its artifact timestamp is after the
relevant codegen/test/make inputs. This proves build provenance and Wasm
validation only, not macro presence in stripped output or runtime execution.

**VERIFIED static control flow:** live nonzero DS/ES selects exact emulate;
only the both-zero arm reaches `movsr` and the candidate EIP write after a
successful return (`source/emulation/cpu/wasm/jitWasmCodeGen.cpp:14212-14338`).
The generated scalar slow-write synchronizes state then calls the helper and
checks bailout before that outer commit (`:12098-12121`); taken bailout exits
the block (`:11675-11682`). Consequently the staged EIP commit is structurally
unreachable from nonzero, helper-fault, and bailout paths. This remains an
emitted-control-flow audit, not an observed Wasm execution.

**VERIFIED evidence separation:** MRGF2 remains its own historic witness. MRGF3 now has an independent direct CDP textarea witness in 339: exact entry banner, complete `OK`/`0 tests FAILED`, both DF rows/counters and same-entry partial-fault/page-cross/ECX markers. SMC, EA16 and worker-table dispatch remain outside that matrix.

## Gates before advance

- **COMPLETE:** MRGF3 fresh-path entry-388 direct browser run and complete matrix, including generated-slow-write=1 per DF row and partial-fault EIP 0, handler reach/execute and no bailout.
- Keep warmed compiled SMC invalidation/re-decode, EA16, worker-table dispatch, MRG2 counters, cache/replay, and FPS blocked. SMC is the next MOVSD-first fixture gate.
