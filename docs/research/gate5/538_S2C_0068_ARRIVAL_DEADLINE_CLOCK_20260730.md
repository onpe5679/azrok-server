# 538 S2C 0x0068 `record[5]` 는 duration 이 아니라 **서버 동기 시계 기준 절대 도착 시각**이다 (2026-07-30)

날짜: 2026-07-30
선행: **#537**(이 카드가 #537 의 핵심 주장을 뒤집는다), #533, #529
근거: `docs/research/_salvage/symbols/plaza_dump.txt` 디컴파일 5개 함수 + 2세션 실측
원본 실행파일·게임 자산 무수정. 클라이언트 패치 0.

---

## 0. 한 줄 요약

`record[5]` 에 **경과시간(ms)** 을 넣으면 클라이언트는 첫 프레임에서 곧바로
목적지로 스냅한다 — 이것이 "텔레포트만 하고 각도도 안 바뀌는" 증상의 전부다.
그 자리는 **`GetTickCount()` 를 서버 시계로 보정한 절대 시각**이어야 한다.

**C2S `0x0066` 의 여섯 번째 dword 는 상대 duration(ms) 이다** (실측 217, 795).
그러므로 변환은 서버 몫이다:

```
record[5] = (int(time.time()*1000) & 0xFFFFFFFF) + duration_ms
```

라이브 클라이언트에 직접 쏴서 **A/B 대조로 확정했다** (§4.1).

## 1. 실측 관찰 (VERIFIED)

| 시도 | 서버 동작 | 사용자 육안 |
|---|---|---|
| #533 | 50ms 보간 배치 프레임 (`record[5]=0`) | 텔포 없음, **걷기 모션 없음, 각도 없음** |
| #537 | `record[5] = duration_ms` 1회 | **텔포 부활**, 각도 여전히 없음 |

> "회귀했는데 텔포만 하고 각도도 반영 안됨"

## 2. 왜 그런지 — 이동 틱 함수 `FUN_0061A710` (VERIFIED — 디컴파일)

```c
now = (flag ? GetTickCount() + offset : GetTickCount() - offset);   // 서버 동기 시계
if (now < *(uint *)(actor + 0x137)) {              // <<<< 걷기 분기 전체의 게이트
    vec_diff(&dir, actor + 0x123, entity + 0x10);  // 목적지 - 현재
    vec_to_angle(entity + 0x1c, &dir);             // <<<< 각도는 여기서만 생긴다
    total   = *(int *)(actor + 0x137) - *(int *)(actor + 0x13b);
    elapsed = now                     - *(int *)(actor + 0x13b);
    step    = vec_length(dir) * elapsed / total;
    vec_normalize(&dir, step);  ...  vec_set(entity + 0x10, &pos);
} else {
    vec_set(entity + 0x10, actor + 0x123);         // 목적지로 즉시 스냅
    return 2;                                       // 이동 종료
}
```

세 가지가 한꺼번에 설명된다.

1. **`0x137` 은 절대 시각**이다. `now`(수백만~수십억)와 직접 크기 비교한다.
   `duration_ms`(수백~수천)를 넣으면 `now < 2500` 은 항상 거짓 → **else → 스냅 → 텔레포트.**
2. **각도는 걷기 분기 안에만 있다.** `vec_to_angle` 이 `entity+0x1c` 를 쓰는 게
   유일한 경로다. 그러니 텔레포트하면 각도도 영원히 안 붙는다.
   **두 증상은 별개가 아니라 같은 원인이다.**
3. **`0x13b`(출발 시각)은 클라이언트가 수신 시점에 스스로 찍는다**
   (`FUN_00524EB0` 의 `iStack_50`). 서버는 도착 시각만 주면 된다.

## 3. C2S 쪽은 duration 이다 — 정적 오독 정정 (VERIFIED — 실측)

처음에 나는 C2S 송신부 `FUN_005AB7B0`(22바이트를 opcode 0x66 으로 송신)의
호출자 `FUN_0061A420` 을 보고 여섯 번째 인자가 `actor+0x137`(절대 시각)이라
결론지었다.

```c
uVar8 = FUN_0061a6e0();                   // actor + 0x137
thunk_FUN_005ab7b0(cell, curX, curY, tgtX, tgtY, uVar8, 1);
```

**이 결론은 실측으로 반증됐다.** 라이브 2세션에서 클릭 이동 2회의 여섯 번째 dword 는
**217** 과 **795** 였다 — 절대 틱이 아니라 거리에 비례하는 **상대 duration(ms)**.

