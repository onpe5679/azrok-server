# 400 -- Liftoff watcher mode-control boundary

Date: 2026-07-25  
Status: **VERIFIED static/dynamic-evidence; Liftoff remains NOT MEASURED**.

## Directly verified current boundary

The human-owned restart watcher is suitable for the standard fresh browser
legs, but not for the required V8 comparison.  It treats
`RESTART_REQUEST` purely as an existence signal; its contents are ignored
(`tools/browser_diagnostics/Watch-AzrokBrowserRestart.ps1:189-195`).  Its
fixed launch list has the three anti-throttling flags and `about:blank`, but
no `--js-flags` argument (`:101-117`).  A text payload containing
`--js-flags=--no-liftoff` would therefore be inert and is not a mode switch.

The older independent diagnostic does implement `Mode=NoLiftoff` by appending
and command-line-verifying exactly `--js-flags=--no-liftoff`
(`Invoke-AzrokBrowserPresentSample.ps1:206-218,237-239`), but its direct
`Start-Process` path is the one previously policy-rejected before a child
browser existed (327).  No Liftoff CSV, browser page or Present measurement
exists.  The active default watcher/browser must not be relabeled as B, and
CDP cannot inject a V8 process-start flag.

The watcher also waits for `pages.Count -ge 1` rather than independently
requiring exactly one page target (`Watch-AzrokBrowserRestart.ps1:119-131`).
Its `RESTART_DONE` consequently is insufficient by itself for the Liftoff
one-page invariant; CDP validation remains mandatory before a future leg.

## Required permitted launch path

This card can resume only after explicit human action creates and starts a
human-owned fixed-mode launcher.  It must accept a bounded `Default` or
`NoLiftoff` selection (or two named empty trigger files), never arbitrary
request-file flags.  In `NoLiftoff` mode it must hard-code exactly one
`--js-flags=--no-liftoff`, verify that effective command line, require exactly
one `about:blank` page, and record selected mode plus launch verification in
its completion record.  Default mode must fail if any V8 override is present.

Only then may fresh-profile Default A -> NoLiftoff B -> Default A begin,
upgraded with the current root-argv, visible/overlap, rect/viewport,
working-set, free-memory and Present-collapse gates.  Assets must remain the
same and each leg must use visible direct Presents for 30 seconds; extend to
A-B-A-B if the controls drift.  This is a human-authorized process launch
requirement, not a request to bypass the browser-launch policy.
