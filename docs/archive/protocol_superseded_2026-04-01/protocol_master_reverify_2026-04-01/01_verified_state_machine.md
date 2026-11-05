# Azrok Verified State Machine

Date: 2026-04-01
Scope: binary re-verification, live packet-log re-check, direct Ghidra MCP HTTP endpoint verification

## 1. 검증에 사용한 근거

- Ghidra MCP decompilation
- current live capture: [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt)
- direct HTTP endpoint checks against `http://127.0.0.1:8089`
  - `/mcp/schema`
  - `/get_function_by_address`
  - `/get_xrefs_to`

## 2. 최상위 inbound state machine

Primary dispatcher:

- `DispatchInbound_ByClientMode @ 0x00594310`

확정된 동작:

- 모든 inbound packet을 먼저 기록한다
- `0x0005`는 mode dispatch 전에 먼저 `HandleS2C_0005_PostLoadState`를 탄다
- `0x0064`는 mode dispatch 전에 `FUN_00594100(1)`로 `dispatch_state = 1`을 강제로 세운다
- `dispatch_state == 0`
  - `DispatchState0Specific_S2C @ 0x0059DD20`
  - 이후 `DispatchState0Common_S2C @ 0x0050CBC0`
- `dispatch_state == 1`
  - `DispatchState1_S2C @ 0x00613740`

결론:

- `S->C 0x0064`는 단순 self spawn packet이 아니다
- **state-0 -> state-1 경계 packet**이다
- 초반에 보내면 남아 있던 state-0 후처리를 끊는다

## 3. login -> lobby/pet -> PatHouse 흐름

### 3.1 `S->C 0x0000`

핸들러:

- `HandleS2C_0000_LoadLobbySparseCache @ 0x0059E070`
- `HandleS2C_0000_SelectLobbyEntryScene @ 0x0050D0E0`
- `Lobby_CopyBootstrapBlob_0183 @ 0x0050D1C0`

확정된 구조:

- total blob length `0x183`
- `+0x00 = result_code`
- `+0x01 = lobby_mode`
- `+0x56 = sparse_count`
- `+0x57 = sparse key array`
- `+0xBB = sparse value array`

분기:

- `result_code == 0 && lobby_mode == 0`
  - room code `0x6C`
  - `lobby.wmb`
  - scene mode `1`
- `result_code == 0 && lobby_mode != 0`
  - room code `0x6B`
  - `pet.wmb`
  - scene mode `0`

즉 login은 곧바로 PatHouse로 가지 않고, 먼저 login shell 단계로 들어간다.

### 3.2 `S->C 0x0003 + 0x0007`

핸들러:

- `HandleS2C_0003_StoreSpacePath @ 0x0050D200`
- `HandleS2C_0007_LoadSetupBlob @ 0x0059E330`
- `HandleS2C_0007_EmitPostSetupStateRequest @ 0x0050D290`

확정된 의미:

- `0x0003`
  - `payload[0] -> gm+0x31C63`
  - `payload[1:] -> path/root string`
- `0x0007`
  - setup blob import
  - stat/selectors/runtime-row import
  - common path에서 다음 room code를 enqueue

중요 교정:

- `0x0007` default common path는 room code `0`이 아니라 **default room enqueue**
- 재검증 결과 이 default path는 `100`으로 이어진다

### 3.3 room bootstrap

`GameManager_DispatchRoomCode @ 0x0050A0F0`

핵심 case:

- code `0`
  - `room.wmb`
  - 이후 code `100` push
- code `100`
  - `GameManager_ExecuteRoomInit(100)`
  - PatHouse room init
  - scene mode `2`

결론:

```text
login shell
-> 0x0003
-> 0x0007
-> default room enqueue
-> room.wmb
-> room init 100
-> scene mode 2
```

## 4. `0x0002`는 초기 bootstrap에서 금지

핸들러:

- `HandleS2C_0002_TransitionPrimary @ 0x0059D150`
- `DispatchState0Common_S2C case 2 @ 0x0050CBC0`
- `GameManager_PerFrameUpdate @ 0x00509200`

확정된 사실:

- common handler가 `gm+0x31946 = 0`
- per-frame room dispatch는 `gm+0x31946 != 0`일 때만 진행
- `HandleS2C_0002_TransitionPrimary`는 client-side `C->S 0x0007`도 다시 발생시킨다

결론:

- 초기 login/PatHouse flow에서 `S->C 0x0002`는 넣으면 안 된다

## 5. `0x0004`는 두 의미가 섞인 packet이다

핸들러:

- `DispatchState0Specific_S2C @ 0x0059DD20`
- `HandleS2C_0004_CalibrationSample @ 0x0059DE50`
- `DispatchState0Common_S2C case 4 @ 0x0050CBC0`

확정된 동작:

- specific dispatcher는 `payload[0] == 0x01`일 때만 calibration sample 처리
- 5개 sample 누적
- 5번째 처리에서 same receive buffer를 `0xFF`로 변경
- common dispatcher는 그 `0xFF`를 보고 readiness latch(`gm+0x31C71`)를 세운다

결론:

- packet-faithful calibration은 `0x01 + timestamp` x5다
- 예전의 `0x00 + timestamp` 해석은 binary와 맞지 않는다

단, 현재 live log 기준으로는:

- `S->C 0x0004`가 모두 `0x00`
- 그래도 PatHouse bootstrap은 진행됨

따라서:

- `0x0004`는 **PatHouse 최초 진입의 하드 게이트는 아님**
- 대신 Hansol/Plaza readiness에 더 중요하다

## 6. Hansol / Plaza 쪽에서 확정된 것

핸들러:

- `Plaza_TransitionFromRoom @ 0x00568770`
- `Hansol_SceneStageHandler @ 0x00614370`

확정된 사실:

- `Plaza_TransitionFromRoom`
  - room code `0x6E` enqueue
  - Hansol flag(`gm+0x31C72`) set
  - calibration accumulator reset
- `GameManager_DispatchRoomCode case 0x0B`
  - `gm+0x31C71 != 0`일 때만 `hansol.wmb`
- `Hansol_SceneStageHandler` stage 0
  - `SendC2S_0064_LocalBootstrapStatus` 호출

HTTP xref 검증:

- `/get_xrefs_to?address=0x004E113B&program=Azrok.exe`
  - `From 006143ec in Hansol_SceneStageHandler`

결론:

- `C->S 0x0064`는 Hansol/state-1 계열의 **늦은 stage**에서 나가는 쪽이 맞다
- 최소 PatHouse bootstrap의 필수 packet이 아니다

## 7. 현재 live session이 실제로 보여준 C->S

현재 capture에서 실제로 본 것은 아래뿐이다.

- `0x0000` x1
- `0x0016` x40
- `0x0007` x3
- `0x000C` x3

즉 이번 세션 기준으로는:

- `0x0001`
- `0x0008`
- `0x0017`
- `0x0019`
- `0x0064`

이 다섯 개는 **미관측**이다.

## 8. 이 문서의 최종 결론

1. 최소 PatHouse packet-only 진입 축은 state-0 중심이다
2. `0x0002`와 early `0x0064`는 배제해야 한다
3. `0x0004`는 binary-faithful target에서는 중요하지만, 현재 live PatHouse 진입의 하드 게이트는 아니다
4. 지금 가장 중요한 미해결 gameplay contract는 `C->S 0x000C`다
