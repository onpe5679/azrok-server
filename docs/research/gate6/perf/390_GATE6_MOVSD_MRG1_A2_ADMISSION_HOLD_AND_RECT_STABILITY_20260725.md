# 390 -- MRG1 second fresh accepted control: admission hold and rect-stability gate

Date: 2026-07-25  
Status: **VERIFIED** control measurement and harness audit; MRG1 comparison remains open.

## A2 direct result

With the same current-ABI accepted replay (`94` groups / `30,550` entries /
`28,944` patches), a watcher-fresh Edge process passed the then-current
attached-sampler contract: one CDP page, all three anti-throttling flags,
visible CSS `1024x768`, visible/non-minimized/uncloaked HWND, zero non-shell
upper overlap, complete isolated Edge tree, no build process, and working set
under its fresh-A 6,000 MiB cap.

The 30-second direct-Present row is:

- 1,106 Presents / 30.016372 seconds = **36.8466 FPS**;
- Edge tree working set: 1,239.00 -> 4,319.12 MiB;
- same root PID `43788`; CSS backing remained `640x480`.

This is a mechanically valid control row under the contract that existed when
it was collected. It nevertheless fails the user-specified 52--55 FPS
admission requirement. The prior fresh A1 was 44.2917 FPS, so the two controls
also differ by 16.81%. MRG1 B was not navigated or sampled. Neither value is a
candidate comparison or a MOVSD performance decision.

## Outer-rect finding and repair

The A2 CSV preserves an additional environment difference: its root HWND
outer size changed during the timed window from `2500x2063` to `2335x1526`.
A1 held `2500x2063` at both boundaries. Static inspection confirmed that the
old sampler read `GetWindowRect`, but retained only width/height and checked
only root PID equality after timing. Therefore its documented 357 contract did
not make A2 retroactively invalid.

The attached sampler is now strengthened for every subsequent leg:

- stores outer `Left`, `Top`, `Right`, and `Bottom` in the pre/post evidence;
- fails closed before CSV publication if any of those four values changes.

Its PowerShell parser passes after the edit. This is an environmental
qualification improvement, not evidence that monitor DPI, backing canvas
size, or the MRG1 candidate caused either control value; none of those causal
claims is verified.

## Next gate

Request another watcher-fresh accepted A under the rect-stable contract. Do
not navigate to MRG1 B unless it first reaches the required 52--55 FPS range.
The accepted and MRG1 Gen2 artifacts remain unchanged.
