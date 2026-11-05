# Gate 2c: standalone WSAEventSelect reproduction

Status: VERIFIED

## Purpose

Separate the browser networking failure from the original executable, D3D9
backend, game protocol, and content flow.

## Test

`tools/d3d9_web_backend/winsock_smoke.cpp` was changed from synchronous
`recv` to the same Windows API sequence used by the client:

```text
WSAEventSelect(socket, event, FD_READ | FD_CLOSE)
send(echo payload)
WSAWaitForMultipleEvents(event, 5000 ms)
WSAEnumNetworkEvents
recv
```

The only peer is the project-owned loopback echo bridge:

```text
browser WebSocket 127.0.0.1:19201 -> TCP echo 127.0.0.1:19200
```

No original game binary, game packet, or server state participates in this
test.

## Result

The browser Wine 11 run completed connection and send, but the wait timed out:

```text
D3D9WEB_WINSOCK_FAIL step=wait result=0x00000102 error=0
D3D9WEB_WINSOCK_EXITCODE=7
```

`0x102` is `WSA_WAIT_TIMEOUT`. Since the test registers the event before it
sends the echo payload, this is direct evidence that the browser
`WSAEventSelect` readiness notification does not reach the Windows event.

## Consequence

This independently confirms the original-client boundary in document 169.
The remaining fix belongs in the BoxedWine/Wine event delivery path, not in
the renderer, original client, local game server, or gameplay logic. The
PatHouse launcher was restored to its normal project-owned D3D9Web package
after the test.
