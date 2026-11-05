# Gate 5 IDBFS bootstrap serialization (2026-07-28)

## Result

- **VERIFIED (fresh two-tab repro):** starting two original browser clients concurrently against the same private origin left the second tab at `Downloading...` while the first client completed its own boot. The page uses one origin-wide IDBFS root, so the observation is consistent with competing first `syncfs(true)` work; it was not accepted as a multiplayer success.
- **VERIFIED (negative control):** forcing the second client to `storage=memory`, or changing its Wine root mount path, reached a Wine initialization error. Those variants were removed; the established persistent Wine root is required by this current app/root bundle.
- **VERIFIED (implementation + fresh browser):** `boxedwine-shell.js` now serializes only the initial IDBFS populate operation with the browser's exclusive `boxedwine-idbfs-bootstrap` lock and always advances its callback even when `syncfs` returns an error. A newly launched peer then advanced past the previous stall through the original Hansol splash into character creation while the primary original client remained connected to the same loopback core.

## Boundary

- **NOT VERIFIED:** the full Gate 5 acceptance: peer character creation, natural Plaza entry by both players, reciprocal actor rendering, movement relay, targeted leave, and simultaneous GUI proof remain open.
- **NOT VERIFIED:** this repair's impact on the canonical three-by-30-second Present performance gate. It runs only during browser filesystem bootstrap, not in the guest frame loop.
