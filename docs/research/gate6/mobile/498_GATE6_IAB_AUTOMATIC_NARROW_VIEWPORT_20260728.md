# 498 Gate 6 in-app automatic narrow viewport containment (2026-07-28)

## VERIFIED

- The retained in-app game tab reports a real `390x844` viewport even without
  an explicit `mobileCapture` URL parameter.
- Before this repair, that tab kept both rendered canvases at displayed
  `1024x768`, overflowing the visible narrow game surface.
- The launcher now applies `d3d9web-mobile` to either explicit mobile capture
  or any viewport at most 600 CSS pixels wide.  A fresh original-client run
  then displayed the source and WebGL overlay canvases at `347x260.25`, exact
  4:3, while retaining their 1024x768 game backing buffers.
- In the repaired narrow path, BGM launched normally on the media-element
  route (`paused=false`, `muted=false`, ready state 4).  Its first valid
  29.721 s direct-Present window measured `125.1661 FPS`.

## Boundary

- Later in-app windows still declined, so this repair fixes actual narrow
  presentation and removes an avoidable compositor mismatch, but does not yet
  establish sustained 50 FPS in the in-app host.
