# 543. Private admission capacity, safe guest launcher route, and game context menu (2026-08-07)

## Scope

This change is limited to the private 192.168/16 and Tailscale browser entry
route.  It neither patches `Azrok.exe` nor publishes the preservation core or
control GUI to a public address.

## VERIFIED

- The failing remote host was observed directly in `tools/boxedwine_local/localhost.log`:
  `<lan-ip>` reached the HTTPS landing page, then received
  `409 no private guest profile is currently available`.  This was an
  exhausted automatic-profile pool, not a certificate, firewall, or public-IP
  failure.
- Before the change the durable registry had exactly three assigned automatic
  profiles: `player2`, `player3`, and `player4`.
- `PrivateAccountRegistry` now keeps the existing browser bindings and assigns
  the next new browser in the five-profile pool `player2` through `player6`.
  It never automatically assigns preserved `player` or `peer111`.
- The rebuilt source-only guest package is
  `tools/boxedwine_local/apps/Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1.zip`
  (`SHA-256 D87E4447169BEE588CBD942EB127BF19E9D7433452347BFCCEB4E17B2DDE0DD9`).
  Its `run_azrok_player3.bat` through `run_azrok_player6.bat` each retain the
  native D3D9 override, `WINEDEBUG=-all,+seh`, Korean locale, and `acklog_tail`
  preamble before launching the unchanged executable.
- `python -m unittest tools.test_private_browser_admission tools.test_control_observability`
  passed 23 tests after the capacity change.  The ZIP was also inspected
  directly: each of those four launchers exists once and has the expected SEH
  and native-D3D9 preamble.
- Only the two private asset listeners were restarted after the code/package
  update: `<lan-ip>:8765` and `<tailscale-ip>:8765`.  The core remains
  loopback-only on `127.0.0.1:9200`; no public listener was introduced.
- The landing page now reports a capacity (`409`) failure separately from
  invalid browser ID, private-network rejection, and temporary registry
  unavailability.  It still offers retry and existing-account login; it never
  restores copied instance-code entry.
- The D3D9Web page now suppresses the browser context menu in capturing phase
  when the target is inside `#dropzone`.  This covers BoxedWine layers created
  over the original canvas while retaining the normal context menu elsewhere
  on the page.

## OX exception boundary

- VERIFIED: `WINEDEBUG=-all,+seh` is the existing continue-running route for
  the Wine unix-call / GStreamer BGM access violation (523).  The newly added
  guest profiles no longer omit that route.
- VERIFIED: the documented browser OX crash is a different `acknex.dll`
  invalid-BMAP dereference after question delivery (534), followed by Wine's
  unhandled-exception path.  Enabling `+seh` is **not** evidence that this OX
  fault can safely be ignored; no blanket exception swallowing was added.

## NOT VERIFIED

- The remote physical browser has not yet retried after the listener restart;
  its next bare-URL request should receive `player5` while the three existing
  bindings are preserved.
- A physical OX round through the new SEH guest package has not been claimed
  fixed.  User-driven testing is required; if it still exits, the next evidence
  must be its post-C8/OX fault trace rather than an assumption that it was the
  BGM unix-call exception.
- The game-area context-menu suppression is statically verified but awaits a
  user right-click on a live runtime-created layer.
