#!/usr/bin/env python3
"""One-shot authenticated public WSS probe without allocating an account."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import time
from urllib.parse import quote

import websockets

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from azrok_private_access import issue_browser_ticket, read_access_secret


def frame(opcode: int, payload: bytes) -> bytes:
    return len(payload).to_bytes(2, "little") + opcode.to_bytes(2, "little") + payload


def opcodes(data: bytes) -> list[int]:
    result = []
    offset = 0
    while offset + 4 <= len(data):
        size = int.from_bytes(data[offset:offset + 2], "little")
        opcode = int.from_bytes(data[offset + 2:offset + 4], "little")
        end = offset + 4 + size
        if end > len(data):
            break
        result.append(opcode)
        offset = end
    return result


async def main() -> None:
    secret = read_access_secret(ROOT / "logs" / "private_runtime_192.token")
    account = "deployprobe"
    ticket = issue_browser_ticket(
        secret,
        "browser_deploy_probe_20260827",
        account,
        now=int(time.time()),
        ttl_seconds=300,
    )
    uri = "wss://playazrok.com/azrok-ws?instance=" + quote(ticket, safe="")
    async with websockets.connect(
        uri,
        subprotocols=["binary"],
        compression=None,
        open_timeout=15,
        close_timeout=3,
        max_size=None,
    ) as websocket:
        login = bytearray(0x6A)
        login[0] = 1
        login[1:1 + len(account)] = account.encode("ascii")
        await websocket.send(frame(0x0000, bytes(login)))
        await websocket.send(frame(0x0016, b"\x00"))
        response = await asyncio.wait_for(websocket.recv(), timeout=15)
        if not isinstance(response, bytes):
            raise RuntimeError("public bridge returned a text frame")
        seen = opcodes(response)
        if not seen:
            raise RuntimeError(f"no complete Azrok frames in {len(response)} bytes")
        print(f"PUBLIC_WSS_OK bytes={len(response)} opcodes={[hex(value) for value in seen]}")


if __name__ == "__main__":
    asyncio.run(main())