```text
eid=2 pos=4023,258  tick_c2s=217
eid=3 pos=4167,131  tick_c2s=795
server_now(32bit) = 2,985,667,541
```

오독의 원인: `FUN_005AB7B0` 의 호출자는 **셋**이다
(`FUN_0061BCF0`, `FUN_0061A420`, `FUN_0061B510`).
`FUN_0061A420` 의 그 블록은 `if (iVar2 == 1)` 안의 **셀 경계 통과 갱신** 경로이지
클릭 한 번이 타는 경로가 아니었다. 한 호출자만 보고 와이어 계약을 단정한 것이 잘못이다.

> **정리: C2S 는 duration, S2C `record[5]` 는 절대 시각. 대칭이 아니다.
> 변환이 서버의 일이다.**

## 4. 시계는 우리 서버 시계다 (VERIFIED — 디컴파일)

`0x137` 이 절대 시각이면 "누구의 시계냐"가 남는다. S2C `0x0004` 핸들러
`FUN_0059DE50` 이 답이다 — 페이로드는 우리가 이미 보내는 `<BI>` = kind + timestamp_ms.

```c
local_c = GetTickCount();
if (local_c < *(uint *)(param_1 + 1))                       // param_1+1 = 서버 timestamp
     { slot[n] = server_ts - local_c;  sign[n] = 1; }
else { slot[n] = local_c - server_ts;  sign[n] = 0; }
...
if (n < 5) { reply C2S 0x0016 payload=0x01; }               // 샘플 5개까지 스스로 요청
else {                                                       // 5개째에 확정
    obj->0x9a9 = sign[2];                                    // 중앙값 샘플의 부호
    obj->0x9a5 = slot[2];                                    // 중앙값 샘플의 오프셋
    *param_1 = 0xff;                                         // 0xFF 커밋 트리거
}
```

`0xFF` 는 `FUN_0050CBC0 case 4` 가 받아 게임 전역에 옮긴다.

```c
case 4:
  if (*param_3 == -1) {                       // payload[0] == 0xFF
      FUN_0050efe0(obj->0x9a5);               // -> 전역 + 0x35c0a (offset)
      FUN_0050f040(obj->0x9a9);               // -> 전역 + 0x35c0e (sign)
  }
```

`FUN_0061A710` 이 읽는 `offset`/`flag` 가 정확히 이 전역이다. 즉

> **클라이언트의 `now` = 우리 서버가 0x0004 에 실어 보낸 `int(time.time()*1000) & 0xFFFFFFFF`.**
> 캘리브레이션이 끝난 두 클라이언트는 **같은 시계**를 본다.
> 그래서 A 의 도착 시각을 B 에게 그대로 넘겨도 맞는다.

부수 확인: `0x0004` 5샘플 요청-응답 방식은 우리 서버가 이미 구현해 둔 것과 일치한다
(`_build_calibration_0004_sample`, `hansol_calibration_active`). **0xFF 종료 패킷을
서버가 따로 보낼 필요는 없다** — 클라이언트가 5번째 샘플에서 스스로 만든다.
라이브 2세션 모두 `calibration_samples=5` 로 관측됐다.

### 4.1 A/B 대조 실측 — 이게 결정적 근거다 (VERIFIED)

정적 근거만으로는 "클라이언트 `now` 가 정말 우리 시계인가"가 추론에 머문다.
그래서 **살아 있는 세션 B 에게 걷기 레코드를 직접 쏴서** 두 가설을 갈랐다
(`scratchpad/deadline_probe.ps1`). 액터 2 를 `4023,258 -> 4343,258` 로 이동시키고
0.9초 간격 스크린샷.

| 가설 | `record[5]` | 결과 |
|---|---|---|
| **H1** 우리 유닉스 ms | `now32 + 3000` = 2,986,173,972 | **걷는다.** t0/t1/t2 세 프레임 모두 **다른 중간 위치**, 게다가 카메라를 향하던 몸이 **진행 방향으로 돌아섰다** |
| **H2** 원시 GetTickCount | `3000` | 걷지 않는다. 스냅 |

> **H1 확정.** 캘리브레이션이 끝난 클라이언트의 `now` 는
> `int(time.time()*1000) & 0xFFFFFFFF` — **우리 서버 시계 그대로**다.
> 걷기 모션과 각도가 같은 분기에서 함께 나온다는 §2 의 예측도 이 한 번의 실측으로 확인됐다.

증거: `artifacts/audio/probe_H1_unixms_t0..t4.png`, `probe_H2_rawtick_t0..t4.png`

## 5. #537 정정 (VERIFIED)

