# 429. INT 0x9A specialized helper: private cache-OFF real-game render

Date: 2026-07-26  
Status: **VERIFIED private cache-OFF render integrity; record/replay/FPS NOT VERIFIED**

## Readiness resolution

428's zero-Present interval was an active cache-OFF bootstrap, not a settled failure.  A direct 30-second worker sample had already shown `42.703` CPU seconds, so the same sole visible primary-display page was allowed to continue without cache generation or timing.  It subsequently entered the real scene.

The exact strict URL remained the private `int9aSpecialized=1` stem with `jitCacheUrl=off` and `Azrok_D3D9Web_pathouse_guestbatch1`.  No tab was created.  At the direct runtime read:

```text
visibility                 visible
CSS canvas                 1024 x 768
direct Presents            11,620
async callbacks            11,620
async errors/gaps/reorders 0 / 0 / 0
specialized direct/fallback/fault
                           1,309,798 / 0 / 0
```

The direct counter proves that the private re-decode-guarded C++ arm—not merely its build identity—executed in the real guest.  Zero fallback and zero fault are recorded facts for this run, not an assumption that those paths are impossible.  The completed async ring is a JS dispatch acknowledgement only; it is not a GPU-completion assertion.

## Guard hardening after the run

Static audit found two identity hardening omissions unrelated to the observed successful run: the specialized Make target did not explicitly depend on the module broker and only an external environment setting forced response-file linking; the page did not reject a private stem with its mode flag omitted.  The Make target now has target-local `EM_FORCE_RESPONSE_FILES=1` plus an explicit broker prerequisite, and the page rejects any stem/mode-flag mismatch before guest execution.  `make -q` remains clean.  The current run itself already used the exact stem, flag, served getter and matching staged/HTTP bytes, so the repair does not retroactively broaden its claim.

## Decision

The specialized helper passes its private cache-OFF real-game render-integrity gate.  It remains entirely separate from the accepted stem.  The next required gate is a fresh private record, exact manifest/identity transform and replay render; no performance sample, candidate adoption or 65-FPS claim is made here.  The HUD's instantaneous FPS text was not captured or used as a performance result.
