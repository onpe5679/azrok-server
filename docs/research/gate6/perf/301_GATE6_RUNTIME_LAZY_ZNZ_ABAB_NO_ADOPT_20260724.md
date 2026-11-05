# 301 — Runtime-lazy Z/NZ release A-B-A-B

## Verdict

**VERIFIED browser/dynamic; performance NOT ADOPTED.**

The uninstrumented release `boxedwine.upstreamjit68runtimeznz1` and its
isolated 111-group cache were tested only after document 300's exact diagnostic
had proved fn16/fn17 `0:0` in an equivalent fresh replay workload.  No
diagnostic counter build was used for any performance leg.

## Method — VERIFIED

- A: accepted `boxedwine.upstreamjit64fn6inlineabi2` plus the accepted
  inline-fetch cache.
- B: uninstrumented runtime-lazy Z/NZ release plus
  `azrok-jit-grouped-commonfast64-depthlocal-inlinefetch-runtimeznz68.zip`.
- Every leg used one visible in-app tab, normal two selection pulses, full
  1024x768 PatHouse, and the page's direct `D3D9WebDebug.presents` 30-second
  capture.  No make/emcc/clang/ninja build or cache-generation process was
  active during sampling.
- A drift exceeded the +/-3% noise band, so the planned A-B-A was extended to
  A-B-A-B before judging.

## Direct Present results — VERIFIED

| leg | stem | presents / wall | FPS |
| --- | --- | --- | ---: |
| A1 | accepted ABI2 | 1,396 / 30.002 s | 46.5308 |
| B1 | runtime-lazy Z/NZ | 1,408 / 30.001 s | 46.9319 |
| A2 | accepted ABI2 | 1,339 / 30.001 s | 44.6319 |
| B2 | runtime-lazy Z/NZ | 1,248 / 30.005 s | 41.5938 |

The matching A-to-B effects are **+0.862%** (A1->B1) and **-6.807%**
(A2->B2); their signs conflict.  A condition mean is 45.5814 FPS and B
condition mean is 44.2629 FPS (-2.893%).  A drift is -4.080%, which was the
reason for the B2 extension.  Therefore the result neither proves an uplift
outside the noise band nor supports adoption.  The accepted ABI2 path remains
the default and Z/NZ remains isolated/opt-in evidence only.

## Integrity

Document 300 already directly proved the release workload's remaining Z/NZ
helper fallback count is 0/0.  This measurement changes no cache/loader
contract and makes no rendering-regression claim beyond the pre-existing
cache-OFF/replay integrity gates in documents 297--300.

## Next

Proceed only with independent idle-slot diagnostics: same-browser standard
Chrome Liftoff/no-Liftoff A-B, then isolated `-nosound` A-B-A.  Do not mix
those cards with Z/NZ or parity.
