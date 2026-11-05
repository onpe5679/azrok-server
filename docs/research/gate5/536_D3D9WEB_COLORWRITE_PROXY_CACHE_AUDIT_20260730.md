# 536 D3D9Web COLORWRITEENABLE 프록시 캐시 감사 (2026-07-30)

범위: 브라우저를 실행하지 않고 `tools/d3d9_web_backend/d3d9_web.cpp`와
`tools/boxedwine_local/web_backend/host/d3d9web-runtime.js`의 코드 본문만
교차 확인했다. 원본 실행파일과 게임 자산은 변경하지 않았다. #535의 브라우저
실측은 전부 VERIFIED 전제로 사용했다.

## 결론

### VERIFIED

1. 프록시에는 `D3DRS_COLORWRITEENABLE` 값 15를 0으로 바꾸는 패킷 변환이
   없다. 일반 경로는 `Device_SetRenderState`가 받은 `value`를 그대로
   `device->render_states[state]`와 `Command2.value2`에 저장한다
   (`d3d9_web.cpp:2351-2365`). 호스트 디스패처도 word1을 state, word2를
   value로 읽어 `applyRenderState`에 그대로 넘긴다
   (`d3d9web-runtime.js:3014-3017`).
2. 게스트 배치 경로도 패킷을 기록 순서대로 큐에 넣고
   (`d3d9_web.cpp:559-570`), fallback 재생도 `record=0..N-1` 순서로
   `SendCommandImmediate`를 호출한다 (`:573-591`). 이 경로에서 15→0 순서가
   뒤집히는 코드는 확인되지 않았다.
3. 정상 송신에서는 게스트 캐시를 송신 전에 갱신한다
   (`:2361-2365`). 송신/배치 flush가 실패하면
   `InvalidateDeviceHostStateCaches()`가 `render_state_set[]`를 전부 FALSE로
   만들어 다음 동일 값 호출의 dedup을 막는다 (`:622-648`, `:494-517`).
4. `Device_Reset`은 host-state cache invalidation 후 `COMMAND_INIT`을 보낸다
   (`:1246-1272`). `D3D9_CreateDevice`는 `g_device`를 `ByteZero`한 뒤 INIT을
   보낸다 (`:2226-2273`). 따라서 두 경로 모두 다음 `SetRenderState(168,15)`의
   `render_state_set[168]`는 FALSE이며, `render_states[168]`에 남아 있던 숫자
   15만으로 dedup될 수 없다. “Reset/재생성 후 15가 영구히 삼켜진다”는
   가설은 이 코드 조건만으로는 반증된다.

5. `Device_SetRenderState`의 일반 경로에는 `state==168`에 대한 특수 변환,
   clamp, bit mask, 또는 `15 -> 0` 대입이 없다. 함수 진입의 `value`가
   일반 경로를 통과하면 같은 값이 `device->render_states[168]`와
   `Command2`의 value word에 각각 기록된다. 따라서 확인된
   `SET_RENDER_STATE(168,15)`와 `(168,0)` 교대는 프록시가 두 값을 서로
   바꿨다는 정적 증거가 아니다.

6. 반대로 host `renderStates`는 runtime closure의 `Map`이며
   `COMMAND.INIT`에서 `clear()`되지 않는다. `Device_Reset` 또는 새
   `D3D9_CreateDevice`가 같은 host runtime에 도달하면 guest device와 host
   Map의 수명이 달라진다. stale Map이 0이면 `clearBackbuffer`가 매 clear
   뒤 all-false를 복원할 수 있다. 이 stale-state 결함 자체는 VERIFIED이나,
   이번 Enter 재현의 최초 `COMMAND.INIT`가 이 경로를 실제로 탔는지는
   브라우저 금지 조건에서는 NOT VERIFIED다.

## A. 캐시가 갈라지는 모든 확인 경로

