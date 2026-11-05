> **SUPERSEDED by 544.** The original three-slot capacity conclusion was expanded
> to five automatic profiles (`player2`--`player6`) on 2026-08-07. Historical
> evidence below remains valid for the earlier package and allocator state.

# Gate 7 automatic guest-profile capacity and code-fallback removal

Date: 2026-07-28

## Scope

This change concerns only the private 192.168/16 and Tailscale browser entry
points.  The preservation core remains loopback-only, and neither the original
client executable nor saved game binaries were patched.

## Findings

- VERIFIED: The original new-device allocator had one automatic profile,
  `player2`.  Once it was bound to an earlier browser, a different unbound
  browser received the intended `409 no private guest profile` response.
- VERIFIED: The old landing page then presented an instance-code fallback.
  That fallback conflicts with the required browser-ID/ID-password admission
  model and is not an account continuation method.
- VERIFIED: The durable account registry now allocates the three independent
  new-device profiles `player2`, `player3`, and `player4`; it never allocates
  preserved `player` or `peer111` automatically.
- VERIFIED: A live HTTPS request to the current <lan-ip> frontend, while
  `player2` was occupied, returned a signed browser ticket and launcher
  `run_azrok_player3.bat`.  The disposable test binding was removed afterward;
  the already occupied real binding was retained.
- VERIFIED: `run_azrok_player3.bat` and `run_azrok_player4.bat` are source-only
  ZIP additions that launch the unchanged `Azrok.exe` with `-PL player3` and
  `-PL player4`, respectively.
- VERIFIED: The landing failure branch now offers retry only; it does not
  execute the copied instance-code form path.

## Current user flow

1. A new private browser opens the bare private HTTPS URL.
2. Its opaque browser ID receives the first unoccupied new-device profile and
   a short-lived transport ticket automatically.
3. The original game launches with that profile.  The ticket expiry never
   deletes the assigned profile or account data.
4. For an existing preserved account, the already-connected browser binds its
   existing profile, sets a password, and another device uses the dedicated
   account login page.  No copied instance code is involved.

## Verification boundary

- NOT VERIFIED: A physical phone launch through the expanded `player3` or
  `player4` profile and its full Plaza multiplayer lifecycle.
- NOT VERIFIED: The 50-FPS target on a physical handset; this is not inferred
  from browser-ID admission or the desktop measurement.
