# Gate 5 browser input boundary and pointer compatibility (2026-07-28)

## Implementation

- **VERIFIED (source):** `index_d3d9web_pathouse.html` now observes canvas `pointerdown`/`pointerup` and supplies the corresponding `mousedown`/`mouseup` only when the native compatibility mouse event did not occur in the same task. The adapter is restricted to mouse pointers and does not duplicate normal browser mouse input.
- **VERIFIED (syntax):** all inline JavaScript in the page passes `node --check` parsing after the change.

## Live input result

- **VERIFIED (browser visual):** native CUA mouse input dismissed the rendered tutorial and changed the local PatHouse camera/character presentation; the reloaded session then reported `PatHouse (local)` through the shared core.
- **VERIFIED (input provenance):** the adapter status remained unset after CUA clicks, proving the current in-app browser already emitted native mouse compatibility events rather than pointer-only events.
- **VERIFIED (packet boundary):** floor click, pointer-lock attempt, keyboard attempts, and a press-move-release drag produced no C2S `0x0066`, `0x0067`, or `0x0019`; the only continuing C2S packets were heartbeat after character admission.

## Interpretation

- **VERIFIED:** current CUA can advance visible local UI, but this alone is not evidence of world movement or door hit success.
- **INFERRED:** the remaining Plaza blocker is the original local movement/hit-test condition for the far-left exit, not a missing DOM Pointer-to-Mouse translation. No synthetic game packet or legacy memory shortcut was used.
