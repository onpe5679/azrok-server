# 515 Gate 7 bare LAN launcher route (2026-07-28)

> **SUPERSEDED by 517.** The redirect prevented the obsolete Gate 2 boot but
> did not supply the WSS instance credential required by the shared bridge.

## VERIFIED

- A bare visit to the HTTPS frontend served `index.html`, the retained Gate 2
  shell.  Its launch configuration hard-coded `root=fullWine1.7.55-v8` and
  `p=run_azrok.bat`.
- The current D3D9Web launcher uses a different, verified default pair:
  `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1` and
  `run_azrok_seh.bat`.
- The phone launch log supplied during this test showed the obsolete path
  (`/root/base`, `run_azrok.bat`) followed by missing `wineboot.exe` and audio
  driver libraries.  It therefore reached the private frontend but did not
  launch the current game image.

## SUPERSEDED IMPLEMENTATION

- Normal visits to `/` now immediately transfer to
  `index_d3d9web_pathouse.html` and preserve the query string, including a
  private instance parameter when present.
- The obsolete Gate 2 page remains available only through an explicit
  `?legacy=1` diagnostic query.

## NOT VERIFIED

- A fresh physical-phone reload of the bare private URL must still prove that
  the current D3D9Web image finishes booting and joins the shared core.
