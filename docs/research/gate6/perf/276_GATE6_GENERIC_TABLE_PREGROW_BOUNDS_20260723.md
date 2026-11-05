# 276. Gate 6 — generic dispatcher table pre-grow bounds removal

Date: 2026-07-23 KST

## Status

- **VERIFIED static:** The candidate changes only the 134 common generic dispatcher bodies. It removes `table.size`, `i32.lt_u`, the bounds `if`, and its matching `end`; `table.get` and `ref.is_null` remain.
- **VERIFIED static:** All 41,625 ordinary compiled functions, 32,439 direct-call patches, imports, exports, and non-code sections are identical between A and B. Reverse-normalizing the nine-byte dispatcher change reproduces all 134 A modules byte-for-byte.
- **VERIFIED runtime:** The release runtime grows each executing worker's local Wasm table to relocation capacity before marking any generic slot ready, and exposes an exact capacity capability checked by the page before enabling the candidate.
- **VERIFIED browser:** Both candidates preserve the accepted 1024x768 PatHouse walls, carpet, furniture, character face, and Korean UI with no visible rendering regression.
- **VERIFIED / REJECTED:** Adaptive A-B-A-B produced adjacent mean-FPS effects of +0.19% and -10.84%. Their two-pair median is -5.33%, so removing the dispatcher bounds check has no reproducible positive effect and is not adopted.

## Candidate and fail-closed gate

The baseline common dispatcher checks a dynamically supplied relocation slot in this order:

1. acquire the published guest `pfnJitCode` token;
2. validate the relocation-map entry;
3. check `slot < table.size`;
4. fetch `table[slot]` and reject a null reference;
5. perform `return_call_indirect` with the same slot. (Terminology corrected by
   direct dispatcher-byte/disassembly verification during 278.)

The test candidate removes only step 3. It does **not** assume that a shared published pfn implies a worker-local table entry. `table.get/ref.is_null` remains the worker-local readiness guard.

Growing the table at module link/start was rejected statically because it would also change the global next-slot sentinel. Instead, `wasmJitSlotReadyForWorker()` performs a one-time worker-local grow after the relocation allocator exists and before its ready-vector fast return. Failure returns false and leaves the compiled entry unavailable. The page additionally requires:

- the new runtime capability export to exist;
- its reported pre-grow capacity to exactly equal the relocation capacity;
- the cache manifest to declare `runtime-pregrown`.

Missing or mismatched capability fails closed before generic dispatch is enabled. Old manifests without the new field continue to use the checked dispatcher.

## Artifacts and structural proof

Runtime:

- stem: `boxedwine.upstreamjit61tablepregrow1`
- JS SHA-256: `9ADD40729434603BCB8621EB92270BF8088E8A2B4745C7DEE490FA3F09A0C08C`
- Wasm SHA-256: `9D1347C668819BA58E685F69617851A4D48B0A80459D6A187864DC33DE7FB5BC`
- relocation-map base: `12963560`
- relocation capacity: `262144`
- reported pre-grow capacity: `262144`

Caches:

| Condition | Artifact | SHA-256 | table bounds |
|---|---|---|---|
| A | `profiles/azrok-jit-grouped-commonfast64-depthlocal-pregrowrt1.zip` | `F161E681D00F0838D0A2C909A3CCF6BCC5A24FB31879210774F788EFDC51754A` | dispatcher checked |
| B | `profiles/azrok-jit-grouped-commonfast64-tablepregrow1.zip` | `AB62075D0BC7974AF77053E127C7B6E7BC9DD4AD92DAB7A36FCD8C185C2BA6E4` | runtime pre-grown |

Both archives contain 134 groups and 41,625 entries. Every B dispatcher is exactly nine bytes smaller. Reverse-normalizing B gives aggregate SHA-256 `824B7CCA...A10620`; structural errors were zero.

## Adaptive A-B-A-B measurement

The user-requested protocol was retained: one clean tab per condition, 30 one-second HUD reads, `document.visibilityState`, foreground application, and renderer CPU as covariates. No sample was discarded. All four windows were visible and had `WindowsTerminal` as foreground for 30/30 samples.

The user reported that the After Effects render ended before A2. A2 therefore directly exposed an environment drift that A1-B1 alone could not control. A mean drift was +11.18%, exceeding the +/-3% rule, so the test was extended to B2.

| Leg | mean FPS | median FPS | min--max | renderer CPU / 30 s |
|---|---:|---:|---:|---:|
| A1 checked | 38.7167 | 38.5000 | 37.4--40.8 | 121.500 s |
| B1 pre-grown | 38.7900 | 39.4000 | 34.8--41.4 | 125.609 s |
| A2 checked | 43.0467 | 42.6000 | 40.6--47.0 | 114.891 s |
| B2 pre-grown | 38.3800 | 39.4000 | 34.0--41.7 | 116.719 s |

Adjacent mean effects:

- B1 versus A1: `+0.1894%`
- B2 versus A2: `-10.8415%`
- two-pair median: `-5.3261%`

Adjacent median-FPS effects are `+2.34%` and `-7.51%`, also conflicting and non-positive in aggregate. Renderer CPU is worse in both B legs. The candidate is therefore rejected; the checked depth-local dispatcher from 275 remains the accepted semantic baseline.

## Next gate

The remaining per-tail reference readiness sequence (`table.get` plus `ref.is_null`) is larger than the rejected bounds check. The next candidate is a fail-closed worker-local installed-slot bitmap exposed through the CPU context: a byte may become one only after that worker installs the exact table slot, and a false byte must return to the existing outer C++ readiness path. Static proof must cover worker migration, publication invalidation, monotonic slot identity, and the absence of a stale-true path before any browser FPS run.
