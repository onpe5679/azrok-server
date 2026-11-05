# 359 -- MOVSD MRG2 no-direct replay: current-corpus A-B-A-B rejection (2026-07-25)

## Decision

**VERIFIED -- reject the private MOVSD MRG2 no-direct replay as a performance
candidate.**  Preserve it only as a correctness/render-integrity artifact
(353); do not publish it or replace the 94-group accepted replay.

The user retired the historical 43--50 FPS admission band for this decision:
that band belongs to an ABI-incompatible, unreplayable 134-group corpus (355).
The valid control is the served current-ABI accepted archive: 94 groups,
30,550 entries, 28,944 patches, live reloc-map base 12,968,408.  The
private candidate remains 95 groups and 30,636 blocks under its distinct MRG2
stem and immutable cache identity.  Thus this is a same-session,
same-browser, relative comparison; it makes no claim that its absolute value
must match historical corpus measurements.

## VERIFIED -- A-B-A-B direct-Present measurements

All four legs used the one existing CDP page (no new tab), the visible
PatHouse scene, direct `D3D9WebDebug.presents`, and a 30-second page capture.
Every leg had `document.visibilityState="visible"` and CSS canvas
1024x768.  The corrected, user-directly-verified root Edge flag set included
`--disable-backgrounding-occluded-windows`,
`--disable-renderer-backgrounding`, and
`--disable-background-timer-throttling`.  The 357 read-only Win32 checks on
the root HWND recorded visible=true, minimized=false, DWM cloaked=0, and zero
known visible/non-cloaked top-level z-order overlaps.  This is prevention
evidence, not a claim of pixel-perfect compositor proof.

| Leg | Archive/stem | Present delta / wall time | FPS |
|---|---|---:|---:|
| A1 | accepted current ABI, 94-group / `boxedwine.upstreamjit64fn6inlineabi2` | 1,638 / 30,001.7 ms | **54.5970** |
| B1 | private MRG2 no-direct, 95-group / `boxedwine.upstreamjit64fn6inlineabi2movsdruntimezero2` | 1,286 / 30,001.6 ms | **42.8643** |
| A2 | accepted current ABI, same A identity | 1,631 / 30,004.6 ms | **54.3583** |
| B2 | private MRG2 no-direct, same B identity | 1,220 / 30,000.5 ms | **40.6660** |

B2 was independently preflighted immediately before capture: direct Presents
8,482; visible CSS 1024x768; capture inactive; root PID 109200; the same
visible/non-minimized/uncloaked HWND and zero-known-overlap result.  Its page
capture started at direct Present 8,485 and ended at 9,705.

The three adjacent A/B boundaries, evaluated as candidate relative change,
are:

| Adjacent boundary | Candidate relative to control |
|---|---:|
| A1 -> B1 | -21.49% |
| B1 -> A2 | -21.15% |
| A2 -> B2 | -25.19% |

Their median is **-21.49%**, far outside the predeclared +/-3% noise band.
The conclusion is therefore a rejection, not an ambiguous result.  The
earlier occluded-window values (A1 3.8851, B 9.3967, A2 3.5534) remain
explicitly INVALID in 356 and are not used here.

## VERIFIED / INFERRED -- scope of the loss

The accepted current archive contains 9,648 direct tails and 209,969 generic
tails across 30,550 entries.  The private MRG2 archive contains 30,636 blocks
but **zero direct tails** and no generic tail admission.  The candidate was
intentionally no-direct so the live MRG identity/guard could be isolated;
353's pinned identity and render proof remain valid.

**VERIFIED:** the measured candidate removes all 9,648 accepted direct-tail
fast paths while adding only 86 recorded blocks.  It is not a dual-entry-R2
measurement, so it cannot quantify the separate R2 5,299-site helper-fallback
versus wrapper-overhead question.  That question remains bounded by 351/325's
missing exact 34,322-module raw corpus and is not inferred from this MRG run.

**INFERRED:** the broad loss of accepted direct-tail chaining is the dominant
explanation for the approximately 21--25% deficit.  This is a coverage and
artifact contrast, not per-site CPU attribution: no counter in this run
separates MOVSD helper fallback time from wrapper time.  The private no-direct
design therefore fails performance admission regardless of MOVSD correctness.

## Consequence

Keep the accepted current-ABI 94-group archive as the only performance
baseline.  MRG2 stays private and fail-closed.  The MOVSD card is closed as a
performance rejection; proceed to the independent census queue in order:
MOVSB MBS1, then FISTP.  No parity or Z/NZ work is reopened.
