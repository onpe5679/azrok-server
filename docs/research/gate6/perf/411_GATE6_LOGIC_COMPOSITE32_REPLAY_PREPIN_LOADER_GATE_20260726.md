# 411 -- Gate 6 logical-composite32 replay pre-pin loader gate (2026-07-26)

## Status

**VERIFIED static loader gate. Replay is intentionally fail-closed before a
fresh private record/transform supplies final pins. No build, cache, browser
render, replay or FPS sample has occurred.**

The candidate page now recognizes its private replay URL only when the stem,
mode and exact candidate cache path agree.  Before group registration it
requires a runtime identity kind, private stem, raw-manifest SHA, ABI=1,
archive SHA and grouped-manifest SHA.  The three current pin constants are
deliberately null, so any candidate replay stops with
`runtime-logic-composite32-pins-unset`.

The grouped pipeline independently emits the mutually exclusive identity and
semantic descriptor: exact CPU result/type offsets, `{6,15,21,42}` runtime
types, `{6,7,12,13,14,15}` conditions, `FLAGS_NULL_ONLY` and
`helpers.cond-composite`.  Page validation rejects a wrong/missing identity,
raw SHA, archive SHA, grouped manifest SHA, descriptor mutation or runtime
getter version before registration.  Accepted and MRG/parity paths remain
separate.

`tools/boxedwine_local/verify-runtime-logic-composite32-loader-gate.mjs`
directly checks the pre-pin fail-close contract and passed, as did page and
pipeline JavaScript syntax checks.  The next action is now authorized: build
the private target, prove its direct ABI export, then cache-OFF real-game
render integrity before record/transform.  No accepted asset is eligible for
reuse.
