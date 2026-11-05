# 367 -- FISTP FQF2 generated-fallback fault closure (2026-07-25)

Status: **VERIFIED static/direct browser -- FQ1 cache-off census gate reopened**

## Scope

FQF1 (365) proves the direct NormalCPU store-fault semantic.  This separate
test-only FQF2 target proves that the real uncached generated Wasm fallback
reaches that same operation-local call/catch boundary without treating helper
return or later FPU state as an outcome signal.

## Fixture isolation and static gates

- **VERIFIED static:** FQF2 is a new `Build/FQF2` target with
  `__TEST + BOXEDWINE_MULTI_THREADED + BOXEDWINE_WASM_JIT +
  BOXEDWINE_WASM_JIT_FISTP_QWORD_FIXTURE`; it deliberately excludes direct
  NormalCPU dispatch.  Source-level `#error` gates reject non-test/non-MT/
  non-Wasm builds and known census, profile, MOVSD guard, FQF1 and direct
  dispatch mixing.  No accepted runtime stem, asset, cache ABI or export
  changes.
- **VERIFIED static:** generated `emulateSingleOp` overwrites a FQF2-private
  FISTP ticket on *every* generic helper call; helper entry records only the
  exact FISTP+magic ticket.  `CPU::runNextSingleOp` copies that predicate
  before `o.pfn`, records normal immediately after return or fault inside the
  same catch, then consumes it.  This does not classify from helper return.
- **VERIFIED static P0/P1 repairs:** a caught ticket sets private bailout=2.
  The generated post-helper arm clears bailout and active-block, then returns
  directly without the ordinary SMC successor-EIP rewrite.  Thus signal
  handler EIP is preserved.  The fixture uses a distinct handler EAX marker,
  checks saved EIP 8, SIGSEGV/SEGV_ACCERR, exact destination, unchanged qword
  guard and nonempty ST0/top=7; it cannot pass merely by falling through the
  original TestEnd successor.

## Build and served-byte proof

- **VERIFIED build:** fresh nice-19, one-job FQF2 build completed with only
  existing unused-capture and pthread-memory-growth warnings.
- **VERIFIED served bytes:** 8765 returned 200 and byte-identical files:
  HTML `D9A124FF9ABFB0F8D7F0F6539B043ECB9F6E64DEED9FFBE7D1BAC3A04FDCF12E`,
  JS `5540A6CE40FDE7E81D69E5C7318C96CAC350476ABCF90ECFB486A7D29F2669B2`,
  Wasm `AB869B8D6BBC237F570DB1B901144E3A5B95081C9BAAFA3B0530ED720ACA0137`
  (2,436,481 B).

## Direct browser closure

The sole existing CDP page was navigated to exact FQF2 entry 504 and read via
`Runtime.evaluate`; `document.visibilityState=visible`.  Its textarea output:

```text
Running 1 Test tests with 1 threads starting at 504
[WASM JIT] first JIT block executed, tableIdx: 8189
FISTP qword generated fallback entry=1 normal=0 fault=1 top=7 tag=0
Test FISTP qword generated fallback fixture ... OK
0 tests FAILED in 0s
```

The final printed line is the protected-destination row.  The immediately
preceding writable row is an internal hard assertion of
`entry=1, normal=1, fault=0`, stored qword and FPU pop; it must pass before
the protected row runs.  The protected row's hard assertions additionally
require the handler EAX marker, saved EIP 8, SIGSEGV code 2, exact linear
destination, unchanged guard and no pop.  Therefore the generic fallback
outcome boundary is closed.

FQ1 may now implement a distinct fail-closed cache-off snapshot ABI and game
census.  It must retain the ticket discipline, capture EA/segment/page/RC/
pair context at codegen/helper entry, prove its own layout and visible
cache-off rendering before any values are used.  Cache/replay/FPS remain
forbidden.
