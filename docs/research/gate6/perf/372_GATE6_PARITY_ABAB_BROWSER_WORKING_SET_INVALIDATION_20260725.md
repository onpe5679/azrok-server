# 372 -- Parity A-B-A-B browser working-set invalidation (2026-07-25)

Status: **VERIFIED environment invalidation; no parity performance verdict**

## Discarded samples

The fresh current-corpus parity replay and current accepted control remain
valid artifacts.  However their first attempted attached-session performance
legs are **invalid and must not be used for a parity decision**:

| leg | direct Present FPS | mechanical page/window contract |
| --- | ---: | --- |
| A1, accepted 94 / 30,550 / 28,944 | 3.5982 | pass |
| B1, parity 113 / 35,492 / 29,181 | 3.2649 | pass |

Both had one CDP target, visible document start/end, CSS `1024x768`, exact
30-second direct-Present wall window, all 357 anti-throttling flags from
`Browser.getBrowserCommandLine`, visible/non-minimized/uncloaked Edge HWND,
and zero known top-level z-order overlap. Those checks are genuine but
insufficient for a long-lived BoxedWine browser process.

## Why relative comparison is invalid

**VERIFIED (environment observation):** Immediately after A1, user direct
measurement found CPU, memory, and build tools non-contended, while the nine
`msedge` processes held a combined 21,979 MB working set. The Wasm build uses
`MAXIMUM_MEMORY=3GB`; repeated private MBS/FQF/FQ1/parity record reloads made
long-lived browser accumulation the remaining abnormal axis.

**VERIFIED historical comparison:** In the earlier occluded collapse, the
same MOVSD candidate appeared faster (`A=3.885`, `B=9.397`), whereas a normal
re-measure showed it decisively slower (`A=54.5970/54.3583`,
`B=42.8643/40.6660`). Thus a collapsed control does not preserve even the
sign of the A/B effect. A1/B1 above cannot be interpreted as a relative
parity result.

## Required restart gate

Human-controlled Edge restart with the same 357 flag set is authorized and
is not a card blocker. Before each new A/B leg, record the total `msedge`
working set in addition to existing argv/sole-page/visibility/CSS/HWND/
overlap evidence. After restart, obtain accepted A in the directly observed
normal `52--55` FPS range before navigating B. If it is outside that range,
discard it and diagnose first. Do not rebuild or regenerate the valid parity
or accepted artifacts.

The first two attached-harness attempts before A1 are also discarded: they
exposed `VoidTaskResult` leakage from the CDP socket-close path rather than a
timing result. The close output is now suppressed and the attached runner
filters to exactly one `Valid` measurement object; its later A1/B1 mechanical
contracts passed, but are independently invalidated by working-set collapse.
