# Gate 6 - ABI2 freeze compiler-flag card contract

Date: 2026-07-24

## VERIFIED static drift attribution

The accepted deployed `boxedwine.upstreamjit64fn6inlineabi2` JavaScript glue
has 33 logical public Wasm bindings (32 explicitly exported functions plus the
Emscripten proxy-main binding). Fresh FLTO/no-SIMD builds from the current tree
instead have 35. The exact two extra public bindings are:

- `_wasm_jit_mt_register_group_entry_pair`
- `_wasm_jit_get_register_thread_abi_version`

Both are unconditionally listed by the current Fn6 ABI2 make targets even
though their compile macro set remains legacy ABI2: it has neither
`BOXEDWINE_WASM_JIT_THREADED_BODY_ABI` nor
`BOXEDWINE_WASM_JIT_THREADED_TAIL_ABI`. The newer source line can therefore
look pair-capable to a loader despite not being the deployed ABI2 contract.

The accepted raw Wasm export count is 54 (53 functions plus table); fresh
no-SIMD is 56. FLTO additionally exposes the internal
`__emscripten_timeout`, yielding 57. Raw count is therefore diagnostic only
and is not a valid strict-equality gate for LTO.

## VERIFIED containment change

Three isolated targets now share an explicit 32-name historical ABI2 export
list that omits precisely the pair-registration and register-thread ABI
bindings:

| condition | target | flags |
|---|---|---|
| fresh control | `...Fn6InlineAbiFreeze` | `-O3 -msimd128` |
| LTO | `...Fn6InlineAbiFreezeFlto` | `-O3 -msimd128 -flto` |
| no SIMD | `...Fn6InlineAbiFreezeNoSimd` | `-O3` |

All retain the legacy ABI2 macro set, async ring, read-hot cache, broker
inputs, runtime methods, shell, and independent build directories. The
accepted deployed asset and cache remain untouched.

Independent review caught two containment defects before the fresh-control
output existed: the new targets were absent from the top-level `.PHONY` list,
and the first verifier only rejected three known newer bindings. `.PHONY` now
includes all three targets. The verifier now extracts every underscore-prefixed
`Module[...]` public binding and requires exact equality with the accepted
33-name set (including proxy-main), so any other new public export fails
closed as well.

## Required gates before any FPS sample

1. Build the fresh freeze control with `LOW_PRIORITY_JOBS=1` and validate its
   logical glue binding set against accepted ABI2: all 33 expected bindings,
   no pair/register-thread/threaded-GP ABI binding.
2. Cache-OFF visible PatHouse, fresh record/replay, and loader manifest proof
   must pass on the freeze control. The legacy v2 one-token loader branch is
   the only permitted manifest shape; no dual-entry registration may occur.
3. Only then build/validate each isolated flag variant and run its own
   cache-OFF/replay integrity gate.
4. Score each card using the freeze control as A, candidate as B, and strict
   visible 30-second direct-Present A-B-A. Never replace the deployed ABI2
   asset during this work.

PGO remains NOT STARTED: profile flush, collection, and `llvm-profdata` merge
are still not a verified reproducible browser contract.

## VERIFIED independent loader/cache audit

The PatHouse replay loader accepts legacy when no pair declaration is present
and then checks only manifest version 2 plus
`source.runtimePublication.tokenWords === 1`. It does **not** require a
runtime pair getter value of zero. This matters because the current C++
register-thread getter returns one under multithreaded JIT even for legacy ABI2.
The glue verifier is consequently a mandatory fail-closed boundary, not a
redundant check: it rejects the pair getter, register-thread getter, and
threaded-GP getter by public name before a candidate can reach record/replay.

The accepted cache's directly extracted legacy contract is version 2,
`boxedwine-wasm-jit-grouped-cache`, cache version `v5`, one publication token,
and no `runtimeRegisterThreading`, `threadedGpAbi`, runtime threaded-tail,
runtime-lazy-Z/NZ, `typedExportName`, or `threadedExportName` metadata. A
freeze record/replay must reproduce that absence as well as the ordinary ABI2
generic/direct/inline-fetch getters and offsets. The v2 loader registers only
single-slot entries and has no hidden pair call.

