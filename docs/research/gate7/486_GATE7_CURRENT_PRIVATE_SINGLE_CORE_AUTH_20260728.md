# 486 Gate 7 current private single-core and auth verification (2026-07-28)

## VERIFIED

- The game core and GUI are currently loopback-only at `127.0.0.1:9200` and
  `127.0.0.1:9300`. The two permitted HTTPS/WSS frontends bind separately to
  the private RFC1918 and Tailscale addresses, and both bridge only to that
  one loopback core.
- There is no wildcard or public-IP listener on the service ports. The
  automatic bind-policy test suite passed all three cases: allowed RFC1918 /
  Tailscale addresses, rejected public/unspecified/non-IPv4 values, and exact
  listener snapshot reporting.
- A live no-token connection attempt to the private WSS endpoint was closed
  with WebSocket policy code `1008`. No credential or instance token is
  recorded in this document.
- The current shared GUI state reports two connected browser identities while
  the single core remains healthy.

## Boundary

This proves restricted ingress and shared-core isolation, not the still-open
current-run Plaza remote-actor proof. The browser sessions must naturally
enter Plaza and exchange the verified roster/position/leave packets before
Gate 5/Gate 7 multiplayer can be accepted.

