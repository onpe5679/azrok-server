# 398 -- FISTP FQ1 pair-lane census: safe same-address admission absent

Date: 2026-07-25  
Status: **VERIFIED static and direct browser; FISTP narrow pair candidate REJECTED before implementation**.

## Scope and integrity

This is the explicit reopening read required by 376, performed with the
existing private FQ1 asset only.  No source, build, cache, replay or accepted
runtime artifact changed, and this is not an FPS sample.

The sole existing CDP page was moved to the strict cache-OFF FQ1 route with
`runtimeStem=boxedwine.upstreamjit64fn6inlineabi2fistpqwordcensus1`,
`jitCacheUrl=off`, and `fistpQwordCensus=1`; it carried no record, replay,
Present-capture or other census flag.  Before the first snapshot it directly
showed a visible/focused CSS 1024x768 PatHouse canvas (backing 640x480),
advancing direct Present, FQ1 ABI 1 and 5,188 words.  Native CDP pointer
events, not DOM `click()`, started the game and issued each input pulse.

The sanctioned ABI-gated `azrokRefreshFistpQwordCensus()` reader returned the
already-present 5,188-word mutex snapshot.  Only its existing pair axis was
summed; no new WebGL context or performance capture was created.

## Exact pair meaning and decoder

**VERIFIED static:** the context layout is four leading U64 values plus
`context[6][2][3][2][4][2][3][3]`, for `4 + 5,184 = 5,188` words
(`wasm/jitWasmCodeGen.h:1284-1297`, `jitWasmCodeGen.cpp:236-242`).  Row-major
indexing is:

```text
4 + (((((((seg*2 + ea16)*3 + route)*2 + page)*4 + rc)*2 + cached)*3 + pair)*3 + outcome)
```

At FISTP-m64 code generation, `pair=0` means no immediately adjacent FILD
m64; `pair=1` means immediately adjacent FILD m64 with the **same linear m64
address**; and `pair=2` means the adjacent FILD m64 uses a **different linear
m64 address** (`jitWasmCodeGen.cpp:14842-14876`).  The state is reset at a new
JIT block and updated after compile, so a block boundary, branch or re-decode
cannot be over-counted as an adjacent pair (`jitWasmCodeGen.cpp:15274-15279`,
`15389-15392`).  Outcomes are normal-pop, normal-no-pop and fault in that
order (`jitWasmCodeGen.cpp:5489-5503`).

The only narrow design retained by 376 needs `pair=1`: it can retain the
FILD-loaded original i64 and use the existing checked b64 write before FPOP.
`pair=2` cannot reuse that value and remains outside the design.

## Direct visible-Present snapshots

All values below are normal-pop / normal-no-pop / fault.  The two post-pulse
intervals used independent nominal 30-second waits; Present progression is
integrity evidence only, not a frame-rate calculation.

| snapshot | direct Present | FISTP context | pair=0 | pair=1 same linear | pair=2 different linear |
| --- | ---: | ---: | ---: | ---: | ---: |
| S0 before pulse | 2,869 | 1,766,654 | 10 / 0 / 0 | **0 / 0 / 0** | 1,766,644 / 0 / 0 |
| S1 after pulse 1 | 7,766 | 4,572,568 | 22 / 0 / 0 | **0 / 0 / 0** | 4,572,546 / 0 / 0 |
| S2 after pulse 2 | 9,586 | 5,932,786 | 22 / 0 / 0 | **0 / 0 / 0** | 5,932,764 / 0 / 0 |

| interval | FISTP context delta | pair=0 delta | pair=1 same-address delta | pair=2 different-address delta |
| --- | ---: | ---: | ---: | ---: |
| S0 -> S1 | 2,805,914 | 12 | **0** | 2,805,902 |
| S1 -> S2 | 1,360,218 | 0 | **0** | 1,360,218 |

All headers satisfy `fn8Total = otherOpcode + invalidTag + invalidMetadata +
context`: S0 `7,795,131 = 6,028,477 + 0 + 0 + 1,766,654`; S1
`20,890,313 = 16,317,745 + 0 + 0 + 4,572,568`; S2 `33,005,104 =
27,072,318 + 0 + 0 + 5,932,786`.  Thus no invalid tag/metadata row is hiding
pair coverage.  This bounded scene again observes only normal-pop; it does
not generalize away the protected-destination fault semantics closed by
FQF1/FQF2.

## Decision

**REJECTED before implementation.**  The exact safe `pair=1` lane has zero
observed production coverage in both independent visible-Present intervals,
despite 4,166,120 total FISTP contexts.  The large `pair=2` count is direct
evidence of different-address adjacency, not an admission substitute.

Accordingly, no FISTP inline source/build/cache/replay/FPS card opens.  The
broad uncached helper remains required for x87 ext80/rounding and
store-before-pop fault semantics (376).  This closes the sole missing
per-tuple gate in 376 without changing the accepted ABI2 stack.
