# 389 ??MRG1 A1 valid sample, admission-range hold

Date: 2026-07-25  
Status: **VERIFIED** ??valid control measurement; candidate comparison held.

After the watcher-created Edge was placed on the isolated left monitor, the
attached sampler passed its full browser argv, sole-page, visible/unminimized/
uncloaked, zero-upper-overlap and single Edge-tree checks before and after the
window. The fresh accepted current-ABI replay was registered and directly
measured for 30.005645 seconds:

- direct Present delta: 1,329
- FPS: **44.2917**
- CSS canvas: `1024x768`; backing: `640x480`
- Edge working set: 3,635.95 -> 4,217.44 MiB, under its 6,000 MiB fresh-A cap

The extended readiness path was required: the old 180-second readiness limit
timed out before this same control later entered Present; the new 600-second
limit admitted only after direct Present advanced. This changes no valid
predicate (visible CSS 1024x768 plus monotonic direct Present).

The user required a fresh A in the 52--55 FPS admission range before MRG1 B.
Although this A1 is mechanically valid and lies in the older historical
43--50 range, it does not meet that newly stated 52--55 admission condition.
Therefore B was not navigated or sampled, and this value is not an
accepted-vs-MRG1 comparison or candidate result. Static/dynamic environment
analysis remains required before a new fresh A attempt.
