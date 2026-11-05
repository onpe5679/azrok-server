# LAN private-bind policy and two-PC preparation (2026-07-19)

## Scope

This record adds an explicit, local-network-only game socket bind option. It
does not change the default single-PC loopback behavior, deploy a firewall
rule, or modify the client binary.

## VERIFIED: binding implementation

- `azrok_launcher.py` accepts `--bind <IPv4>`, with the unchanged default
  `127.0.0.1`.
- `azrok_network.parse_private_ipv4_bind()` accepts only one literal IPv4
  address in `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`,
  `192.168.0.0/16`, or `100.64.0.0/10` (Tailscale/CGNAT).
- It rejects wildcard `0.0.0.0`, public addresses, link-local addresses,
  hostnames, and IPv6. The launcher fails before starting a game server when
  validation rejects the value.
- `AzrokServer` validates the same value at construction and binds the game
  listener to that exact address. It prints the exact listener address on
  startup.
- `/api/state` exposes `server.bind_host` and `server.listen_address` in
  addition to `server.port`, so clients and operators can determine the exact
  game listener without inferring an adapter from routing.

## VERIFIED: host-address inventory, not a route guess

The host had these IPv4 candidates during this verification:

| Interface | Address | Policy result |
|---|---:|---|
| Loopback | `127.0.0.1` | allowed default |
| NAS_Bridge | `<lan-ip>` | allowed LAN candidate |
| Tailscale | `<tailscale-ip>` | allowed remote-private candidate |
| Default Switch | `<lan-ip>` | allowed, but Hyper-V-only unless intentionally routed |
| WSL_B | `<public-ip>` | rejected public address |

The default route prefers the WSL_B adapter, so deriving an address from a UDP
route would select the rejected public address. The user must choose an
eligible interface explicitly; the server does not guess among multiple
private adapters.

## Regression evidence

```text
python -m py_compile azrok_network.py azrok_server.py azrok_launcher.py azrok_control.py
python -m unittest tools.test_network_bind -v
python azrok_launcher.py --help
python -m unittest discover -s tools -p 'test_*.py' -v

Ran 185 tests in 3.123s
OK
```

The policy tests cover every allowed range, including the observed LAN and
Tailscale addresses, and reject `<public-ip>`, wildcard, link-local,
hostname, and IPv6 inputs.

## NOT VERIFIED: manual two-PC proof remains required

No firewall rule was added and no second computer has connected yet. After
the user chooses either `<lan-ip>` (same LAN) or `<tailscale-ip>`
(Tailscale), the required manual proof is:

1. Start the server with the selected explicit `--bind` address.
2. Allow inbound TCP for the selected game port on the Windows **Private**
   profile only.
3. Start the second client with that same IP and port, then verify both
   clients complete login, see same-room movement, and exchange chat.

Do not automate installation or firewall provisioning until this manual
two-PC proof succeeds.