| 경로 | 게스트 `device->render_states[]` | 호스트 `renderStates` | 판정 |
|---|---|---|---|
| 최초 CreateDevice | `ByteZero`; set flag FALSE | `new Map()` | VERIFIED, 일치하는 초기 기본값은 host의 `?? 0x0f` |
| 일반 SetRenderState | 성공 시 원값 저장 후 packet 송신 | `applyRenderState`가 원값 저장 | VERIFIED, 정상 송신이면 일치 |
| SetRenderState 중 bridge 실패 | 값은 먼저 저장되지만 set flag는 invalidation으로 FALSE | 실패한 packet은 적용되지 않음 | VERIFIED, 일시적 숫자 차이는 있으나 다음 호출 dedup은 차단 |
| StateBlock 기록 중 SetRenderState | block에만 원값 저장, device와 host에는 송신하지 않음 (`:2356-2359`) | 변화 없음 | VERIFIED, 기록 중에는 의도된 deferred path |
| StateBlock Capture | 표시된 키만 현재 `device->render_states[]`로 덮음 (`:2674-2683`) | 직접 변경 없음 | VERIFIED, block 값이 live cache 값으로 바뀔 수 있음 |
| StateBlock Apply | block 값을 `Device_SetRenderState`로 재적용 (`:2755-2788`) | packet을 받으면 변경 | VERIFIED, 현재 device cache와 같으면 dedup 가능 |
| Reset | set flag만 FALSE; 숫자 배열은 zero하지 않음 (`:1254`) | INIT가 Map을 지우지 않음 | VERIFIED, Reset 직후 host Map이 stale일 수 있음 |
| Device 재생성 | `g_device` 전체 zero | INIT가 기존 closure Map을 지우지 않음 | VERIFIED, 새 device와 stale host Map이 갈라질 수 있음 |
| Device Release | refcount만 감소; host INIT/Map 정리 없음 (`:1190-1201`) | 변경 없음 | VERIFIED, 실제 재생성까지 이어질 때 위 stale 경로와 결합 |
| COMMAND.INIT | 게스트 쪽은 Reset/Create에서 set flag를 초기화 | `viewport/scissor/renderer`만 갱신하고 `renderStates.clear()` 없음 (`d3d9web-runtime.js:2983-2990`) | VERIFIED, 확인된 실제 분기 |
| renderer 생성/캔버스 resize | 게스트 cache와 무관 | WebGL 기본 state가 재설정될 수 있으나 Map은 보존 | VERIFIED, GL state와 Map도 잠시 갈라질 수 있음 |

추가로 `Device_Reset`은 `render_state_set[]`만 FALSE로 만들고
`render_states[]`의 숫자 자체는 보존한다. 따라서 Reset 직후의
`StateBlock_Capture`가 이미 기록된 168을 캡처하면, 유효한 현재 상태가
아닌 Reset 이전의 숫자를 읽을 수 있다. 이는 `render_state_set[]`의 유효성
없이 Capture가 live 배열을 읽는 별도 stale-read 경로이며 VERIFIED(코드
경로), 실제 Plaza Enter 순서에서 사용됐는지는 NOT VERIFIED다.

호스트의 `applyRenderState`는 현재 168 case에서 즉시
`gl.colorMask(Boolean(value & 1), ...)`를 호출하고 Map에도 값을 저장한다
(`d3d9web-runtime.js:2105-2112`, `:2191-2201`). `clearBackbuffer`는 clear 후
Map의 168을 GL mask로 복원한다 (`:1877-1924`). 따라서 INIT 이후 stale Map이
0이면 clear가 all-false를 복원하는 것은 코드상 확정이다. 다만 이것은
`SetRenderState(168,15)`의 packet value를 0으로 바꾸는 증거가 아니다.

## dedup 가설의 정확한 범위

### VERIFIED

dedup은 다음 조건에서만 발생한다.

```cpp
device->render_state_set[state] && device->render_states[state] == value
```

따라서 현재 host가 0인데 게스트가 15를 실제로 호출했다면, 다음 둘이
동시에 관측되어야 한다.

- 호출 직전 `render_state_set[168] == TRUE` 및 `render_states[168] == 15`
- 그 호출에 대해 `Command2`가 생성되지 않음

Reset/CreateDevice 직후에는 첫 조건의 set flag가 FALSE이므로 이 경로의
영구 삼킴은 성립하지 않는다. 남는 정적 후보는 Reset/CreateDevice가 아닌
시점의 host Map/GL 재설정 또는 StateBlock 값 덮어쓰기이며, 현재 소스만으로
그 시점의 실제 호출 순서를 확정할 수 없다.

## B. CreateStateBlock 관여 여부

### VERIFIED

현재 vtable은 `g_device_vtable[60] = Device_BeginStateBlock`,
`[61] = Device_EndStateBlock`만 채우고, CreateStateBlock 슬롯은 채우지
않는다 (`d3d9_web.cpp:2885-2887`). 표준 D3D9 zero-based vtable에서
CreateStateBlock은 59이고, 이 소스의 60/61은 Begin/End와 일치한다. 사용자가
말한 “슬롯 60”은 이 소스의 Trace 번호(60)와 혼동하지 않도록 구분해야 한다.

#252에서 확인된 Plaza 경로는 EndStateBlock 108회와 Capture/Apply 호출을
실제로 사용했지만, CreateStateBlock 호출이 확인된 것은 아니다. 따라서
현재 `15→0` 문제의 직접 원인으로 CreateStateBlock 미구현을 지목할 근거는
없다. 호출되면 null vtable entry로 실패/크래시할 수 있는 별도 표면 결함이다.

### 구현안 (현재 미적용)

CreateStateBlock을 추가할 때는 `D3DSBT_ALL`, `D3DSBT_PIXELSTATE`,
`D3DSBT_VERTEXSTATE`에 따라 초기 block의 `*_set[]` 집합을 만들고, 현재
device live cache/resource를 복사한 뒤 `StateBlock_Capture`와 동일한
참조 보존 규칙을 적용해야 한다. 그 후 표준 슬롯 59에만
`Device_CreateStateBlock`을 연결해야 하며, Begin/End 슬롯을 이동시키면 안
된다. 이 작업은 현재 COLORWRITE 원인 확정 전에는 적용하지 않는다.

## C. 수정 및 빌드 판단

