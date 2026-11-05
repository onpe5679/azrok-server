# 391 -- MRG1 third fresh accepted control: rect-stable admission hold

Date: 2026-07-25  
Status: **VERIFIED** control measurement; MRG1 comparison remains open.

## Fresh A3 result

After the 390 full-outer-rect fail-closed repair, the human-owned watcher
created a new isolated Edge profile and placed it at
`(-3800,20)-(-1300,2083)`. The attached sampler used a real pointer activation,
waited for direct-Present readiness, then applied its 300-second scene settle,
15-second warm-up and 30-second measurement.

The accepted current-ABI replay (`94` groups / `30,550` entries / `28,944`
patches) produced:

- 1,260 direct Presents / 30.003605 seconds = **41.9950 FPS**;
- visible CSS `1024x768`, backing `640x480`, and `document.visibilityState`
  visible at both timing boundaries;
- exact same outer HWND rect before and after, with visible/non-minimized/
  uncloaked state and zero non-shell upper overlap;
- full isolated Edge tree (8 -> 10 processes) and working set
  1,229.44 -> 4,242.88 MiB, below the 6,000 MiB fresh-A cap;
- full required anti-throttling argv before and after; no build process.

Thus A3 is valid under the strengthened contract, but it again misses the
user-required 52--55 FPS admission range. The sequence A1/A2/A3 is
44.2917/36.8466/41.9950. MRG1 B remains unvisited and unmeasured, so there is
no candidate FPS result or adoption/rejection decision.

The stable A3 rect rules out the specific A2 in-window rect change as a
necessary explanation for all low controls. It does not establish a cause for
the low control rate. Static and dynamic environment comparison against the
earlier 54--55 accepted runs is required before a further fresh A, and no
baseline/admission threshold is relaxed here.
