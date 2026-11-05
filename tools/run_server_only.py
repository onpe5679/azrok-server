"""Run the local preservation server without launching the game client.

This is useful for preparing or inspecting one isolated profile before the
original client connects through ``azrok_launcher.py --reuse-server``.
"""

import argparse
import os
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description="Run the Azrok server only")
    parser.add_argument(
        "--bind", default="127.0.0.1",
        help="explicit loopback, RFC1918, or Tailscale game-server bind",
    )
    parser.add_argument("--port", type=int, default=9207)
    parser.add_argument("--control-port", type=int, default=9300)
    parser.add_argument(
        "--content-profile",
        choices=("minimal", "playable", "shipped"),
        default="playable",
    )
    parser.add_argument("--state-namespace", default="")
    parser.add_argument("--access-secret-file", type=Path)
    parser.add_argument(
        "--auto-select-existing",
        action="store_true",
        help="opt in to the verified C2S 0x0005 slot-0 continuation after lobby bootstrap",
    )
    parser.add_argument(
        "--auto-select-heartbeats",
        type=int,
        default=8,
        choices=range(1, 9),
        metavar="1..8",
        help="test-only paced lobby heartbeats before the exact 0x0005 continuation",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    os.environ["AZROK_CONTENT_PROFILE"] = args.content_profile
    if args.state_namespace:
        os.environ["AZROK_STATE_NAMESPACE"] = args.state_namespace
    else:
        os.environ.pop("AZROK_STATE_NAMESPACE", None)
    if args.auto_select_existing:
        os.environ["AZROK_AUTO_SELECT_EXISTING"] = "1"
        os.environ["AZROK_AUTO_SELECT_HEARTBEATS"] = str(args.auto_select_heartbeats)
    else:
        os.environ.pop("AZROK_AUTO_SELECT_EXISTING", None)
        os.environ.pop("AZROK_AUTO_SELECT_HEARTBEATS", None)
    sys.path.insert(0, str(root))

    from azrok_control import ControlServer
    from azrok_network import parse_private_ipv4_bind
    from azrok_private_access import PrivateAccountRegistry, read_access_secret
    from azrok_server import AzrokServer

    try:
        bind_host = parse_private_ipv4_bind(args.bind)
    except ValueError as exc:
        parser.error(str(exc))
    server = AzrokServer(args.port, log_dir=str(root), bind_host=bind_host)
    # The GUI remains loopback-only, but reads the same durable registry used
    # by both LAN/Tailscale HTTPS asset listeners.
    recovery_secret = (
        read_access_secret(args.access_secret_file) if args.access_secret_file else None
    )
    private_accounts = PrivateAccountRegistry(
        root / 'logs' / 'private_browser_accounts.json', recovery_secret
    )
    control = ControlServer(
        server,
        port=args.control_port,
        private_account_registry=private_accounts,
    )
    server.start()
    if args.control_port:
        control.start()
    print(
        f"[SERVER-ONLY] tcp={bind_host}:{args.port} "
        f"control=127.0.0.1:{args.control_port} "
        f"profile={args.content_profile} namespace={args.state_namespace or '<root>'}",
        flush=True,
    )
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        control.stop()
        server.stop()


if __name__ == "__main__":
    main()
