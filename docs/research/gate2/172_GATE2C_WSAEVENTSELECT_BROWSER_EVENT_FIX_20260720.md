> **SUPERSEDED by 173 for the combined FD_CONNECT + FD_READ path.**

# 172 — Gate 2c browser Winsock event delivery fix (2026-07-20)

## Scope

This is a bounded browser-network proof only. It does not launch Azrok content,
does not alter client packets, and does not manufacture a Windows event or a
server response.

## VERIFIED

### Failure before the change

The standalone Wine 11 `WSAEventSelect(FD_READ|FD_CLOSE)` smoke in 171 returned
success from `WSAEventSelect`, but `WSAWaitForMultipleEvents` timed out. A
separate direct receive smoke also timed out in browser execution.

The native WebSocket-to-TCP bridge was independently live: its log records the
accepted WebSocket, TCP connection, and byte-for-byte relay. Therefore the
missing edge was guest readiness delivery, not the echo payload.

### Runtime correction

The official Emscripten `multiThreaded` target moves emulation to workers. Its
`source/sdl/emscripten/mainloop.cpp` multi-thread branch omitted the existing
single-thread call to `checkWaitingNativeSockets(0)`. Consequently SOCKFS
readiness transitions could not wake BoxedWine's registered native socket
conditions while the guest ran on a worker.

The multi-thread branch now calls `checkWaitingNativeSockets(0)` after timers
on every browser main-loop iteration, guarded by
`BOXEDWINE_EMSCRIPTEN_SOCKETS`. The function polls real SOCKFS descriptors and
signals the existing condition objects only when the browser reports readiness.
It neither writes a packet nor sets a Wine event directly.

The official `multiThreaded` build was rebuilt with Emscripten 6.0.3 and served
from the supplied COOP/COEP Node server. The temporary cross-host Make support
allows `CC`/`CXX` override and `NO_DEPS=1` only because Windows-hosted emcc
emits backslash dependency paths that WSL GNU make cannot re-read.

### Direct byte-path proof

`winsock_recv_smoke.exe` initially targeted raw TCP `19200`; that is invalid
for browser SOCKFS because it must dial the project-owned WebSocket listener.
The test now targets `19201`, whose WebSocket bridge forwards to TCP `19200`.
The browser run produced:

```
D3D9WEB_SELECT select=1 select_error=0 bytes=25 error=0 match=1
D3D9WEB_WINSOCK_EXITCODE=0
```

This is an actual browser guest send and echoed receive, not an injected
response.

### WSAEventSelect proof

The original event smoke then ran unchanged against the same bridge. Its
browser output produced:

```
D3D9WEB_WINSOCK_EVENT_SELECT result=0 error=0
D3D9WEB_WINSOCK_RESULT connect=1 event_select=1 wait=1 enum=0x00000001 send=38 recv=38 match=1
D3D9WEB_WINSOCK_EXITCODE=0
```

`enum=0x00000001` is `FD_READ`. The event was observed through the normal
Wine `WSAWaitForMultipleEvents` / `WSAEnumNetworkEvents` route after a real
browser WebSocket relay and receive queue transition.

## Rejected paths

- Wine 11 `NtDeviceIoControlFile`/`NtFsControlFile` server forwarding for AFD
  event codes reached the Wine server but returned `WSAEOPNOTSUPP (10045)`.
  It is not the browser fix.
- The raw TCP port `19200` is not a valid browser SOCKFS target; use the
  WebSocket listener (`19201` for this bounded echo harness).

## Next

Run one bounded original-Azrok network startup with this runtime and a
WebSocket-to-TCP listener for the project server's configured port. The next
claim is only whether the original client advances through its existing
network wait; PatHouse remains the content-render upper bound.