Fresh records overwrite the shared raw-record pathname. Before any subsequent
record, preserve the freeze raw ZIP under a unique name, generate a uniquely
named grouped ZIP from only that raw record, and verify its v2/no-pair manifest
before replay. Cache-off record and replay are mutually exclusive by page
contract.

## VERIFIED fresh-control build and static gates

The isolated control completed as one low-priority forced-rebuild job with no
compiler or linker error. Its `boxedwine.wasm` is 3,048,478 bytes and passes
`WebAssembly.validate`. Its generated glue passes exact equality with the
accepted 33-key public binding set: 32 explicit legacy functions plus
`__emscripten_proxy_main`, with no pair/register-thread/threaded-GP binding.
The accepted dual-entry replay ownership regression (5 contract + 3 ownership
cases) and threaded-GP loader regression (9 cases) still pass after the
makefile/verifier change. Compiler diagnostics were only existing unused
lambda-capture warnings and the known pthread+memory-growth warning.

This clears build/static containment only. No candidate asset has been copied
to the served directory, no cache has been generated, and no browser/FPS
measurement has been performed.

## VERIFIED cache-off and fresh-record control path

The separately served freeze-control JS/Wasm pair is byte-identical to the
validated build output. A visible cache-off run, with no replay archive,
completed original character selection and rendered the full 1024x768
PatHouse 3D scene. A second visible `jit-record=true&jitCacheUrl=off` run
reached the same scene and uploaded a 45,198,400-byte raw archive. It was
immediately copied to
`abi2freezecontrol1-record-20260724-080517.zip` with matching SHA-256
`F10740CB889A096E127E13DE2F9840641AE4A93072CCA4254468FD4BE699F55F`.

The raw archive has no source/layout object, so the cache pipeline correctly
rejected a first attempt without explicit runtime offsets. This is fail-closed
behavior, not a rendering failure. The retried low-priority pipeline receives
only the accepted ABI2 verified offsets: pfn 12, nextOp 740, depth 1660,
bailout 132, reloc-map `12964392/262144`, and inline-fetch layout
`thread728/terminating72/process36/eip112/cs48/big1632/opCache652`, together
with the accepted generic limit-64/depth-local/inline-fetch options. It must
still produce and pass an exact v2/no-pair manifest before replay.

## VERIFIED fresh grouped cache and offline replay gate

The explicit-layout retry completed with no pipeline error. The preserved raw
record produced `azrok-jit-grouped-abi2freezecontrol1-inlinefetch2.zip`
(5,469,815 bytes, SHA-256
`380FFD2AD89CF65A381A4DE51ECD711B8E246F15E70F8A30675DCED4336A554D`):
34,240 input blocks, 109 groups, 34,240 entries, and 27,942 patches. Its
generic dispatcher rewrote 245,400 common tails at the accepted limit 64.

`verify-abi2-freeze-cache.mjs` is now a separate fail-closed offline gate. It
uses an explicit expected reloc-map base, passes the accepted inlinefetch2
cache with its `12964392` value (134/41,625/32,439), and validates the
remaining new-freeze cache structure (109/34,240/27,942). Beyond the page
loader's count check, it requires
exact legacy-v2/no-pair metadata, all generic/inline-fetch offsets and modes,
exact ZIP group paths, each group `WebAssembly.Module` validation, entry
function-export presence, globally unique v5 keys, valid target keys, and the
same `i32.const` patch-marker bounds test used by the C++ registrar.

This clears offline cache integrity only. Replay must still show legacy-v2
registration, exact 109/34,240/27,942 browser datasets, and visible PatHouse
before any compiler-flag A-B-A can begin.

## VERIFIED first replay rejection and corrected runtime layout

The first freeze grouped ZIP was rejected before registration by the page's
generic-ABI guard: its accepted-ABI2 reloc-map base `12964392` did not equal
the live freeze runtime getter `12968408`. The same direct runtime check
confirmed nextOp/depth/bailout/pfn/capacity remain
`740/1660/132/12/262144`. No group registered and no performance sample was
taken. This is a required fail-closed source-generation-layout drift, not a
rendering or cache-corruption result. A fresh uniquely named cache must use
the measured freeze base `12968408`; the offline verifier now requires the
base explicitly rather than silently inheriting the accepted value.

