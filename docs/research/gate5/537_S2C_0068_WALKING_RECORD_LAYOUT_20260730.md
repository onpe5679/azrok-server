> **SUPERSEDED by 538.** `record[5]` 를 duration 으로 읽은 것이 틀렸다 —
> 서버 동기 시계 기준 **절대 도착 시각**이다. 그래서 이 카드의 수정은
> 텔레포트 회귀를 일으켰다. §2 의 필드 [0]~[4] 와 "heading 필드 없음" 결론은
> 유효하며 538 이 `vec_to_angle` 로 더 강하게 확인했다. §4 의 코드는 폐기됐다.
> (파일명 번호도 536 → 537 로 변경: 536 은 Codex 의 COLORWRITE 감사 카드와 충돌했다.)

# 537 S2C 0x0068 의 걷기 레코드 — heading 필드는 존재하지 않는다 (2026-07-30)

날짜: 2026-07-30
선행: **#533**(이 카드가 레코드 필드 해석을 뒤집는다), #529, #52
근거: `docs/research/_salvage/symbols/plaza_dump.txt` 디컴파일 + 2세션 실측
원본 실행파일·게임 자산 무수정.

---

## 1. 실측 관찰 (VERIFIED)

#533 의 서버측 보간을 넣은 뒤 사용자가 2세션에서 확인했다.

> "적어도 텔레포트하진 않는데 걷기 애니메이션이랑 각도는 따라서 안보여"

서버 계측도 일치한다 — 이동 1회에 `relay_tx` 가 **345** 까지 올라간다(50ms 간격 보간 프레임).
위치는 부드럽게 따라오는데 **걷기 모션과 방향이 없다.**

## 2. 레코드는 [id][현재][목표][duration] 이다 (VERIFIED — 디컴파일)

`0x00615D50` 이 0x18 바이트 단위로 레코드를 소비하며 **record[5] 로 두 경로를 가른다.**

```c
if (param_1[5] == 0) {                 // 배치 경로
    thunk_FUN_00526ec0();
    thunk_FUN_00527a40(1);             // actor+0x107 = 1
    thunk_FUN_00524da0(param_1[1], param_1[2]);   // x, y 만 전달
} else {                               // 걷기 경로
    thunk_FUN_00526ec0();
    thunk_FUN_00524eb0(param_1, 0);    // 레코드 전체 전달
}
```

`thunk_FUN_00527a40` 은 한 줄짜리 setter 다 — `*(this + 0x107) = param_2`.
배치 경로는 **1**, 걷기 경로 끝은 **2** 를 쓴다. 이것이 정지/걷기 애니메이션 상태다.

`thunk_FUN_00524eb0` 내부:

```c
this->0x11b = f(entity->0x10);      // 현재 x  (살아 있는 엔티티에서 읽는다)
this->0x11f = f(entity->0x14);      // 현재 y
... GetTickCount() 기반 시간차 iStack_50 계산 ...
this->0x123 = param_2[3];           // 레코드[3]
this->0x127 = param_2[4];           // 레코드[4]
thunk_FUN_00525050(param_2[5]);     // -> this->0x133
thunk_FUN_00525080(param_2[5], iStack_50);   // -> this->0x137, this->0x13b
thunk_FUN_00527a40(2);              // 상태 = 2 (걷기)
```

`thunk_FUN_00525050`·`thunk_FUN_00525080` 도 순수 setter 다.

### 결정적 교차 근거 — 0x69 핸들러

`thunk_FUN_005250c0`(opcode 0x69) 이 같은 슬롯을 쓰는데 **duration 을 명시적으로 다룬다.**

```c
*(this + 0x12B) = param_2[1];                 // x
*(this + 0x12F) = param_2[2];                 // y
if (param_2[3] != 0) *(this + 0x137) = param_2[3];    // <-- duration
if (param_3 == 0) { this->0x123 = this->0x12B; this->0x127 = this->0x12F; }
```

`0x123/0x127` 에 좌표가 들어가고 `0x137` 이 duration 이다.
따라서 0x0068 걷기 레코드의 필드는:

| dword | 의미 |
|---:|---|
| [0] | entity_id |
| [1] | **현재 x** |
| [2] | **현재 y** |
| [3] | **목표 x** |
| [4] | **목표 y** |
| [5] | **duration (ms). 0 이면 배치 경로** |

C2S `0x0066` 의 `<BiiiiiB>` = `cell, x1,y1, x2,y2, duration, pathflag` 와 **정확히 같은 모양**이다.

## 3. #533 의 필드 해석은 틀렸다 (VERIFIED)

#533 은 레코드를 `[entity_id][x][y][z][heading][mode_flag]` 로 읽고
C2S `0x0067` 의 angle 을 5번째 dword(index 4)에 실었다.
**그 자리는 실제로는 목표 Y 다.**

> **S2C 0x0068 에 heading 필드는 존재하지 않는다.**
> 클라이언트가 현재→목표 방향에서 스스로 각도를 낸다.
> 그래서 heading 을 아무리 채워도 렌더링된 각도가 바뀌지 않았던 것이다.

현재는 우리가 항상 `record[5] = 0` 을 보내므로 배치 경로만 타고,
그 경로는 `param_1[1]`, `param_1[2]` 만 넘기므로 index 3·4 는 **읽히지도 않는다** —
즉 잘못된 값이 실렸어도 무해했다. 다만 계약으로서는 틀렸다.

#533 의 나머지 결론(레코드 크기 0x18, 6 dword, `0x00613740 -> 0x00615D50` 라우팅,
C2S 디코더 형식)은 그대로 유효하다.

## 4. 수정 (적용됨)

`azrok_server.py`:

- `_build_state_0068_movement_record(entity_id, from_x, from_y, to_x, to_y, duration_ms)` 신설.
  필드 이름을 실제 의미대로 붙이고 위 디컴파일 근거를 주석으로 남겼다.
- `_plaza_relay_movement_intent()` 신설 — 기존 `visible_remote_actor_ids` 게이트와
  `_plaza_relay_lock` 을 그대로 쓰며 **패킷 1개**만 보낸다.
- `_start_plaza_movement_relay()` 가 duration > 0 이면 의도 중계로, 0 이면 기존 배치 경로로 간다.
- 50ms 보간 worker(`_plaza_movement_worker`)는 남겨 뒀다 — duration 0 경로와
  회귀 비교용. 기본 경로에서는 더 이상 호출되지 않는다.

부수 효과: 이동 1회당 릴레이 패킷이 **345 → 1**.

### 비브라우저 검증 (VERIFIED)

```text
py_compile azrok_server.py                    PASS
tools/test_server_room_mapping.py             OK
tools/test_content_builders.py                OK
tools/test_server_contract_layers.py          Ran 101 tests ... OK
```

### NOT VERIFIED

2세션 브라우저에서 걷기 모션과 방향이 실제로 표시되는지는 사용자 육안 확인이 필요하다.
`_ox_relay_position` 은 건드리지 않았다.
