# 169 Gate 2c `WSAEventSelect` read-rearm boundary (2026-07-19)

## Scope

브라우저 BoxedWine의 원본 `Azrok.exe`에서 로그인 뒤 서버 응답이 게임의 inbound ring에 들어오지
않는 현상을, 콘텐츠 진행 없이 receive thread와 BoxedWine socket poll 경계까지만 측정했다.

## Result

| Boundary | Result | Evidence |
|---|---|---|
| browser guest receive thread start | **VERIFIED** | `Azrok.exe!0x0061E7E0` 표식 도달 |
| `WSAEventSelect` | **VERIFIED success** | `0x0061E83D`, `EAX=0` |
| Wine server poll loop | **VERIFIED alive** | `tid=15`의 `internal_poll(... timeout=16)`가 240회 연속 실행 |
| socket `FD_READ` re-arm | **NOT OBSERVED** | `WSAEventSelect` 뒤 `KTYPE_NATIVE_SOCKET` poll 항목 0건 |
| `WSAWaitForMultipleEvents` return / `WSAEnumNetworkEvents` / `recv` | **NOT OBSERVED** | 각각의 재배치 EIP 표식 및 `recvmsg` trace 0건 |

## 1. Direct receive-thread trace

**VERIFIED (browser dynamic).** 아래 정적 주소는 `Azrok.exe` receive thread
`FUN_0061E7E0`의 직접 명령 경계다.

```text
0061E7E0 RECV_THREAD_ENTER
0061E83D return from WSAEventSelect(socket,event,FD_READ|FD_CLOSE)
0061E855 return from WSAWaitForMultipleEvents
0061E869 WSAEnumNetworkEvents
0061E8AD recv call
```

실행에서는 다음 두 표식만 나왔다.

```text
D3D9WEB_TARGET name=RECV_THREAD_ENTER eip=0061E7E0 ...
D3D9WEB_TARGET name=EVENT_SELECT_RETURN eip=0061E83D eax=00000000 ...
```

따라서 `WSAEventSelect`의 호출 자체와 성공 반환은 직접 확인됐다. 그 뒤 wait-return,
event-enumeration, recv 표식은 없었다.

### Ghidra MCP static cross-check

**VERIFIED (Ghidra MCP, `Azrok_analyzed.exe`).** 재기동한 Ghidra MCP HTTP endpoint에서
`/decompile_function?address=0x0061E7E0`와
`/disassemble_function?address=0x0061E7E0`를 다시 조회했다. 실제 루프는 다음 조건이다.

```c
WSAEventSelect(socket, read_event, 0x21); // FD_READ | FD_CLOSE
do {
    result = WSAWaitForMultipleEvents(2, events, FALSE, INFINITE, FALSE);
    if (result != 0) break;
    WSAEnumNetworkEvents(socket, read_event, events_out);
    if (events_out[0] & FD_READ) recv(socket, buffer, 0x2000, 0);
} while (!(events_out[0] & FD_CLOSE));
```

즉 dynamic trace의 `EVENT_SELECT_RETURN` 뒤 `WAIT_RETURN`가 없는 것은 receive thread가
정상적으로 `WSAWaitForMultipleEvents(INFINITE)`에 블록되어 있다는 직접 해석과 일치한다.
이 단계에서는 game main loop나 protocol handler가 수신을 버린 것이 아니다.

## 2. Scheduler is not the stop point

**VERIFIED (browser dynamic).** `kpoll.cpp::internal_poll`에 bounded trace를 넣은 결과,
Wine server thread `tid=15`는 event-select 이후에도 16ms timeout으로 poll loop를 계속 실행했다.

```text
D3D9WEB_INTERNAL_POLL n=202 tid=15 count=10 timeout=16
...
D3D9WEB_INTERNAL_POLL n=240 tid=15 count=10 timeout=16
```

따라서 "Wine server thread가 멈춰서 FD_READ를 못 받는다"는 가설은 배제된다.

## 3. Native socket observation is missing after event-select

**VERIFIED (browser dynamic).** trace 전체에서 native socket guest poll은 connect 시점의
한 항목뿐이었다.

```text
D3D9WEB_GUEST_POLL n=1 tid=15 guestfd=123 events=4 timeout=16
```

`events=4`는 연결 완료의 write readiness 관측이며, `POLLIN`은 아니다. Event-select 성공 뒤에는
`D3D9WEB_GUEST_POLL`, `D3D9WEB_SOCKET_POLL`, `D3D9WEB_READ_READY`, `D3D9WEB_RECVMSG`가
추가로 관측되지 않았다.

BoxedWine Emscripten main loop는 `checkWaitingNativeSockets(0)`를 매 slice 호출하지만,
해당 함수는 `waitingNativeSockets`가 비어 있으면 즉시 return한다. `KNativeSocketObject`는
`waitForEvents(..., K_POLLIN)`에서만 자신을 그 집합에 넣는다. 현재 직접 증거는
`WSAEventSelect` 뒤 실제 Wine poll 항목에서 native socket이 사라졌다는 것까지다.

## 4. Full poll-set result

**VERIFIED (browser dynamic, post-reboot `eipsample13`).** The bounded full
descriptor dump is now complete. After `WSAEventSelect` succeeds, each sampled
`count=10` poll contains only `KTYPE_UNIX_SOCKET` (`type=1`) descriptors with
`POLLIN` (`events=1`):

