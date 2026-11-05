#!/usr/bin/env python3
"""Run a loopback TCP echo target and the fixed WebSocket bridge together."""

import asyncio
import websockets

from ws_tcp_bridge import handle_connection, stamp


async def echo(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            payload = await reader.read(65536)
            if not payload:
                return
            writer.write(payload)
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def main() -> None:
    tcp_server = await asyncio.start_server(echo, "127.0.0.1", 19200)
    ws_server = await websockets.serve(
        lambda websocket: handle_connection(websocket, "127.0.0.1", 19200),
        "127.0.0.1",
        19201,
        subprotocols=["binary"],
        compression=None,
        max_size=None,
    )
    print(f"{stamp()} WINSOCK_SMOKE_SERVER_READY ws=127.0.0.1:19201 tcp=127.0.0.1:19200", flush=True)
    try:
        await asyncio.Future()
    finally:
        ws_server.close()
        await ws_server.wait_closed()
        tcp_server.close()
        await tcp_server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
