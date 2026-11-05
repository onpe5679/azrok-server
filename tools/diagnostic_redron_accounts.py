"""Temporary loopback launcher for the two verified Redron test characters.

No account registry or character state is written. Keep redirect URLs out of logs.
"""

from __future__ import annotations

import json
import re
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from azrok_private_access import issue_browser_ticket, read_access_secret  # noqa: E402

PRODUCTION = Path("X:/home/u32ws/32dev/azroksrv")
ACCOUNTS = {
    "/one": ("aLqiY2zrTj3Vi", "a614c716959327a72546a335669_s0_c64646464_state_v1.json"),
    "/two": ("aoeK24gJwwTYh", "a616f654b3234674a7777545968_s0_c73647364_state_v1.json"),
}
PAGE = "https://playazrok.com/index_d3d9web_pathouse.html"


def pinned_parameters() -> dict[str, str]:
    source = (PROJECT / "tools/boxedwine_local/azrok_launch.js").read_text(encoding="utf-8")
    values = {}
    for key in ("appStem", "rootStem", "runtimeStem", "jitCacheUrl"):
        match = re.search(rf'const {key} = "([^"]+)";', source)
        if match is None:
            raise RuntimeError(f"missing launcher constant: {key}")
        values[key] = match.group(1)
    match = re.search(r"const runtimeIdentityFlags = (\[[^;]+\]);", source)
    if match is None:
        raise RuntimeError("missing launcher identity flags")
    flags = json.loads(match.group(1))
    return {
        "p": "run_azrok_account.bat",
        "app": values["appStem"],
        "root": values["rootStem"],
        "runtimeStem": values["runtimeStem"],
        "jitCacheUrl": values["jitCacheUrl"],
        **{flag: "1" for flag in flags},
        "autorun": "1",
        "ws": "wss://playazrok.com/azrok-ws",
        "inputPulse": "1",
    }


def checked_account(route: str) -> str:
    account, filename = ACCOUNTS[route]
    state = json.loads((PRODUCTION / "server_state" / filename).read_text(encoding="utf-8"))
    registry = json.loads((PRODUCTION / "logs/private_browser_accounts.json").read_text(encoding="utf-8"))
    if account not in registry.get("accounts", {}):
        raise RuntimeError("test account absent from production registry")
    if state.get("revision", 0) < 24 or "g1:r0:k3:a0:e1" not in state.get("completed_runtime_rows", []):
        raise RuntimeError("test character no longer matches verified Redron state")
    return account


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        # Neither account identifiers nor tickets belong in server logs.
        pass

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b"ready\n")
            return
        if self.path not in ACCOUNTS:
            self.send_error(404)
            return
        try:
            account = checked_account(self.path)
            secret = read_access_secret(PRODUCTION / "logs/private_runtime_192.token")
            browser_id = "browser_redron_diag_" + secrets.token_hex(16)
            ticket = issue_browser_ticket(secret, browser_id, account, ttl_seconds=3600)
            parameters = pinned_parameters()
            parameters.update(instance=ticket, args=account)
            location = PAGE + "?" + urlencode(parameters)
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError):
            self.send_error(503, "Diagnostic account unavailable")
            return
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Length", "0")
        self.end_headers()


if __name__ == "__main__":
    pinned_parameters()
    for route in ACCOUNTS:
        checked_account(route)
    server = ThreadingHTTPServer(("127.0.0.1", 18802), Handler)
    server.serve_forever()
