# 173 — Gate 2c WSAEventSelect connect promotion

**VERIFIED (browser, Wine 11 smoke):** the prior browser path still failed when an application requested `FD_CONNECT | FD_READ | FD_CLOSE` before a non-blocking connect. The project smoke received `FD_CONNECT` and the 30-byte echo payload, but the second Windows event wait timed out.

## Direct cause

**VERIFIED:** SOCKFS became writable while `KNativeSocketObject` still had `connecting=true` and `connected=false`. `KPoll` therefore injected synthetic `POLLHUP` beside the real `POLLOUT`; the Wine server completed FD_CONNECT but did not retain the read registration.

## Fix and proof

`checkWaitingNativeSockets()` now promotes the native object to connected and clears its error before waking the write condition. The same browser smoke now proves:

```
D3D9WEB_CONNECT_EVENT_CONNECT wait=0x00000000 enum=0 events=0x00000010
D3D9WEB_CONNECT_EVENT_READ    wait=0x00000000 enum=0 events=0x00000001
D3D9WEB_FD_CONNECT_EXITCODE=0
```

The trace also shows native read interest re-armed and then woken by the actual 30-byte WebSocket payload. No client packet or Wine binary was synthesized or patched.

**VERIFIED (original client smoke):** the normal Azrok browser launch now opens
the project WebSocket, consumes the 405-byte lobby response, and continues
receiving heartbeat payloads while the Wine server repeatedly modifies native
read/write interest. This is a bounded transport proof only; PatHouse content
render is not claimed here.

## Scope

This closes the standalone readiness blocker from 169/171. The next bounded check is one original-Azrok startup through the normal project bridge; content QA remains out of scope.