## VERIFIED corrected cache replay and PatHouse integrity

The distinct R2 pipeline used the directly measured freeze reloc-map base
`12968408` and produced
`azrok-jit-grouped-abi2freezecontrol1-inlinefetch2r2.zip`
(5,469,806 bytes, SHA-256
`B3AD8FACEA8C8D1513CC07F3C9E8EAAC05F7D1902A70C8B773E57A5D708874C4`).
The explicit-base offline gate passes it as exact legacy v2/no-pair:
109 groups, 34,240 entries, 27,942 patches, and all 109 group Wasm modules
validated. Its measured generic layout is
`nextOp/depth/bailout/pfn/map/cap = 740/1660/132/12/12968408/262144`; the
inline-fetch layout remains `728/72/36/112/48/1632/652`.

The visible R2 browser replay registered the legacy-v2 cache with the same
109/34,240/27,942 counts, then completed normal existing-character selection
and rendered the reference PatHouse 3D scene. The directly captured frame
shows the in-scene avatar, HUD, menu and room geometry at CSS 1024x768; it is
not a loading or selection screen. Runtime logs after entry contain no error
level records and the latest async-ring window reports 120 submitted/120
reaped, zero gaps/reorders/errors. This clears the freeze-control
cache-off-record-pipeline-replay rendering gate. It is **not** a performance
sample: no 30-second Present result is claimed.

The accepted deployed ABI2 asset remains unchanged. Future compiler-flag
legs must each generate, explicitly validate, and visibly replay their own
fresh cache with their own directly measured layout; the scored comparison is
fresh freeze control A versus one such candidate B, never a cache or artifact
crossed with the deployed accepted layout.

## VERIFIED independent compiler-card static audit

An independent source audit confirms all three freeze targets use the same
32-name `ABI2_LEGACY_EXPORTED_FUNCTIONS` list, and that the dual-entry
pair/register-thread/threaded-GP exports are absent. Control and FLTO have
identical compile and link contracts except `-flto`; noSIMD has the same
contract except removal of the `-msimd128` compile and link flag. All three
names are present in `.PHONY`, recursive target dispatch, and the JIT-broker
dependency set, so a misspelled target cannot silently fall through to a
different build path.

The glue verifier proves only the generated public `Module["_..."]` binding
set, not provenance of the candidate JS/Wasm or raw internal Wasm ABI. The
cache verifier similarly proves declared structure and Wasm validity, not a
candidate runtime getter relationship by itself; its reloc-map base is an
explicit caller argument. Therefore each candidate must retain the full
cache-off -> fresh record -> directly read candidate getter -> pipeline ->
offline verifier -> visible replay sequence. The first old-map rejection
demonstrated why this dynamic binding cannot be inferred from a manifest.

## VERIFIED FLTO candidate build and replay integrity; performance pending

The single-job, nice-19 FLTO build completed with no compiler/linker errors;
only the known unused lambda-capture diagnostics and the pthread plus memory-
growth warning remained. The 3,549,167-byte Wasm validates, and its glue has
the exact 32-explicit/33-public legacy binding set. The separately served
asset hashes are JS `0AB2BCDA673347B7262C0DA52E65E596A0BF6E24C84C16FCDADC89D58B628CED`
and Wasm `FB7D6500C0726DE21B68F51939BFE9B6E609F1AA680353FB77A8B91323984158`.

A visible cache-off FLTO run and a separate visible recording run both
rendered PatHouse. The raw record is preserved as
`abi2freezeflto1-record-20260724-090000.zip` (45,155,636 bytes, SHA-256
`72821DE6E5993F6FD467C643447FA9F44AB95D91198277CB8D11053CBC6C8EB8`).
The first grouped cache used the freeze-control map base and was correctly
rejected by the FLTO runtime guard: live `12965240` versus cache `12968408`.
It remains preserved as a fail-closed negative artifact.

FLTO R2 uses the observed live map base `12965240`, passes the explicit-base
offline verifier (109 groups, 34,207 entries, 27,948 patches, 109 modules),
and has SHA-256 `FC01C7BD3D5B8703410660CD4F1C49221C21E53AE2A91460F2601F46BF3D1299`.
Browser replay registered the same legacy-v2 counts and visibly reached full
CSS-1024x768 PatHouse with no error-level console entries and a clean async
ring window. This is integrity-only; a fresh-control A-B-A begins next.