#537 은 **S2C** 레코드를 `[id][현재x][현재y][목표x][목표y][duration]` 으로 읽었다.
**앞 다섯은 맞고 여섯 번째만 틀렸다** — S2C 쪽은 duration 이 아니라 절대 도착 시각이다.
(C2S 쪽은 #537 말대로 duration 이 맞다. 두 방향의 단위가 다른 것이 함정이었다.)

"heading 필드는 없고 클라이언트가 방향에서 각도를 낸다"는 #537 의 결론은 유효하며,
`vec_to_angle` 과 §4.1 실측으로 오히려 더 강하게 확인됐다.

#533 의 레코드 크기 0x18 / 6 dword / `0x00613740 -> 0x00615D50` 라우팅도 그대로 유효하다.

## 6. 수정 (적용됨)

`azrok_server.py`:

- `_build_state_0068_movement_record(..., arrival_tick)` — §2 디컴파일 전문을 주석으로.
- `_start_plaza_movement_relay` 가 **변환을 수행**한다:
  `arrival_tick = (server_now_ms + duration_ms) & 0xFFFFFFFF`.
  패킷은 이동 1회당 **1개** (`PLAZA_MOVEMENT_RELAY_MODE='intent'`, 기본값).
- duration 이 `0 < d <= 60000` 밖이면 걷기 레코드를 만들지 않는다
  (`movement_duration_rejects` 로 관측). 음수 duration 이 거대한 부호 없는
  deadline 으로 둔갑하는 것을 막는다 — `decode_c2s_0066` 이 이 dword 를
  `<i`(부호 있음)로 읽기 때문에 실재하는 위험이다.
- `movement_duration_ms`, `movement_duration_c2s`, `movement_arrival_tick` 을
  players API 로 노출.

`_plaza_movement_worker`(50ms 보간)는 남겨 뒀다 — `AZROK_PLAZA_MOVE_MODE=interpolate` 로
언제든 #533 동작으로 되돌릴 수 있다. `_ox_relay_position` 은 건드리지 않았다.

### 시행착오 기록 (왜 두 번 회귀했나)

1. **#533**: `record[5]=0` 고정 → 배치 분기만 탐 → 걷기·각도 없음.
2. **#537**: `record[5]=duration` → `now < 217` 거짓 → **텔레포트 부활**.
3. 첫 538 시도: C2S 값을 절대 시각으로 오독하고 그대로 중계 →
   페일세이프가 정상 작동해 걷기 레코드는 막았지만, **폴백을 배치 프레임 1개로**
   둔 탓에 화면상으로는 여전히 텔레포트. 폴백을 잘못 고르면 페일세이프도 회귀다.
4. 실측(§3, §4.1) 후 확정.

### 비브라우저 검증 (VERIFIED)

```text
py_compile azrok_server.py                       PASS
tools/test_server_room_mapping.py                Ran 7   OK
tools/test_content_builders.py                   Ran 14  OK
tools/test_server_contract_layers.py             Ran 106 OK
  PlazaMovementRelayContractTests (신규 5개)
    - 실측 duration 217 이 절대 deadline 으로 변환되고 와이어에 duration 이
      그대로 나가지 않는지 (`assertNotEqual(record[5], 217)`)
    - duration 0 이면 걷기 레코드 없이 배치
    - 상한 초과 duration 은 deadline 이 되지 않음
    - 음수 duration 이 wrap 되지 않음
    - visible_remote_actor_ids 게이트 유지
```

### 브라우저 실측 (VERIFIED — §4.1)

라이브 세션 B 에 걷기 레코드를 직접 주입해 **걷기 모션과 방향 전환을 눈으로 확인**했다.

### 최종 2세션 실측 (VERIFIED — 2026-07-30 17:15)

사용자가 양쪽 캐릭터를 직접 클릭 이동. **"어 잘된다"** — 걷기·방향 모두 정상.

```text
eid=2 pos=4104,271 relay_tx=42 dur_c2s=480 tick=2987878761 rejects=0 calib=5 vis=1
eid=3 pos=4090,152 relay_tx=16 dur_c2s=374 tick=2987886608 rejects=0 calib=5 vis=1
now32 = 2987903096
```

- `dur_c2s` 480·374 → **상대 duration 확정**(§3 과 일치)
- `tick` 이 `now32` 바로 아래 몇 초 → **절대 deadline 변환 정상**
- `rejects=0` → 페일세이프가 한 번도 걸리지 않음. 모든 이동이 걷기 레코드로 나감
- `relay_tx` 세션 전체 42·16 (이전에는 **이동 1회에 345**)

**#533 · #537 이 남긴 두 회귀는 이것으로 종결.**
