# 377 -- parity cold A1 CDP target loss (2026-07-25)

Status: **VERIFIED environment abort; no FPS sample or parity verdict**

## Direct preflight

After the human-created fresh Edge instance, direct CDP verification exposed
exactly one visible `about:blank` page on port 9222. `Browser.getBrowserCommandLine`
contained the isolated profile, port 9222, and all required anti-throttling
flags: `--disable-backgrounding-occluded-windows`,
`--disable-renderer-backgrounding`, and
`--disable-background-timer-throttling`. The four runtime service ports were
also listening. Combined Edge working set was 471.94MiB across eight processes
at the direct preflight.

The previously completed cold-B distinction is not repeated: 374 already
directly established that B alone reaches the valid replay at 4,019.02MiB, so
the former >5GiB state was same-tab lifetime retention rather than a B-only
memory property.

## A1 abort

The sole blank target was navigated once to the pinned 94/30,550/28,944
accepted-control URL (`build=paritycurrent1-cold-a1-20260725`). Before replay
identity, scene readiness, working-set baseline, or any Present timing could
begin, `/json/list` returned zero page targets. A six-read, 30-second direct
CDP follow-up observed zero page targets on every read. Edge processes and one
top-level HWND remained, so this evidence does not identify whether the page
was silently closed, CDP target discovery was lost, or another browser-lifetime
event occurred. No crash attribution is made.

## Decision

This is an environment abort, not a control value and not a parity result. The
A1 navigation produced **no working-set baseline and no FPS row**. Do not use
this process for B or later A/B legs. The next human-created isolated browser
must again expose exactly one blank CDP page; then restart at cold Control A
with `-EstablishWorkingSetBaseline`. Per 374, each subsequent B/A/B leg still
requires its own cold browser process and the prior valid cold-A reference.
Neither valid parity artifact nor accepted control artifact was regenerated.
