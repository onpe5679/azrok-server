# 519 Gate 7 browser-identifier admission correction (2026-07-28)

## VERIFIED

- The prior bare-LAN route required a copied, static bridge token.  That does
  not meet the requested first-device flow and is not account identity.
- The preservation core already persists character state by original client
  account/character key, independently of the browser bridge credential.

## VERIFIED (running private frontends)

- The four replacement frontends now listen only on `<lan-ip>:8765`,
  `<lan-ip>:9201`, `<tailscale-ip>:8765`, and `<tailscale-ip>:9201`.
  The game core and GUI remain loopback-only at `127.0.0.1:9200` and
  `127.0.0.1:9300`; the service-port listener scan has zero public/wildcard
  rows.
- A browser-identifier ticket was issued by both private HTTPS endpoints and
  accepted by both WSS bridges.  Each accepted bridge connection targeted only
  `127.0.0.1:9200`, then closed cleanly; the GUI afterward reported zero
  residual clients.
- A fresh bare private page redirected without a copied code to the current
  game launcher with a ticket and the unused `run_azrok_multi2.bat` profile.
  Its local browser identifier persisted and the fallback code form was absent.
- The pre-existing static URL admission was separately accepted during the
  migration, so current full game URLs are not invalidated by the frontend
  change.

## IMPLEMENTED

- `azrok_private_access.py` defines a private-source check plus a signed,
  12-hour browser-admission ticket.  The ticket is bound to an opaque browser
  identifier and is validated by the WSS bridge; it is not an Azrok account,
  character, or saved-game expiry.
- The HTTPS asset server can issue that ticket at same-origin
  `/api/private-session`; the bare launcher stores a stable browser ID and
  requests a ticket automatically.  It assigns only the unused guest
  `player2` launcher to a new browser, never silently claims the preserved
  `player` or `peer111` identities.
- The durable local registry records browser-to-original-account bindings and
  only an scrypt password verifier.  An existing full game URL first binds
  its own browser to its original launcher; the owner may then set a local
  password.  A new device can use the explicit account-login route once,
  after which it receives the same account launcher on ordinary bare visits.
- If an older frontend process has not yet been restarted, the page preserves
  the previous manual-code fallback rather than failing closed into an
  unusable blank page.
- The old static token remains accepted during the frontend migration so an
  already-open game URL is not immediately invalidated.

## NOT VERIFIED

- A physical phone still needs to complete the automatic bare-URL boot and,
  separately, the old-account password login/reconnect path.  The registry and
  password migration have unit coverage but no user account password was set
  or tested during this run.
  The ticket lifetime must never be used as an account lifetime.
