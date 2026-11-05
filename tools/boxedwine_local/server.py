#!/usr/bin/env python3
"""Serve the pinned BoxedWine web build on loopback with HTTP Range support."""

from __future__ import annotations

import argparse
import json
import ssl
import os
import re
import sys
import tempfile
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
from azrok_network import parse_private_ipv4_bind
from azrok_private_access import (
    browser_ticket_claims,
    is_private_client,
    issue_browser_ticket,
    PrivateAccountRegistry,
    read_access_secret,
    valid_browser_id,
)


class RangeRequestHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".wasm": "application/wasm",
        ".zip": "application/zip",
        ".js": "text/javascript; charset=utf-8",
    }
    max_jit_cache_upload = 256 * 1024 * 1024
    private_access_secret: bytes | None = None
    private_account_registry: PrivateAccountRegistry | None = None
    private_ticket_ttl_seconds = 43200
    private_control_base_url = "http://127.0.0.1:9300"

    def do_GET(self) -> None:
        route = urlsplit(self.path).path
        if route == "/":
            # The 2012 homepage restoration is not part of this repository;
            # the bare root opens the server-selection page instead.
            self.path = "/azrok_server_list.html"
        if route == "/api/private-session":
            self.serve_private_session()
            return
        if route == "/api/private-server-status":
            self.serve_private_server_status()
            return
        super().do_GET()

    def serve_private_session(self) -> None:
        """Issue a same-origin ticket for one locally persisted browser ID."""
        if self.private_access_secret is None:
            self.send_error(404, "Private browser admission is disabled")
            return
        if not is_private_client(self.client_address[0]):
            self.send_error(403, "Private network required")
            return
        browser_id = self.headers.get("X-Azrok-Browser-Id", "")
        if not valid_browser_id(browser_id):
            self.send_error(400, "Valid browser identifier required")
            return
        if self.private_account_registry is None:
            self.send_error(503, "Private account registry unavailable")
            return
        try:
            account_id = self.private_account_registry.session_account(browser_id)
            launcher = self.private_account_registry.launcher_for(account_id)
        except ValueError as exc:
            self.send_error(409, str(exc))
            return
        ticket = issue_browser_ticket(
            self.private_access_secret,
            browser_id,
            account_id,
            ttl_seconds=self.private_ticket_ttl_seconds,
        )
        body = json.dumps(
            {
                "instance": ticket,
                "expires_in": self.private_ticket_ttl_seconds,
                "launcher": launcher,
                "account": account_id,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def serve_private_server_status(self) -> None:
        """Expose only the current connected-player count to the server list."""
        if not is_private_client(self.client_address[0]):
            self.send_error(403, "Private network required")
            return
        try:
            with urlopen(f"{self.private_control_base_url}/api/overview", timeout=2.0) as response:
                overview = json.load(response)
            players = overview.get("server", {}).get("players", [])
            if not isinstance(players, list):
                raise ValueError("invalid player overview")
            online = sum(
                1 for player in players
                if isinstance(player, dict) and player.get("connected") is True
            )
        except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError):
            self.send_error(503, "Preserved server status unavailable")
            return
        self._send_private_json({"ok": True, "online": online})

    def _private_browser_id(self) -> str | None:
        if not is_private_client(self.client_address[0]):
            self.send_error(403, "Private network required")
            return None
        browser_id = self.headers.get("X-Azrok-Browser-Id", "")
        if not valid_browser_id(browser_id):
            self.send_error(400, "Valid browser identifier required")
            return None
        if self.private_account_registry is None:
            self.send_error(503, "Private account registry unavailable")
            return None
        return browser_id

    def _private_json_body(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = 0
        if length <= 0 or length > 8192:
            self.send_error(413, "Invalid private account request")
            return None
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error(400, "Invalid private account JSON")
            return None
        if not isinstance(payload, dict):
            self.send_error(400, "Invalid private account JSON")
            return None
        return payload

    def _send_private_json(self, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def serve_private_account_recovery(self) -> None:
        browser_id = self._private_browser_id()
        payload = self._private_json_body()
        if browser_id is None or payload is None:
            return
        try:
            account_id = self.private_account_registry.import_recovery_code(
                browser_id, str(payload.get("recovery_code", ""))
            )
            self._send_private_json({"ok": True, "account": account_id})
        except ValueError as exc:
            self.send_error(403, str(exc))

    def serve_private_recovery_code(self) -> None:
        browser_id = self._private_browser_id()
        payload = self._private_json_body()
        if browser_id is None or payload is None:
            return
        try:
            recovery_code = self.private_account_registry.export_recovery_code(
                browser_id, rotate=payload.get("rotate") is True
            )
            self._send_private_json({"ok": True, "recovery_code": recovery_code})
        except ValueError as exc:
            self.send_error(400, str(exc))

    def _archive_private_account_state_via_overview(self, account_id: str) -> dict:
        """Compatibility reset path while an older core process is draining."""
        with urlopen(f"{self.private_control_base_url}/api/overview", timeout=3.0) as response:
            overview = json.load(response)
        players = (overview.get("server") or {}).get("players") or []
        if any(
            isinstance(player, dict)
            and player.get("connected") is True
            and player.get("account") == account_id
            for player in players
        ):
            raise ValueError("account is still connected")
        state_value = (overview.get("content") or {}).get("state_store_dir")
        if not isinstance(state_value, str) or not state_value:
            raise ValueError("state store unavailable")
        state_dir = Path(state_value).resolve()
        project_root = PROJECT_ROOT.resolve()
        if state_dir != project_root / "server_state" and project_root not in state_dir.parents:
            raise ValueError("unsafe state store path")
        account_hex = account_id.encode("ascii").hex()
        prefix = f"a{account_hex}_s"
        names = [
            path.name for path in state_dir.iterdir()
            if path.is_file() and path.name.startswith(prefix)
            and (path.name.endswith("_state_v1.json")
                 or path.name.endswith("_c2s0007.bin"))
        ]
        legacy_names = set()
        for name in names:
            for suffix in ("_state_v1.json", "_c2s0007.bin"):
                if not name.endswith(suffix):
                    continue
                body = name[len(prefix):-len(suffix)]
                _slot, marker, name_hex = body.partition("_c")
                if marker == "_c" and name_hex:
                    legacy_names.add(f"{name_hex}_c2s0007.bin")
        for name in sorted(legacy_names):
            if name not in names and (state_dir / name).is_file():
                names.append(name)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        archive_dir = state_dir / "reset_accounts" / f"{account_id}_{stamp}"
        archive_dir.mkdir(parents=True, exist_ok=False)
        moved = []
        try:
            for name in names:
                source = state_dir / name
                destination = archive_dir / name
                os.replace(source, destination)
                moved.append((source, destination))
        except OSError:
            for source, destination in reversed(moved):
                try:
                    os.replace(destination, source)
                except OSError:
                    pass
            raise
        return {
            "ok": True,
            "account": account_id,
            "archived_files": len(moved),
            "archive_dir": str(archive_dir),
            "compatibility_path": True,
        }

    def serve_private_account_reset(self) -> None:
        """Reset the requesting browser to a newly allocated empty account."""
        browser_id = self._private_browser_id()
        payload = self._private_json_body()
        if browser_id is None or payload is None:
            return
        if payload.get("confirmation") != "RESET":
            self.send_error(400, "Explicit account reset confirmation required")
            return
        try:
            old_account = self.private_account_registry.session_account(browser_id)
            control_body = json.dumps({
                "account": old_account,
                "confirmation": f"RESET {old_account}",
            }).encode("utf-8")
            request = Request(
                f"{self.private_control_base_url}/api/private-accounts/reset-state",
                data=control_body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=5.0) as response:
                    archived = json.load(response)
            except HTTPError as exc:
                if exc.code != 404:
                    raise
                archived = self._archive_private_account_state_via_overview(
                    old_account
                )
            if not archived.get("ok"):
                raise ValueError(str(archived.get("error") or "account reset rejected"))
            replacement = self.private_account_registry.replace_browser_account(
                browser_id, old_account
            )
        except HTTPError as exc:
            self.send_error(exc.code if 400 <= exc.code < 600 else 502,
                            "Account reset rejected; close the running game first")
            return
        except (URLError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            self.send_error(409, str(exc))
            return
        self._send_private_json({
            "ok": True,
            **replacement,
            "archived_files": int(archived.get("archived_files") or 0),
        })

    def serve_private_chat_say(self) -> None:
        """Relay authenticated browser IME text through the preserved 0x006A path."""
        if self.private_access_secret is None or self.private_account_registry is None:
            self.send_error(503, "Private chat bridge unavailable")
            return
        if not is_private_client(self.client_address[0]):
            self.send_error(403, "Private network required")
            return
        payload = self._private_json_body()
        if payload is None:
            return
        ticket = payload.get("instance")
        message = payload.get("message")
        claims = browser_ticket_claims(self.private_access_secret, ticket)
        if claims is None:
            self.send_error(403, "Valid private session required")
            return
        if not isinstance(message, str):
            self.send_error(400, "Chat message must be text")
            return
        message = message.strip()
        try:
            encoded = message.encode("cp949")
        except UnicodeEncodeError:
            self.send_error(400, "Chat message contains unsupported characters")
            return
        if not encoded or len(encoded) > 120 or any(ord(char) < 0x20 for char in message):
            self.send_error(400, "Chat message must contain 1..120 CP949 bytes")
            return

        try:
            account_id = str(claims["account_id"])
            with urlopen(f"{self.private_control_base_url}/api/overview", timeout=2.0) as response:
                overview = json.load(response)
            players = [
                player for player in overview.get("server", {}).get("players", [])
                if player.get("connected") and player.get("account") == account_id
            ]
            if not players:
                self.send_error(409, "Preserved account is not connected")
                return
            entity_id = max(players, key=lambda player: int(player.get("entity_id") or 0))["entity_id"]
            body = json.dumps(
                {"entity_id": int(entity_id), "message": message},
                ensure_ascii=False,
            ).encode("utf-8")
            request = Request(
                f"{self.private_control_base_url}/api/chat/say",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=2.0) as response:
                result = json.load(response)
        except (HTTPError, URLError, OSError, ValueError, KeyError, json.JSONDecodeError):
            self.send_error(502, "Private chat relay failed")
            return
        self._send_private_json(
            {"ok": bool(result.get("ok")), "entity_id": int(entity_id), "message": message}
        )

    def serve_private_chat_state(self) -> None:
        """Report whether the ticket's connected character is actually in Plaza."""
        if self.private_access_secret is None or self.private_account_registry is None:
            self.send_error(503, "Private chat bridge unavailable")
            return
        if not is_private_client(self.client_address[0]):
            self.send_error(403, "Private network required")
            return
        payload = self._private_json_body()
        if payload is None:
            return
        ticket = payload.get("instance")
        claims = browser_ticket_claims(self.private_access_secret, ticket)
        if claims is None:
            self.send_error(403, "Valid private session required")
            return
        try:
            account_id = str(claims["account_id"])
            with urlopen(f"{self.private_control_base_url}/api/overview", timeout=2.0) as response:
                overview = json.load(response)
            players = [
                player for player in overview.get("server", {}).get("players", [])
                if player.get("connected") and player.get("account") == account_id
            ]
        except (HTTPError, URLError, OSError, ValueError, KeyError, json.JSONDecodeError):
            self.send_error(502, "Private chat state unavailable")
            return
        if not players:
            self._send_private_json({"ok": True, "ready": False, "entity_id": None})
            return
        player = max(players, key=lambda item: int(item.get("entity_id") or 0))
        room_kind = player.get("room_kind")
        self._send_private_json({
            "ok": True,
            "ready": room_kind == 27,
            "entity_id": int(player["entity_id"]),
            "room_kind": room_kind,
        })

    def do_POST(self) -> None:
        """Accept the explicit local JIT-record export used by the profiler."""
        route = urlsplit(self.path).path
        private_routes = {
            "/api/private-account-recovery": self.serve_private_account_recovery,
            "/api/private-recovery-code": self.serve_private_recovery_code,
            "/api/private-account-reset": self.serve_private_account_reset,
            "/api/private-chat-state": self.serve_private_chat_state,
            "/api/private-chat-say": self.serve_private_chat_say,
        }
        if route in private_routes:
            private_routes[route]()
            return
        if route != "/api/jit-cache-upload":
            self.send_error(404, "Unknown API route")
            return
        # The profiler upload endpoint is intentionally never exposed to a
        # phone/LAN client; remote play receives only static assets.
        if self.client_address[0] not in {"127.0.0.1", "::1"}:
            self.send_error(403, "JIT cache upload is loopback-only")
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
        if length <= 0 or length > self.max_jit_cache_upload:
            self.send_error(413, "Invalid JIT cache size")
            return

        root = Path(self.directory).resolve()
        output_dir = root / "profiles"
        output_dir.mkdir(parents=True, exist_ok=True)
        record_name = self.headers.get("X-Azrok-Jit-Record-Name", "azrok-jit-record-raw")
        if not re.fullmatch(r"(?:azrok-jit-record-raw|azrok-jit-record-int9aspecialized1)", record_name):
            self.send_error(400, "Invalid JIT record identity")
            return
        output = output_dir / f"{record_name}.zip"
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="wb", dir=output_dir, prefix="azrok-jit-record-",
                    suffix=".tmp", delete=False) as temp:
                temp_path = Path(temp.name)
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ConnectionError("short JIT cache upload")
                    temp.write(chunk)
                    remaining -= len(chunk)
            os.replace(temp_path, output)
            body = f'{{"ok":true,"bytes":{length},"path":"profiles/{output.name}"}}'.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            self.send_error(500, f"JIT cache upload failed: {exc}")

    def translate_path(self, path: str) -> str:
        """Keep compatibility with absolute URLs embedded by the public build."""
        parts = urlsplit(path)
        route = parts.path
        aliases = {
            "/boxedwine/build/default/": "/assets/",
            "/boxedwine/fs/": "/fs/",
            "/boxedwine/apps/": "/apps/",
        }
        for public_prefix, local_prefix in aliases.items():
            if route.startswith(public_prefix):
                route = local_prefix + route[len(public_prefix):]
                break
        rewritten = urlunsplit(("", "", route, parts.query, parts.fragment))
        return super().translate_path(rewritten)

    def end_headers(self) -> None:
        route = urlsplit(self.path).path.lower()
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        if route.endswith(".html") or route == "/" or route.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        elif route.endswith((".zip", ".wasm", ".js", ".png", ".jpg", ".gif", ".ico", ".mp4")):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()

        try:
            source = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None

        stat = os.fstat(source.fileno())
        size = stat.st_size
        range_header = self.headers.get("Range")
        self._range_remaining = None

        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
            if not match:
                source.close()
                self.send_error(416, "Invalid byte range")
                return None

            first, last = match.groups()
            if first:
                start = int(first)
                end = int(last) if last else size - 1
            elif last:
                length = int(last)
                start = max(0, size - length)
                end = size - 1
            else:
                source.close()
                self.send_error(416, "Invalid byte range")
                return None

            if start >= size or start > end:
                source.close()
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None

            end = min(end, size - 1)
            length = end - start + 1
            source.seek(start)
            self._range_remaining = length
            self.send_response(206)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(length))
            self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
            self.end_headers()
            return source

        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Length", str(size))
        self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
        self.end_headers()
        return source

    def copyfile(self, source, outputfile) -> None:
        remaining = getattr(self, "_range_remaining", None)
        while remaining is None or remaining:
            chunk_size = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
            chunk = source.read(chunk_size)
            if not chunk:
                break
            outputfile.write(chunk)
            if remaining is not None:
                remaining -= len(chunk)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bind", default="127.0.0.1",
        help="explicit loopback, RFC1918, or Tailscale IPv4 asset bind",
    )
    parser.add_argument(
        "--account-registry",
        type=Path,
        help="durable browser-to-preserved-account binding registry",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--tls-cert", type=Path, help="PEM certificate for private HTTPS")
    parser.add_argument("--tls-key", type=Path, help="PEM private key for private HTTPS")
    parser.add_argument(
        "--access-secret-file",
        type=Path,
        help="shared private-secret file used to issue browser admission tickets",
    )
    # Test artifacts can be served through the same COOP/COEP policy without
    # copying them into the production asset root.
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    if bool(args.tls_cert) != bool(args.tls_key):
        parser.error("--tls-cert and --tls-key must be supplied together")
    try:
        bind_host = parse_private_ipv4_bind(args.bind)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        access_secret = read_access_secret(args.access_secret_file) if args.access_secret_file else None
    except (OSError, ValueError) as exc:
        parser.error(f"invalid --access-secret-file: {exc}")
    asset_root = (args.root or Path(__file__).resolve().parent).resolve()
    account_registry = None
    if access_secret is not None:
        registry_path = args.account_registry or (args.access_secret_file.parent / "private_browser_accounts.json")
        account_registry = PrivateAccountRegistry(registry_path, access_secret)
    log = open(Path(__file__).resolve().parent / "localhost.log", "a",
               encoding="utf-8", buffering=1)
    sys.stdout = log
    sys.stderr = log
    handler_type = type(
        "PrivateRangeRequestHandler",
        (RangeRequestHandler,),
        {
            "private_access_secret": access_secret,
            "private_account_registry": account_registry,
        },
    )
    handler = lambda *a, **kw: handler_type(*a, directory=str(asset_root), **kw)
    server = ThreadingHTTPServer((bind_host, args.port), handler)
    scheme = "http"
    if args.tls_cert:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(args.tls_cert, args.tls_key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        scheme = "https"
    print(f"BoxedWine local: {scheme}://{bind_host}:{args.port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
