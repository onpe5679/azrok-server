# 381 — Fresh cache-off common no-Present boundary

> **SUPERSEDED by 382.** The bounded zero-Present observation was a transient
> cache-off bootstrap state, not a persistent common environment boundary.

Date: 2026-07-25  
Status: **VERIFIED** — cache-off render proof withheld; not an FPS result.

After MRG1 generation-2 cache-off reached visible CSS 1024x768, ABI guard 1,
zero JIT cache entries, first JIT block, and `Showing Window`, its direct
Present count remained zero for two bounded post-start observations. A genuine
CDP canvas click did not change that state.

To separate candidate behavior from the environment, a new watcher-created
browser process (one blank page, 721 MiB initial working set, standard three
anti-throttling flags) then loaded the ordinary accepted ABI2 stem with
`jitCacheUrl=off`. It reached the same visible 1024x768 / first-JIT / Showing
Window state and likewise remained at zero direct Presents. Neither run is an
FPS sample and the accepted replay control was not changed.

At the time this document was written, the bounded observation supported only a
common, not-yet-localized startup state. It did not support a persistent
environment diagnosis. Document 382 records the later direct recovery on the
same accepted page and replaces the temporary conclusion.