```text
D3D9WEB_POLL_SET sample=1  tid=15 fd=16 type=1 events=1
...
D3D9WEB_POLL_SET sample=10 tid=15 fd=14 type=1 events=1
```

The three repeated 10-entry samples contain no `KTYPE_NATIVE_SOCKET` (`type=2`)
entry. The only native entry in the whole run remains the earlier connect
`POLLOUT` observation:

```text
D3D9WEB_GUEST_POLL n=1 tid=15 guestfd=123 events=4 timeout=16
```

The local preservation server simultaneously accepted the connection, received
the login and repeated heartbeats, and sent its paced lobby payload. Therefore
the server/bridge has delivered outbound data, but the Wine-side `WSAEventSelect`
path does not add the corresponding native socket to the waiting set. This
rules out the alternative that a native socket was present and Emscripten
`poll()` merely failed to report `POLLIN` for it.

**Next direct measurement:** instrument the native-socket and Wine Unix-socket
event registration boundary to identify which Wine-side reselect operation
omits the native descriptor. Do not inject S2C data or patch the original
client.

### Native registration boundary result

**VERIFIED (browser dynamic, `eipsample14`).** The registration-boundary trace
shows precisely two calls for the active TCP object (`nativefd=43`):

```text
D3D9WEB_NATIVE_WAIT n=1 ... nativefd=43 ... events=C
D3D9WEB_NATIVE_WAIT n=2 ... nativefd=43 ... events=0
```

`0xC` is the connect-time write/error registration. The immediately following
zero removes it. There is no later `KNativeSocketObject::waitForEvents` call,
and no direct `isReadReady` trace, after `WSAEventSelect` returns success.
Thus the missing descriptor is not removed by `kpoll` cleanup: Wine's
WSA-event-select implementation never requests native read monitoring in this
BoxedWine/Emscripten execution path.

## 5. Superseded next-measurement hypothesis

**NOT VERIFIED.** `count=10` Wine server poll을 구성하는 모든 guest descriptor의
`fd/type/events`를 bounded dump하도록 diagnostic WASM을 확장했다. 이 측정은 다음 둘을
직접 가른다.

1. native socket 자체가 Wine의 AFD event-select reselect 단계에서 poll set에 들어가지 않음
2. native socket은 들어가나 BoxedWine/emscripten poll readiness가 event queue transition을 알리지 않음

브라우저 재기동 후 이 한 번의 dump가 나오기 전에는 forced S2C injection, client binary patch,
또는 임의의 socket wakeup workaround를 적용하지 않는다.

## Files

- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/source/kernel/kpoll.cpp`
- `artifacts/boxedwine/20260719_gate2b_native/Boxedwine/source/kernel/knativesocket.cpp`
- `tools/boxedwine_local/index_d3d9web_pathouse.html`
- `artifacts/web_backend/20260719_postreboot*/`

## 6. Browser delivery is present; the missing link is Wine event notification

**VERIFIED (browser dynamic, post-reboot `eipsample17`).** The page-level
WebSocket observer received the bridge's binary frames (`D3D9WEB_WS_MESSAGE 5`),
and the active BoxedWine native socket then reported the same queue as readable:

```text
D3D9WEB_READ_READY fd=43 poll=1 revents=1 result=1
```

The condition persists because the Wine receiver thread never reaches its
post-wait `recv`; the SockFS queue is therefore not drained. This corrects the
earlier narrower wording in sections 3/4: Emscripten SOCKFS *does* report
`POLLIN` once data is queued. What remains missing is the propagation of that
readiness into the Windows event created by Wine's `WSAEventSelect`, so the
blocked `WSAWaitForMultipleEvents(INFINITE)` never returns. The local bridge
and server are excluded: browser delivery, native readiness, C2S heartbeats,
and S2C replies all occur in the same live run.

**NOT VERIFIED:** the exact Wine 11 event-registration function that should
set the Windows event. Next work is static/dynamic correlation of that Wine
function and the BoxedWine event-object wakeup path. Do not add a client-side
packet workaround or broaden game-content testing.

## 7. Wine 1.7.55 server-side contract

**VERIFIED (Wine 1.7.55 source matching the mounted `fullWine1.7.55-v8.zip`,
plus browser trace).** `dlls/ws2_32/socket.c::WSAEventSelect` sends the
`set_socket_event` request to wineserver. `server/sock.c::set_socket_event`
stores the supplied Windows event and calls `sock_reselect()`. For `FD_READ`,
`sock_reselect()` obtains `POLLIN` from `sock_get_poll_events()` and calls
`set_fd_events(sock->fd, POLLIN)`. On a native readiness notification,
`sock_poll_event()` marks `FD_READ` pending and `sock_wake_up()` invokes
`set_event(sock->event)`.

The direct browser trace has the first and last observable application-side
facts: successful `WSAEventSelect` and a permanently blocked wait, while the
same native fd has SockFS `POLLIN`. Therefore the corrective target is not the
Azrok receiver or its server protocol: it is the BoxedWine representation of
the Wine-server `set_fd_events(..., POLLIN)` registration or its subsequent
event dispatch after an AF_INET descriptor crosses the Wine Unix control
channel. This is the next static/dynamic boundary to instrument.
