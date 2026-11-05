# 415 -- Gate 6 logical-composite32 attached-sampler identity gate (2026-07-26)

## Status

**VERIFIED static sampler extension.  No logical-composite32 FPS row has been
captured.**

The existing attached Present sampler was intentionally narrow: it understood
only accepted control, the separate parity candidate, and MRG1.  Calling it
for the new private logical-composite32 replay would therefore have either
rejected the URL or, worse, had no candidate-specific runtime identity proof.

A fourth role, `LogicComposite32CandidateB`, now requires before timing:

```text
runtimeStem = boxedwine.upstreamjit64fn6inlineabi2logiccomposite321
jitCacheUrl = /profiles/azrok-jit-grouped-logiccomposite321.zip
runtimeLogicComposite32 = 1
groups / entries / patches = 92 / 30061 / 28632
parity / MRG / logical ABI getters = 0 / 0 / 1
logical replay live tuple = 1:108:328
```

All established constraints remain unchanged: only fresh `ControlA` may
establish working-set, free-memory and Present baseline values; each later leg
must carry those values; build-process, visibility/focus, HWND/overlap,
viewport/outer-rect stability, process-tree, working-set, memory and present
collapse gates still fail closed.  PowerShell parser validation passed.

## Next gate

With no build process and approximately 105,266 MiB currently free, use the
human-owned restart watcher for a fresh accepted A.  A valid fresh A establishes
this run's three baselines; only then take the private B, fresh A and, if
needed for drift, fresh B 30-second Present legs.  This document makes no
performance claim.
