# 544. Private-account GUI management (2026-08-07)

> **SUPERSEDED by 565.** The fixed five-account pool and password recovery
> described here were replaced by dynamic accounts and one-time recovery codes.

## Scope

Add an operator-facing account-management view to the existing **loopback-only**
Azrok control GUI. This is for the private LAN/Tailscale browser-admission
registry only; it does not expose the game core, the GUI, or an account API to a
public address.

## VERIFIED

- `ControlServer` still binds only to `127.0.0.1`. The management API is served
  by that same server, so it cannot be reached through the private 8765/9201
  listeners.
- `PrivateAccountRegistry.admin_snapshot()` returns only account ID, launcher,
  auto-slot state, binding count, password-configured boolean, and a stable
  one-way browser display reference (`browser…<sha256-prefix>`). Full browser
  IDs, password plaintext, and password hashes are not returned.
- The GUI shows all seven supported profiles (`player`, `peer111`, and automatic
  `player2`--`player6`), their launcher, browser-binding count, slot status, and
  password-set state. It can set/reset a password for a selected profile.
- The GUI can release every browser binding for one selected profile only after
  the API receives the exact confirmation `RELEASE <account>`. This deletes
  neither the profile's saved game data nor its password hash; it merely makes
  that automatic slot available again or releases a preserved-profile binding.
- `tools/run_server_only.py` constructs the control GUI with the same
  `logs/private_browser_accounts.json` path used by the browser asset servers.
- Automatic guest capacity is now five independent profiles (`player2` through
  `player6`). The rebuilt source-only package
  `Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1.zip` contains exactly one
  launcher each for `player3`--`player6`; each has the same native-D3D9,
  `WINEDEBUG=-all,+seh`, Korean locale, and `acklog_tail.exe` preamble as the
  known `run_azrok_seh.bat` path. This records known Wine-side fault context;
  it is not evidence that an OX/Acknex BMAP access violation is bypassed.
- Static and temporary-loopback tests passed on 2026-08-07:
  - `python -m unittest tools.test_private_browser_admission`: 6 tests passed.
  - `python -m unittest tools.test_control_observability`: 17 tests passed,
    including HTTP API redaction/confirmation/password persistence.
  - `py_compile` passed for the changed Python modules.
  - `node` compiled the extracted GUI script with `new Function(...)`.

## NOT VERIFIED

- The already-running `9200/9300` process imported the preceding source before
  this change. A controlled core restart is required before the running GUI
  presents the new account panel; it was intentionally not restarted while the
  user reserved live play testing.
- The already-running 8765 asset listeners also imported the prior three-slot
  registry module. They need a controlled asset-listener restart before a new
  browser can receive `player5` or `player6`; the loopback core does not need
  to restart for that source/package change.
- A game connection does not carry the opaque browser ID through the WSS bridge
  into the legacy core. Therefore the GUI shows durable browser-binding state
  and live game-client state separately; it does not claim a per-live-client
  account mapping.

## Safety boundary

The only externally reachable private endpoints remain the authenticated
LAN/Tailscale HTTPS/WSS listeners. The account manager is local operator
control, not a phone-facing account service. No password value or hash is
rendered, logged by the new API, or included in API responses.
