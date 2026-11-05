# 533 Gate 5 광장 액터 릴레이 heading 및 이동 보간 수정 (2026-07-30)

## 범위

- 수정 대상은 `azrok_server.py` 하나입니다.
- 클라이언트, `Azrok.exe`, 게임 자산은 수정하지 않았습니다.
- 브라우저 실행과 2세션 시각 검증은 수행하지 않았습니다. 해당 검증은 별도 주체의 범위입니다.
- `docs/research/gate5/INDEX.md`는 이 checkout에 존재하지 않았습니다. 프로젝트의 실제 조사 인덱스인 `docs/research/INDEX.md`에 533번을 등록했습니다.

## 원본 프로토콜 근거

### VERIFIED — b1 선택 근거

저장된 Ghidra 디컴파일 산출물 `docs/research/_salvage/symbols/plaza_dump.txt`에서 다음을 직접 확인했습니다.

1. `thunk_FUN_00613740`는 state-1 opcode `0x68`을 `thunk_FUN_00615d50`으로 전달합니다.
2. `thunk_FUN_00615d50`은 payload를 `0x18`바이트(6 dword) 단위로 반복하고, `param_1[5] == 0` 분기에서 `thunk_FUN_00524da0(param_1[1], param_1[2])`를 호출합니다. 이 수신 함수에는 C2S `0x0066`의 시작점·끝점·duration을 읽는 별도 필드가 없습니다.
3. 원본 클라이언트의 `thunk_FUN_0061b510`은 `GetTickCount()` 기반 시각값을 만들고 `thunk_FUN_005ab7b0`을 호출해 C2S `0x0066` 0x16바이트 payload를 전송합니다. 따라서 이 경로에서 duration은 밀리초 시간축으로 사용됩니다.
4. `thunk_FUN_005ab830`은 C2S `0x0067`을 0x0F바이트로 만들며 마지막 필드를 `u16`으로 기록합니다. 서버 decoder의 `<BiiIH>`와 일치합니다.

위 본문은 S2C `0x0068`에 이동 의도 전체를 전달하는 별도 b2 경로를 입증하지 않습니다. 0x0068 레코드 레이아웃을 변경하지 않고 원본 수신 경로가 실제로 적용하는 좌표를 시간에 따라 전달하려면 b1이 직접적인 선택입니다.

### VERIFIED — 레코드 레이아웃 보존

`azrok_server.py`의 `_build_state_0068_actor_position_record`는 기존 순서 그대로 `[entity_id][x][y][z][heading][mode_flag]`, 6 dword/0x18바이트를 유지합니다. 이번 수정은 heading 인자에 저장된 angle을 전달할 뿐 필드 순서·크기·mode_flag 의미를 변경하지 않습니다.

## 구현 결과

### VERIFIED — heading

- C2S `0x0067` 유효 패킷의 `angle`을 해당 액터 메타데이터 `heading`에 저장합니다.
- 이후 roster 초기 위치 및 Plaza의 모든 릴레이 `0x0068` 빌드가 해당 heading을 사용합니다.
- 도착 commit은 진행 중인 `0x0066` 보간 worker를 generation 증가로 취소하고, 저장된 heading을 담은 최종 `0x0068`을 보냅니다.

### VERIFIED — b1 이동 보간

- C2S `0x0066`의 시작점·끝점·duration을 보존합니다.
- 시작점 프레임을 즉시 1회 전송하고, duration(ms) 동안 50ms 간격으로 선형 보간한 좌표를 기존 S2C `0x0068` 레코드로 전송합니다.
- 새 이동이나 도착 commit이 이전 worker의 generation과 달라지면 이전 worker는 중단합니다.
- 각 프레임마다 기존 `visible_remote_actor_ids`를 다시 확인합니다. 가시성 게이팅을 우회하지 않습니다.
- `_ox_relay_position` 및 OX 분기는 수정하지 않았습니다.

## 비브라우저 검증

### VERIFIED — 기존 테스트

- `tools/emsdk/python/3.13.3_64bit/python.exe -m py_compile azrok_server.py` — PASS
- `tools/test_server_room_mapping.py` — 7 PASS
- `tools/test_content_builders.py` — 14 PASS
- `tools/test_server_contract_layers.py` — 101 PASS

### VERIFIED — 인메모리 릴레이 재현

브라우저나 클라이언트를 실행하지 않고 두 가상 connection과 `_emit` 캡처를 사용했습니다.

- C2S `0x0066 = <BiiiiiB>(21, 0, 0, 300, 0, 120, 0)` 입력
- S2C `0x0068` 좌표: `0 -> 100 -> 200 -> 300` (4 frames)
- 이후 C2S `0x0067 = <BiiIH>(21, 300, 0, 7, 0x1234)` 입력
- 메타데이터 `heading == 0x1234`
- 최종 S2C `0x0068` heading dword `== 0x1234`
- 출력: `plaza_relay_flow: PASS`, `frames_0068=4 start=0 end=300 heading_final=0x1234`

## 검증 경계

### NOT VERIFIED

- 실제 브라우저 2세션에서 상대 캐릭터가 보간 프레임을 걷기 애니메이션으로 표시하는지는 이 작업에서 확인하지 않았습니다.
- 원본 클라이언트의 `0x0068` `mode_flag != 0` 분기(`thunk_FUN_00524eb0`)가 어떤 추가 애니메이션 의미를 갖는지는 기존 레코드 필드만으로 완전히 확정하지 않았습니다. 그러므로 이번 수정은 해당 미확정 분기를 사용하지 않고, 디컴파일로 직접 확인된 좌표 적용 분기와 반복 `0x0068` 전송만 사용합니다.

### INFERRED

- 원격 클라이언트가 짧은 간격의 좌표 갱신을 걷기처럼 시각화한다는 점은 클라이언트의 실제 2세션 표시 결과가 필요합니다. 서버 측에서는 원본 S2C `0x0068` 좌표 적용 경로에 맞는 시간 순서의 프레임이 실제로 전송되는 것까지만 확인했습니다.
