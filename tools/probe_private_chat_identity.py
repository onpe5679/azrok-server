"""Bounded public WSS/HTTP admission probe; never prints credentials or sends chat."""
import asyncio
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import websockets
from azrok_private_access import issue_browser_ticket, read_access_secret


async def main():
    secret = read_access_secret(Path(sys.argv[1]))
    account = 'chatprobe0927'
    assert len(account) == 13
    ticket = issue_browser_ticket(secret, 'browser_chat_probe_20260927', account,
                                  now=int(time.time()), ttl_seconds=300)
    def frame(op, data):
        return len(data).to_bytes(2, 'little') + op.to_bytes(2, 'little') + data
    def state():
        req = Request('https://playazrok.com/api/private-chat-state',
                      data=json.dumps({'instance': ticket}).encode(),
                      headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}, method='POST')
        with urlopen(req, timeout=15) as response:
            return json.load(response)
    async with websockets.connect('wss://playazrok.com/azrok-ws?instance=' + quote(ticket, safe=''),
                                  subprotocols=['binary'], compression=None,
                                  open_timeout=15, close_timeout=3) as ws:
        login = bytearray(106)
        login[0] = 1
        login[1:14] = account.encode()
        await ws.send(frame(0, login))
        await ws.send(frame(0x16, b'\x00'))
        await asyncio.wait_for(ws.recv(), 15)
        before = await asyncio.to_thread(state)
        assert before['entity_id'] is not None and before['ready'] is False, before
        # Protocol-only stage-0 report; this is not a rendered Plaza assertion.
        await ws.send(frame(0x64, b'\x00'))
        await asyncio.wait_for(ws.recv(), 15)
        after = await asyncio.to_thread(state)
        assert after['ready'] is True and after['room_kind'] == 27, after
        assert after['entity_id'] == before['entity_id']
        print('PUBLIC_CHAT_IDENTITY_PASS account_length=13 pre_plaza=False plaza=True same_entity=True')


if __name__ == '__main__':
    asyncio.run(main())
