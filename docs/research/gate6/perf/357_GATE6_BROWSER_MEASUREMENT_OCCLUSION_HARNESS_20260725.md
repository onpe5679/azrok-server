# 357 -- browser measurement occlusion harness (2026-07-25)

## Scope

356 invalidated an entire A-B-A because `document.visibilityState=visible`
does not prove that a backgrounded Edge renderer was launched with the
occlusion-prevention switch. This card hardens only the diagnostic harness;
it does not alter Azrok, BoxedWine, any cache, or an active browser tab.

## VERIFIED -- prior harness gap

`Invoke-AzrokBrowserPresentSample.ps1` passed
`--disable-backgrounding-occluded-windows`,
`--disable-renderer-backgrounding`, and
`--disable-background-timer-throttling` to `Start-Process`, but checked only
the requested NoLiftoff flag after the whole sample. `CdpPresent.psm1` checked
page visibility, CSS canvas and direct Present at start/end; neither script
checked the root argv or HWND state before a measurement.

Direct current-state probes establish the API boundary:

* CDP reports page visibility and focus, and `Browser.getWindowForTarget`
  exposes one initial bounds snapshot, but does not disclose launch flags or
  prove compositor coverage.
* The current Edge page was visible but unfocused. Win32 directly found the
  Edge HWND visible, non-iconic and DWM-uncloaked; ChatGPT was foreground on a
  non-overlapping monitor rectangle. Enumerating higher z-order top-level
  visible/non-iconic/non-cloaked windows found zero rectangles overlapping
  Edge at that instant.
* Win32 rectangle/z-order checks cannot detect a transparent, click-through or
  compositor-only overlay, nor prove exact covered pixels.

## VERIFIED -- fail-closed harness change

The runner now performs and records all of the following before and after its
30-second sample:

1. It obtains the `Start-Process` root PID command line; failure to obtain it
   aborts the run.
2. It requires the expected executable, exact unique `--user-data-dir`, exact
   CDP port, and exactly one occurrence of each required diagnostics flag.
3. It obtains the root top-level HWND and requires visible, non-minimized,
   nonzero-rectangle and `DWMWA_CLOAKED=0` state.
4. It traverses higher top-level z-order windows. Any visible, non-minimized,
   DWM-uncloaked non-shell window with a positive rectangle intersection is a
   fail-closed overlap. Foreground status is recorded but is not required.

The output includes serialized launch-contract, HWND and top-level-overlap
snapshots for both boundaries. The README explicitly prohibits describing this
as pixel-perfect "unoccluded" proof; the correct claim is the complete launch
contract and zero known top-level overlap.

## Verification

PowerShell parser validation of the changed runner passed. The embedded native
Win32/DWM declarations compiled in a fresh PowerShell process, and direct
calls against the live Edge HWND succeeded (`GetWindowRect=true`, DWM HRESULT
0, cloaked 0). The runner's extracted read-only HWND functions were also
executed against that same live Edge: `visible=true`, `minimized=false`,
`cloaked=0`, and `TopLevelOverlapCount=0`. A full runner execution was
intentionally not launched because the sole-tab policy reserves the active
page for the MRG measurement gate.

## Status

The harness removes the omitted-flag recurrence path for its own isolated
browser launches. It cannot retroactively validate 356's invalid samples and
does not resolve the current-corpus baseline policy; MRG B remains unmeasured.
