# 373 -- parity restart control admission retry (2026-07-25)

Status: **VERIFIED control-only; parity A-B-A-B remains unopened**

## Restart and harness evidence

**VERIFIED:** CDP `Browser.getBrowserCommandLine` directly reported the
isolated Edge profile, port 9222, and all three required anti-throttling
switches: `--disable-backgrounding-occluded-windows`,
`--disable-renderer-backgrounding`, and
`--disable-background-timer-throttling`.  The four runtime service ports were
listening and CDP exposed exactly one page target.

The attached runner now records the root Edge process tree and combined
`WorkingSet64` before/after each leg, alongside the existing argv, single page,
document-visible, CSS 1024x768, HWND and z-order evidence.  The first valid
leg is recorded without an invented absolute working-set cap: a 3GiB Wasm
linear-memory build can have a larger browser working set.  Each later leg is
instead fail-closed if its pre-sample tree working set exceeds the prior valid
pre-sample value by both the operational relative envelope (25 percent) and
the 512MiB floor.  This is a hygiene gate, not a claim that a value below any
fixed threshold is healthy.

## No-FFT sample attempts before the control leg

**VERIFIED:** The first post-restart control launch reached the 94-group replay
but had no direct Present until a normal centre input pulse was supplied;
`Measure-CdpPresentWindow` therefore timed out in its readiness gate.  It
produced no FPS value and is not a performance sample.  A subsequent
pre-sample attempt was fail-closed before timing when two top-level Edge HWNDs
were present (the isolated BoxedWine window plus a separate YouTube Edge
window).  That window later disappeared; it likewise produced no FPS value.

## Control A1 result and admission decision

**VERIFIED:** After the input pulse, the sole visible page showed
`D3D9WebDebug.presents=9462`; the 94/30,550/28,944 accepted replay then passed
the full attached measurement contract.  Its 30-second direct-Present result
was **51.2849 FPS** (1,539 presents / 30,008.829ms), with Edge tree working
set **4,265.01 -> 4,263.68 MiB**, 10 processes, unchanged root PID, and zero
known top-level overlap.

This number is mechanically valid but is **not admitted as parity A**:
the authorized restart gate requires an accepted control observation in the
52--55 FPS band before B may start.  It is 0.7151 FPS below the lower bound.
No parity page navigation, candidate FPS, cache rebuild, or record regeneration
occurred.

**VERIFIED diagnostics after A1:** no clang/emcc/wasm-ld/wasm-opt build process
was active; only the isolated Edge tree remained (one top-level HWND, about
4.23GiB working set), and system total CPU was 21 percent.  These observations
exclude the specific prior 21,979MB Edge accumulation and build contention,
but do not establish an exact cause for the small remaining below-band delta.

## Next action

Take another accepted control-only A under the same single-tab contract.  Do
not navigate to parity B unless that control first satisfies the 52--55 FPS
admission band; when it does, use its pre-sample Edge working set as the B
relative fail-closed reference.

## Accepted A retry and B1 working-set stop

**VERIFIED:** The next control-only retry passed the same contract and produced
**55.0276 FPS** (1,651 presents / 30,003.1ms).  Its Edge tree working set was
**4,225.28 -> 4,203.96 MiB**; the prior 4,265MiB reference yielded the
5,332MiB relative gate for that retry.  This satisfies the authorized
control-admission condition, so the sole CDP page was then navigated to the
private parity URL without rebuilding either artifact.

**VERIFIED:** B's private page directly reached `parity=1`, registered
**113 groups / 35,492 blocks / 29,181 patches**, CSS 1024x768, visible document,
and 6,770 advancing direct Presents after the same input pulse.  Its A-derived
pre-sample working-set gate was `ceil(max(4225*1.25, 4225+512)) = 5,282 MiB`.
Before timing began, the isolated Edge tree was **5,720.46 MiB**, so the
attached runner fail-closed.  **No B1 FPS value exists; no candidate result
exists.**  The 35.4 percent increase relative to A is an environment-hygiene
failure, not evidence about parity.

## Current hold

Human-controlled Edge restart is required before restarting the sequence from
control A.  Do not reuse the present B process as a performance environment;
do not rebuild the valid 94/30,550/28,944 control or 113/35,492/29,181 parity
artifacts.

**VERIFIED follow-up dynamic probe:** With no compiler build process present,
the retained B tab was still one visible/complete CDP page and retained the
full anti-throttling launch contract.  Its nine Edge processes then totalled
**5,864.71MiB**; renderer PID 48008 alone held **5,341.12MiB**.  This is
8.06 times the directly observed 728MiB post-restart process total and remains
above the 5,282MiB A-derived B gate.  It confirms the stop condition but does
not attribute the growth to parity semantics.

## Harness hardening after the B stop

**VERIFIED static audit and repair:** The initial working-set implementation
allowed a caller to omit `PriorValidMsedgeWorkingSetMiB`, which silently made
the later-leg gate zero.  The attached runner now requires exactly one of:

* `-EstablishWorkingSetBaseline` -- permitted only for the first fresh-restart
  control A; or
* a positive `-PriorValidMsedgeWorkingSetMiB` -- mandatory for every later
  A/B leg.

It now applies the computed later-leg cap both before and after the timing
window.  A before/after violation writes a separate
`<OutputCsv>.rejections.csv` row containing the URL, phase, root PID/tree,
working set and cap before throwing, so a rejected leg is durable evidence
rather than only terminal text.

**VERIFIED dynamic regression:** Against the retained B page with A prior
4,225MiB, the repaired runner stopped before timing at **5,904.77MiB** against
the same 5,282MiB cap and wrote a `working-set-before`, `Valid=false` rejection
row.  No direct-Present sample was started.  This probes the harness only and
does not create a B performance result.
