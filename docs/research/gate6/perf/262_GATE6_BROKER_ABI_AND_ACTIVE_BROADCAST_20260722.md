# 262 — Gate 6 broker ABI 및 active broadcast 판정 (2026-07-22)

## 결론

- **VERIFIED:** Emscripten 6의 pthread 시작 메시지는 문자열 `run`이 아니라 숫자 `cmd=2`이며, 실행 중 worker는 `PThread.runningWorkers`가 아니라 `PThread.pthreads`에 들어간다. broker가 이 ABI를 인식하도록 수정한 `BrokerAbi` 빌드는 기준 PatHouse 렌더와 양방향 패킷을 유지했다.
- **VERIFIED:** Windows foreground를 측정 전·후 모두 `ChatGPT` PID 15032 / HWND `0x10A82`로 직접 확인한 15개 1초 표본에서 `BrokerAbi`는 평균 33.9333 FPS(30–38)였다. 문서 261의 동일 방식 official O3 32.7267 FPS보다 3.69% 높지만 표본 변동이 있으므로 큰 성능 돌파로 보지 않는다.
- **REJECTED:** 세 번째 grouped-module publication 뒤 같은 owner worker에 모듈을 1회 broadcast하는 후보는 동일 foreground 조건에서 평균 30.0733 FPS(26–33.3)였다. `BrokerAbi`보다 11.38% 느리므로 채택하지 않았다.
- **VERIFIED:** broadcast 세션의 서버 경로는 단일 WS/TCP 연결이었다. `S2C 0003(Data\\Space\\PatHouse),0007,0005,000A,000B` 뒤 클라이언트가 `C2S 0017,0017,0008`을 반환했고, 기준 카펫·벽·가구·캐릭터·한글 UI가 그대로 렌더됐다.
- **VERIFIED:** 성능 저하 후보의 broadcast 관련 소스와 make target은 제거했고, Emscripten 6 ABI 수정(`cmd=2`, numeric `cmd=9`, `PThread.pthreads`)은 유지했다.

## 동적 수치

| 빌드 | foreground 증거 | 15초 평균 FPS | 최소–최대 | 판정 |
|---|---|---:|---:|---|
| official O3 (문서 261) | 전·후 `0x10A82` | 32.7267 | 27.1–38.0 | 기준 |
| BrokerAbi | 전·후 `0x10A82` | 33.9333 | 30–38 | 유지 |
| BrokerBroadcast | 전 15:04:23.587, 후 15:05:07.837 모두 `0x10A82` | 30.0733 | 26–33.3 | REJECTED |

Broadcast 세션의 broker snapshot:

- `groupedLocalCompiles=18018`, `groupedBrokerHits=818`
- `duplicatePublications=8340`
- `activeBroadcastModules=662`, `activeBroadcastSent=780`, `activeBroadcastFailures=0`
- 응답한 두 worker의 집계에서는 `receivedCacheEntries=0`; 전체 45개 중 2개만 stats reply를 반환했으므로 이 0을 전체 worker의 절대값으로 확대하지 않는다.

## 정적 판정

- **VERIFIED:** guest CPU worker는 `platformThreadRun` 안에서 `cpu->run()`을 종료까지 계속 호출한다. 일반 `Worker.postMessage`의 `message` 이벤트는 JS event loop로 복귀해야 처리되므로, 실행 중 hot worker에 broadcast가 즉시 적용된다는 전제가 성립하지 않는다.
- **VERIFIED:** 기존 preload OOM 차단 owner도 broadcast 필터가 제외하지 않았고, byte cap/backpressure 없이 owner당 256개 모듈을 worker 수만큼 전송할 수 있었다.
- **VERIFIED:** `allocatedWorkers()`에는 unused pool도 포함되며 worker 반환 시 임시 owner key가 지워지지 않아 idle worker도 대상이 될 수 있었다.
- **VERIFIED:** 트리거는 고유 publisher 3개가 아니라 같은 module의 publication event 3회였다.

## 다음 단계

ABI 호환 수정은 유지하되 active broadcast는 폐기한다. 다음 성능 변경은 실행 중 CPU worker의 JS message-loop 복귀를 가정하지 않아야 하며, 실제 steady-state PatHouse frame time을 줄이는 경로만 foreground 전·후 HWND와 기준 렌더를 함께 기록해 판정한다.
