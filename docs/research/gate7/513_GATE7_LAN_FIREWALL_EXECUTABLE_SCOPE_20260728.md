# 513 Gate 7 LAN firewall executable scope (2026-07-28)

## VERIFIED

- The RFC1918 HTTPS listener is `<lan-ip>:8765`, but it runs through
  `<home>\\AppData\\Local\\Programs\\Python\\Python311\\python.exe`.
- The active authenticated WSS listener is `<lan-ip>:9201`, using the
  bundled Codex runtime Python executable.
- The pre-existing inbound allow rules target Python 3.12 and Python 3.14
  executable paths, not either active frontend executable.
- Local HTTPS to `<lan-ip>:8765` returns HTTP 200 and its TLS certificate
  carries the matching IP SAN.  This proves local server/TLS health but does
  not prove a phone can traverse Windows Firewall.
- Creating an inbound rule from the current non-elevated workspace session
  fails with Windows `Access is denied`.

## IMPLEMENTED

- `tools/enable_azrok_private_lan_firewall.ps1` is an elevation-required,
  idempotent rule installer.  It permits only TCP 8765/9201, only for their
  exact active executables, only on local address `<lan-ip>`, only from
  remote subnet `<lan-ip>/24`, and only on the Private profile.  Edge
  traversal is explicitly blocked.

## NOT VERIFIED

- A physical phone retry after the two rules are installed is still required.
  The acceptance evidence must include a phone HTTPS page load, authenticated
  WSS connection, shared loopback core admission, and no public listener.

