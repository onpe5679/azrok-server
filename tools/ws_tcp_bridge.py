#!/usr/bin/env python3
"""Fixed-target WebSocket-to-TCP bridge for the browser Azrok client.

Emscripten's SOCKFS maps a guest TCP connection to a binary WebSocket.  This
bridge restores byte-stream semantics against the local preservation server;
it deliberately exposes no client-selected target and therefore isn't an open
proxy.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from datetime import datetime, timezone
import hmac
import ssl
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

import websockets

# This script is executed from ``tools/`` by Python, so add the project root
# explicitly before importing the shared bind policy.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from azrok_network import parse_private_ipv4_bind
from azrok_private_access import (
    browser_ticket_claims,
    is_private_client,
    read_access_secret,
)


def request_admission_claims(websocket, expected_token: str, access_secret: bytes | None) -> dict | None:
    """Validate admission and return its authenticated account claim."""
    query = parse_qs(urlsplit(getattr(websocket, "path", "")).query)
    supplied = query.get("instance", [""])[0]
    if access_secret is not None:
        return browser_ticket_claims(access_secret, supplied)
    if expected_token and hmac.compare_digest(supplied, expected_token):
        return {"version": 0, "account_id": None}
    return None


async def read_account_bound_login(websocket, expected_account: str) -> bytes:
    """Buffer and verify the first original-client login packet.

    Wire framing is ``payload_size:u16, opcode:u16, payload``.  A v2 browser
    ticket may reach the loopback core only when its signed account is the
    account in the first C2S 0x0000/106-byte login payload.
    """
    buffered = bytearray()
    total_size = None
    while total_size is None or len(buffered) < total_size:
        message = await websocket.recv()
        if isinstance(message, str):
            raise ValueError("text WebSocket frame rejected; binary required")
        buffered.extend(message)
        if len(buffered) > 256 * 1024:
            raise ValueError("login prefix exceeds private relay limit")
        if total_size is None and len(buffered) >= 4:
            payload_size = int.from_bytes(buffered[0:2], "little")
            opcode = int.from_bytes(buffered[2:4], "little")
            if opcode != 0x0000 or payload_size != 0x6A:
                raise ValueError("first game packet must be C2S 0x0000/106B")
            total_size = 4 + payload_size
    account_raw = bytes(buffered[5:18]).split(b"\x00", 1)[0]
    try:
        account = account_raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("login account must be ASCII") from exc
    if not hmac.compare_digest(account, expected_account):
        raise ValueError("ticket account does not match game login")
    return bytes(buffered)


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


async def relay_client_to_server(websocket, writer: asyncio.StreamWriter) -> None:
    async for message in websocket:
        if isinstance(message, str):
            raise ValueError("text WebSocket frame rejected; binary required")
        writer.write(message)
        await writer.drain()
        print(f"{stamp()} WS2TCP bytes={len(message)}", flush=True)


async def relay_server_to_client(
    reader: asyncio.StreamReader, websocket
) -> None:
    while True:
        payload = await reader.read(65536)
        if not payload:
            return
        await websocket.send(payload)
        print(f"{stamp()} TCP2WS bytes={len(payload)}", flush=True)


async def handle_connection(
    websocket, tcp_host: str, tcp_port: int, instance_token: str, access_secret: bytes | None
) -> None:
    peer = getattr(websocket, "remote_address", None)
    print(f"{stamp()} WS_ACCEPT peer={peer}", flush=True)
    peer_host = peer[0] if isinstance(peer, tuple) and peer else None
    if not is_private_client(peer_host):
        print(f"{stamp()} WS_REJECT peer={peer} reason=non_private_source", flush=True)
        await websocket.close(code=1008, reason="private network required")
        return
    claims = request_admission_claims(websocket, instance_token, access_secret)
    if claims is None:
        print(f"{stamp()} WS_REJECT peer={peer} reason=bad_private_admission", flush=True)
        await websocket.close(code=1008, reason="private browser admission required")
        return
    account_id = claims.get("account_id")
    initial = b""
    if account_id is not None:
        try:
            initial = await read_account_bound_login(websocket, str(account_id))
        except Exception as error:
            print(f"{stamp()} WS_REJECT peer={peer} reason=account_claim error={error!r}", flush=True)
            await websocket.close(code=1008, reason="private account claim rejected")
            return
    try:
        reader, writer = await asyncio.open_connection(tcp_host, tcp_port)
    except Exception as error:
        print(f"{stamp()} TCP_CONNECT_FAIL target={tcp_host}:{tcp_port} error={error!r}", flush=True)
        await websocket.close(code=1011, reason="TCP target unavailable")
        return

    if initial:
        writer.write(initial)
        await writer.drain()
    print(
        f"{stamp()} TCP_CONNECTED target={tcp_host}:{tcp_port} "
        f"account={account_id or 'legacy'}",
        flush=True,
    )
    tasks = {
        asyncio.create_task(relay_client_to_server(websocket, writer)),
        asyncio.create_task(relay_server_to_client(reader, websocket)),
    }
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
    except Exception as error:
        print(f"{stamp()} RELAY_END peer={peer} error={error!r}", flush=True)
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()
        with contextlib.suppress(Exception):
            await websocket.close()
        print(f"{stamp()} WS_CLOSED peer={peer}", flush=True)


async def run(args: argparse.Namespace) -> None:
    handler = lambda websocket: handle_connection(
        websocket, args.tcp_host, args.tcp_port, args.instance_token, args.access_secret
    )
    tls_context = None
    if args.tls_cert:
        tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls_context.load_cert_chain(args.tls_cert, args.tls_key)
    async with websockets.serve(
        handler,
        args.ws_host,
        args.ws_port,
        subprotocols=["binary"],
        compression=None,
        max_size=None,
        ping_interval=20,
        ssl=tls_context,
    ):
        print(
            f"{stamp()} WS_TCP_BRIDGE_READY "
            f"ws={args.ws_host}:{args.ws_port} tcp={args.tcp_host}:{args.tcp_port} "
            f"admission={'browser-ticket' if args.access_secret else ('legacy-token' if args.instance_token else 'loopback-only')}",
            flush=True,
        )
        await asyncio.Future()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ws-host", default="127.0.0.1")
    parser.add_argument("--ws-port", type=int, default=9201)
    parser.add_argument("--tcp-host", default="127.0.0.1")
    parser.add_argument("--tcp-port", type=int, default=9200)
    parser.add_argument("--tls-cert", type=Path, help="PEM certificate for private WSS")
    parser.add_argument("--tls-key", type=Path, help="PEM private key for private WSS")
    parser.add_argument(
        "--instance-token",
        default="",
        help="optional legacy WebSocket ?instance= token during private-ticket migration",
    )
    parser.add_argument(
        "--access-secret-file",
        type=Path,
        help="shared private-secret file used to validate browser-issued tickets",
    )
    args = parser.parse_args()
    if bool(args.tls_cert) != bool(args.tls_key):
        parser.error("--tls-cert and --tls-key must be supplied together")
    try:
        args.ws_host = parse_private_ipv4_bind(args.ws_host)
        args.tcp_host = parse_private_ipv4_bind(args.tcp_host)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        args.access_secret = read_access_secret(args.access_secret_file) if args.access_secret_file else None
    except (OSError, ValueError) as exc:
        parser.error(f"invalid --access-secret-file: {exc}")
    if args.ws_host != "127.0.0.1" and not (args.instance_token or args.access_secret):
        parser.error("a non-loopback bridge requires --instance-token or --access-secret-file")
    return args


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
