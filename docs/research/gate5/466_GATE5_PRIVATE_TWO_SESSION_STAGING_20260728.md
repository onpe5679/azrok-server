# Gate 5 private two-session staging (2026-07-28)

## Current result

- **VERIFIED (private runtime):** two isolated in-app browser tabs launched the original StateBlock package through the private HTTPS/WSS bridge, using the same bridge admission token and distinct game roles (`player` and `peer111`). Both reached active rendering and their browser BGM fallback was `playing`.
- **VERIFIED (single-core control API):** the loopback-only preservation server reported `server_clients=2`, `connected_clients=2`, `plaza_clients=0`, and `transition_code=multi_client`. The GUI/control state remained responsive while both browser sessions rendered.
- **VERIFIED (visual):** both sessions reached the original character-selection flow; the primary reached a live PatHouse scene after selecting its persisted character.

## Boundary

- **NOT VERIFIED:** current private-run reciprocal Plaza actor rendering, movement relay, and targeted leave. The `peer111` account was at the original character-creation screen, so it had not yet completed the character selection and natural Plaza entry sequence.
- **NOT VERIFIED:** the Gate 5 requirement is not met by two TCP/WebSocket connections alone. It still requires both initialized clients in Plaza, reciprocal `0x0066/0x0068` evidence, a visible remote actor on both screens, and a targeted `0x0067` leave check.