### VERIFIED

이번 감사에서는 `15→0`의 프록시 변환 근본 원인이 확정되지 않았으므로
`d3d9_web.cpp`와 host JS에는 수정하지 않았다. 이미 적용된 host `case 168`은
그대로 보존했다. 따라서 이번 조사로 새 DLL 재빌드는 필요하지 않다.

정적으로 확정된 최소 방어 수정 후보는 host `COMMAND.INIT`에서
`renderStates.clear()`를 호출하는 것이다. 이는 Reset/재생성 경계의 stale
Map을 제거하지만, 현재 증상의 Enter 경로가 그 경계를 거쳤다는 동적 증거가
없으므로 이번 감사에서는 적용하지 않았다. C++의 dedup을 168에 대해서만
무조건 해제하는 수정도 같은 이유로 적용하지 않는다. 실제 호출 상관관계
없이 증상을 가릴 수 있기 때문이다.

소스 수정이 확정될 경우 현재 패키지에 맞는 정적 빌드 명령은 다음이다.

```powershell
cmd /c tools\d3d9_web_backend\build.bat
```

guest-batch 패키지를 검증할 때는 다음을 사용한다.

```powershell
cmd /c tools\d3d9_web_backend\build_guest_batch.bat
```

브라우저 실행은 하지 않는다.

## D. 결론을 가르는 계측

### NOT VERIFIED (동적 확인 필요)

다음 단일 상관관계를 기록하면 StateBlock 문제, dedup, host INIT stale을
서로 분리할 수 있다. 모든 로그에는 하나의 monotonic sequence 번호와
`state=168`만 남겨 hot path 영향을 제한한다.

1. 게스트 `Device_SetRenderState` 진입 직전:
   `value`, `recording_block` 주소/유무, `device->render_state_set[168]`,
   `device->render_states[168]`를 기록한다.
2. 같은 함수에서 dedup 분기 직전과 packet 생성 직후를 기록한다:
   `DEDUP`이면 packet 없음, 아니면 raw `Command2 = {5,168,value}`를
   기록한다. 특히 entry value 15인데 packet value 0이 되는지 확인한다.
3. `Device_EndStateBlock`에서 block 주소와
   `block->render_state_set[168]`, `block->render_states[168]`를 기록한다.
4. `StateBlock_Capture`에서 168에 대해 overwrite 전후의
   `device->render_states[168]`와 block 값을 기록한다.
5. `StateBlock_Apply`에서 168을 `Device_SetRenderState`로 넘기기 직전
   block 값과, 그 직후의 `DEDUP/SEND` 결과를 기록한다.
6. `Device_Reset`, `D3D9_CreateDevice`에서 각각 guest cache의 168 값/set
   flag와 INIT 송신 시점을 기록한다.
7. host `COMMAND.INIT` 진입 시 `renderStates.has(168)`와 기존 값을 기록하고,
   `clearBackbuffer` 직전/직후에는 Map 168과 `gl.getParameter(gl.COLOR_WRITEMASK)`를
   기록한다.
8. host `COMMAND.SET_RENDER_STATE` raw packet에서 `word1`, `word2`, Map의
   이전/이후 168, `COLOR_WRITEMASK`를 한 행으로 기록한다.

판정표:

- `entry=15`, `packet=0`: 프록시 내부 호출/계측 오류이며 현재 코드 본문과
  모순되므로 재현 로그와 함께 우선 확인한다.
- `entry=15`, `DEDUP`, host Map=0: dedup/host stale 결합이 확정된다.
- `StateBlock_Capture after=0`, 이후 Apply=0: Capture가 0을 block에 주입한
  경로가 확정된다.
- packet이 처음부터 0이고 Capture/Apply가 관여하지 않음: 원본 guest 호출이
  0을 보낸 것이므로 이 프록시의 value 전달 문제는 반증된다.
- host INIT에서 Map=0이 유지되고 그 뒤 CLEAR가 all-false를 복원하지만
  packet 15가 존재함: INIT stale 결함은 확정되나, 15→0의 원인은 별도로
  추적해야 한다.

최종 정적 판정:

- REJECTED: C++ `Device_SetRenderState`가 받은 15를 0으로 바꿔
  `Command2`에 쓴다는 가설.
- REJECTED: Reset/Create 직후 첫 `SetRenderState(168,15)`가
  `render_state_set[168]` 때문에 영구 dedup된다는 가설.
- CONDITIONALLY POSSIBLE: host Map이 0으로 stale된 상태에서 live guest
  cache가 15인 동일값 Apply가 dedup되어 host에 재전송되지 않는 조합.
  이 경우에만 dedup이 갈라짐을 만들 수 있다.
- CONFIRMED BUG: `COMMAND.INIT`가 host Map을 초기화하지 않으며,
  `clearBackbuffer`가 그 stale 168을 GL mask로 복원한다.
- NOT VERIFIED: 위 조건부 조합 또는 Reset 후 Capture stale-read가 이번
  Enter 재현의 실제 원인이라는 점. 아래 계측 없이는 둘 중 하나로 닫지
  않는다.
