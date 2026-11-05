"""Network-address policy for the local-only preservation server.

The game socket may be shared with a second PC only on an explicitly chosen
private, loopback, or Tailscale/CGNAT IPv4 address. Do not infer an address
from the default route: virtual adapters can make that a public address.
"""

from __future__ import annotations

import ipaddress


_ALLOWED_BIND_NETWORKS = (
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    # Tailscale uses CGNAT. It is intentionally allowed for a private
    # preservation session even though IPv4Address.is_private is false here.
    ipaddress.IPv4Network("100.64.0.0/10"),
)


def parse_private_ipv4_bind(value: str) -> str:
    """Return a canonical explicitly-safe IPv4 bind address.

    ``0.0.0.0``, hostnames, IPv6, multicast, link-local, and public addresses
    are rejected. Multiple eligible NICs must be selected through ``--bind``
    rather than guessed.
    """

    raw = str(value or "").strip()
    try:
        address = ipaddress.IPv4Address(raw)
    except ipaddress.AddressValueError as exc:
        raise ValueError("--bind must be one explicit IPv4 address") from exc
    if not any(address in network for network in _ALLOWED_BIND_NETWORKS):
        raise ValueError(
            "--bind permits only loopback, RFC1918 private, or 100.64.0.0/10 "
            "Tailscale/CGNAT IPv4 addresses"
        )
    return str(address)