## VERIFIED FLTO A-B-A performance: NOT ADOPTED

The scored comparison used only visible (`capVisible:true`, document visible)
PatHouse legs after each fresh replay. Direct 30-second Present results were
freeze control A1 `41.00` FPS (1,230 / 30.001 s), FLTO B `41.10` FPS
(1,233 / 30.000 s), and fresh freeze control A2 `41.10` FPS
(1,233 / 30.004 s). The two adjacent candidate-relative effects are +0.24%
and 0.00%, both inside the predeclared +/-3% noise band. FLTO therefore has
no demonstrated uplift and is not adopted; the accepted deployed ABI2
artifact remains unchanged.

Two start attempts observed a false browser visibility capability immediately
before capture (one FLTO, one A2). They were explicitly discarded; after
visibility was restored and re-verified, replacement captures above were used.

## VERIFIED noSIMD build and replay integrity; performance pending

The separate noSIMD target completed as one nice-19 job with no compiler/linker
error. Its 3,038,453-byte Wasm validates and its glue matches the exact
32-explicit/33-public legacy binding set. The served asset hashes are JS
`80195DB565C5000935130E534F4724EC1570DFE9F6D6FAB85C02665739DB0572` and
Wasm `935D7FD5832C8E22F2B623B5AFD52C30756232918258930C62CC62C74DBD5046`.

Visible cache-off PatHouse and a separate fresh recording run passed. The raw
archive is `abi2freezenosimd1-record-20260724-093000.zip` (39,915,657 bytes,
SHA-256 `3A0B3FA34B6D0983B06887515717C4281A04B062BF8D173E2A3120EC369B91EE`).
Its grouped cache uses the control-compatible map base `12968408`, passes the
offline legacy-v2/no-pair verifier at 97 groups / 30,763 entries / 27,519
patches, and has SHA-256
`BB6A2804DC58BCCD245096B5ECBB7648A95AAABD91B10AAA246C3DF039F4A298`.
Browser replay registered those exact counts and visibly rendered full
CSS-1024x768 PatHouse. No noSIMD FPS result is claimed yet; fresh-control
visible A-B-A is the next gate.

## VERIFIED noSIMD strict A-B-A; NOT ADOPTED

With no build or cache-generation CPU active, one renderer tab was kept at a
time and each leg used normal selection pulses (100,500 then 90,722) before
the full PatHouse scene. Immediately before each capture the browser
visibility capability and `document.visibilityState` were both `true`/
`visible`; the rendered game canvas was CSS 1024x768. Loading, selection and
transition frames were excluded. Console error count was zero and the final
async-ring samples had zero gaps, reorders and errors.

The legs used the fresh freeze control URL/stem/cache (`boxedwine.abi2freezecontrol1`,
`azrok-jit-grouped-abi2freezecontrol1-inlinefetch2r2.zip`) for A1/A2 and the
independent noSIMD URL/stem/cache (`boxedwine.abi2freezenosimd1`,
`azrok-jit-grouped-abi2freezenosimd1-inlinefetch2.zip`) for B. B logged
`AZROK_JIT_REPLAY_REGISTERED groups=97 entries=30763 patches=27519`; the
control fresh replay/cache identity and legacy-v2 ABI were verified in its
earlier integrity gate. All three legs visibly rendered the full PatHouse
scene before capture.

| Leg | Direct visible 30-second Present result |
|---|---|
| A1 freeze control | 44.60 FPS (1,338 presents / 30.001 s) |
| B noSIMD | 39.90 FPS (1,197 presents / 30.001 s) |
| A2 freeze control | 41.90 FPS (1,257 presents / 30.002 s) |

The adjacent effects are B/A1 -10.54% and B/A2 -4.77% (candidate-relative
form, B divided by following control). Both are negative and outside the
plus/minus 3% noise band, so this is not an environment-drift ambiguity and
does not need A-B-A-B extension. Removing `-msimd128` is therefore **NOT
ADOPTED**. The noSIMD artifacts remain quarantined test inputs only; accepted
ABI2 stays untouched.
