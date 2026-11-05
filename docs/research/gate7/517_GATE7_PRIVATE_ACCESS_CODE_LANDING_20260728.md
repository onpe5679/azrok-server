# 517 Gate 7 private access-code landing (2026-07-28)

## VERIFIED

- The physical-phone source address `<lan-ip>` reached the private WSS
  bridge on port 9201.  The bridge rejected it with `bad_instance_token`, so
  this is not a firewall, TLS, or public-address failure.
- The bridge intentionally requires the per-instance `instance` value for
  every non-loopback WSS connection and closes a missing/incorrect value with
  policy code 1008.
- A bare HTTPS URL previously selected an obsolete `run_azrok.bat` image;
  forwarding it to the current launcher without a credential merely moved the
  failure to WSS authentication.

## IMPLEMENTED

- The bare private HTTPS page is now a small access-code landing page.  It
  never launches the obsolete Gate 2 Wine image and it never attempts WSS
  without a code.
- A complete private URL containing `instance` still forwards directly to the
  current D3D9Web launcher.  The landing page also accepts an explicitly
  entered 20--128-character URL-safe access code and passes it only as the
  bridge's existing `instance` query credential.
- `legacy=1` remains the only route to the retained Gate 2 diagnostic page.
- Static launcher tests now parse both the game page and landing page; the
  live private HTTPS server returned the new landing markup.

## NOT VERIFIED

- A physical-phone code entry followed by full guest boot, authenticated WSS
  relay, and shared-core admission is still required.  The browser identifier
  or distinct username layer requested for multiple devices remains separate
  from this shared bridge-access credential.
