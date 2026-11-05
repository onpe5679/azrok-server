# Gate 7 Tailscale-only endpoint (2026-07-28)

## Result

- **VERIFIED (bind inspection):** the machine's Tailscale interface is `<tailscale-ip>/32`; the existing LAN endpoint remains explicitly bound to `<lan-ip>`.
- **VERIFIED (implementation):** a second HTTPS asset server and WSS-to-TCP bridge are bound only to `<tailscale-ip>:8765` and `<tailscale-ip>:9201`. Both forward only to the existing `127.0.0.1:9200` preservation core; the core and Codex GUI endpoint remain loopback-only.
- **VERIFIED (private authentication):** the Tailscale WSS bridge rejects an invalid per-instance token with policy close `1008`, and accepts the project instance token with binary subprotocol before connecting only to the fixed loopback core.
- **VERIFIED (TLS):** a dedicated private-CA certificate with the Tailscale IPv4 SAN serves the page successfully over HTTPS with its CA trusted by the test client.

## Safety boundary

- **VERIFIED:** listeners are explicit `<lan-ip>` or `<tailscale-ip>`; no wildcard or public IP listener was introduced.
- **VERIFIED:** the asset server rejects JIT-record uploads from non-loopback sources, so an external player cannot write profiler artifacts or affect Codex measurement data.

## Open verification

- **NOT VERIFIED:** a second physical Tailscale device that has trusted the private CA, opened the authenticated page, completed guest start, and joined a live reciprocal multiplayer session.
- **NOT VERIFIED:** private endpoint latency and mobile 50-fps requirement. Those require the planned physical-device Present and thermal samples.
