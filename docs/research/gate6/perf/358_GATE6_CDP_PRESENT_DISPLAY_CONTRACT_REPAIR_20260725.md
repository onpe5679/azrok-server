# 358 -- CDP Present display-contract repair (2026-07-25)

## VERIFIED defect

`CdpPresent.psm1` emitted the `VoidTaskResult` of both `ClientWebSocket`
connect and send calls. This made callers receive an array mixed with the
actual socket/result, requiring ad-hoc filtering and causing the module's own
`Get-PresentState` to fail under strict mode. It also tested `canvas.width` and
`canvas.height`, which are backing-store pixels, despite the performance-card
contract and page-side capture both requiring a CSS displayed 1024x768 canvas.

The active B page directly demonstrates why the distinction matters before
guest startup: backing was 800x600 while CSS display was 0x0 and direct
Presents were zero. That is correctly not sample-ready.

## VERIFIED repair

Connect/send `GetResult()` values are now explicitly discarded, so
`Connect-Cdp` returns one `ClientWebSocket` and `Invoke-CdpCommand` returns one
CDP result. `Get-PresentState` now records both CSS display and backing sizes;
readiness and validity use only `canvas.getBoundingClientRect()` display
width/height. The output keeps backing dimensions as diagnostic evidence.

PowerShell parser validation passed, and live read-only `Get-PresentState` on
the sole B target returned the expected typed state without caller filtering.
No navigation, click, cache, or service change occurred for this repair.
