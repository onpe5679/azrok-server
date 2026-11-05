# State-1 전환 흐름 + 0x0064 분석

> **Note:** This document was written during investigation. 0x0064 is currently NOT sent by the server — the natural FUN_0050B400(100) bootstrap path handles room entry without it.

## 1. S->C 0x0064 핸들러: HandleS2C_0064_ApplyAuthoritativeSelf

### 진입 조건

```
if ((*param_1 == 0x00) || (*param_1 == 0x0A) || (*param_1 == 0x0B) || (*param_1 == 0x14))
```

entry byte가 이 네 값 중 하나가 아니면 핸들러 전체를 스킵한다.

### Entry Byte 의미

| 값 | 의미 | 추가 동작 |
|----|------|-----------|
| `0x00` | 기본 진입 (일반 월드) | appearance/time 설정만. 추가 scene 분기 없음 |
| `0x0A` | Plaza 씬 진입 | `player+0x107 = 0x2E`, weather/환경 초기화 5종, `player+0x324=1, +0x325=0` |
| `0x0B` | Plaza 씬 진입 (variant) | `player+0x107 = 0x2F`, 동일 환경 초기화, `player+0x324=1, +0x325=1` |
| `0x14` | 기본 진입 (0x00과 동일 경로) | 0x00과 동일 |

**현재 서버**: `entry_mode=0x00` 사용 중 - Plaza 씬 분기를 타지 않음.

### 페이로드 레이아웃 (Ghidra 디컴파일 검증)

> **이전 분석의 오류 수정**: 구 문서는 `+0x01` actor_id(u32), `+0x06` x, `+0x0A` y로 기록했으나
> Ghidra 디컴파일로 확인한 실제 레이아웃은 아래와 같다.

| 오프셋 | 크기 | 필드 | 용도 |
|--------|------|------|------|
| `+0x00` | 1 | entry_kind (u8) | 씬 타입 선택 (0x00/0x0A/0x0B/0x14) |
| `+0x01` | 1 | selector_0 (u8) | 보조 선택자 |
| `+0x02` | 1 | selector_1 (u8) | 보조 선택자 |
| `+0x03` | 4 | self_id (u32) | `player+0x2F8`에 저장. self actor id |
| `+0x07` | 4 | pos_x_raw (u32) | `FUN_004EDDE0`로 변환 후 `entity+0x10` |
| `+0x0B` | 4 | pos_y_raw (u32) | `FUN_004EDDE0`로 변환 후 `entity+0x14` |
| `+0x0F` | 4 | tail_dword (u32) | 후미 필드 |
| `+0x13` | 1 | room_domain (u8) | 값 < 0x1E이면 `FUN_0060B880(0)` (리셋 게이트 트리거) |
| `+0x18` | 3 | field_0x18 (3 bytes) | 용도 미상 |

> **미확인 필드**: 구 분석에서 `+0x12` appearance_a/b, `+0x14` year(u16), `+0x16` month, `+0x17` day,
> `+0x18` hour, `+0x19` minute, `+0x1A` second로 기록된 필드들은 Ghidra 검증 레이아웃과
> 오프셋이 충돌하므로 재검증 필요. 아래 처리 흐름의 `payload[0x12]`, `payload[0x14..0x1A]` 참조는
> 구 분석 기준이며 실제 오프셋과 다를 수 있다.

### 처리 흐름

1. **appearance 저장**: `FUN_006108F0(0, payload[0x12])`, `FUN_006108F0(1, payload[0x13])`
2. **self actor id 설정**: `FUN_00615AF0(actor_id)` -> `player+0x2F8 = actor_id`
3. **시간 오프셋 계산**: `GetTickCount()` -> `FUN_00524CF0` -> `player+0xFF = tickcount +/- base`
4. **entity 생성**: vtable call `(**(piVar3+8))()` -> 새 entity 할당 -> `local_c`
5. **좌표 설정**: `entity+0x10 = FUN_004EDDE0(x)`, `entity+0x14 = FUN_004EDDE0(y)`, `entity+0x1C = FUN_004EDDE0(0)`
6. **terrain snap**: `FUN_0061B370`으로 지형 높이 보정
7. **entity 플래그**: `entity+0x34 = 0xAE0200`
8. **위치 배치**: `FUN_00523620` - 랜덤 오프셋으로 entity 배치
9. **시간 설정**: `FUN_0050EE80(payload[0x14..0x1A])`
10. **time-of-day**: `payload[0x1A] < 0x1E`이면 `FUN_0060B880(0)` (100→day, else→night 분기)
11. **카메라/환경**: `FUN_005B61F0`, `FUN_00614D40` -> `FUN_0060AD00`
12. **entry_mode 분기**: 0x0A/0x0B일 때 Plaza 전용 초기화 (아래 상세)
13. **지형 충돌 검사**: `FUN_0061ACB0` - 실패 시 fallback 좌표로 재배치 + `FUN_00619900(entity, 2, 0)`
14. **최종 호출**: `FUN_0050A840()` - 로딩 완료 시그널

### 0x0A/0x0B 분기 상세

entry byte가 `0x0A`일 때:
```
player+0x107 = 0x2E    (Plaza scene code)
FUN_00600970(0)        (weather reset)
FUN_005FFBC0(0)        (env param 1)
FUN_005FFBF0(0)        (env param 2)
FUN_005FFC50(0)        (env param 3)
player+0x324 = 1       (active flag)
player+0x325 = 0       (variant = 0)
```

entry byte가 `0x0B`일 때:
```
player+0x107 = 0x2F    (Plaza scene code variant)
(동일 환경 초기화 5종)
player+0x324 = 1
player+0x325 = 1       (variant = 1)
```

### 핵심 발견: `FUN_0050A840`

```c
void FUN_0050a840(void) {
    FUN_005CA8B0();  // engine frame advance
}
```

이 함수가 0x0064 핸들러의 맨 마지막에 호출된다. 로딩-클로즈 경로의 시작점이며,
이 호출이 도달해야 로딩 화면 종료가 시작된다.

---

## 2. SendC2S_0064_LocalBootstrapStatus (Local Bootstrap)

### 역할

로컬 self 플레이어 싱글톤을 생성하는 네이티브 부트스트랩 함수.

### 처리 흐름

1. **임시 ID**: `local_27 = GetTickCount()` (나중에 0x0064의 authoritative id로 교체됨)
2. **species 읽기**: `local_23 = FUN_00545500()` (manager `+300`에서 읽음, 원래 `0x0007 byte1`)
3. **subtype 읽기**: `local_22 = FUN_005465C0()` (manager `+0x130`에서 읽음, 원래 `0x0007 byte2`)
4. **이름 복사**: `FUN_005286E0()` -> 13바이트 이름 버퍼
5. **슬롯 값 읽기**: `FUN_005AB2B0(0..3)` -> `local_14..local_11` (원래 `0x0007 +0x1D4..+0x1D7`)
6. **struct 조립**: `local_28` = `[0, tickcount(4), species(1), subtype(1), name(13), ...slots(4)]`
7. **핵심 초기화**: `FUN_00524280(struct, 1)` -> self 싱글톤 필드 설정
8. **기존 entity 확인**: `FUN_005270D0()` -> 이름으로 기존 entity 검색
9. **entity 미존재 시**:
   - `FUN_00525A60(1, 0)` -> 3D 모델 생성 + `player+0x99 = entity`, `player+0x31A = 1`
   - `FUN_005247F0(1)` -> `player+0x31A = 1` (ready flag)
   - `FUN_00521E90(slot, value, 0)` x4 -> 장비/아이템 슬롯 설정
10. **후처리**: `FUN_0050F0A0`, flags 설정, `FUN_006133B0(0x6E)` -> `gm+0x3084A = 0x6E`

### Byte1/Byte2의 모델 선택 (FUN_00525A60 내부)

`player+0x9D` (species = `0x0007 byte1`):

| 값 | 모델 경로 |
|----|-----------|
| 0 | `Data\Plaza\Model\P_AK` |
| 1 | `Data\Plaza\Model\P_AO` |
| 2 | `Data\Plaza\Model\P_PZ` |
| 3 | `Data\Plaza\Model\P_TO` |

`player+0xA1` (subtype = `0x0007 byte2`):

| 값 | 모델 파일 |
|----|-----------|
| 0 | `%s_2.mdl` |
| 1 | `%s_2.mdl` |
| 2 | `%s_3.mdl` |
| 3 | `%s_4.mdl` |
| 4 | `%s_5.mdl` |

특이사항: `species==2 (P_PZ)` + `subtype<2`일 때 별도 스케일 팩터 적용.

Entity 생성 후:
- `entity+0x22C = player+0x90`
- `entity+0x28/0x2C/0x30 = scale` (float)
- `entity+0x34 = 0x100` (flags)
- `player+0x31A = 1` (ready)

---

## 3. FUN_00614370 (Scene Stage Flow)

### 구조

```c
for (local_10 = 0; local_10 <= 9; local_10++) {
    engine_frame();
    switch(local_10) { ... }
    // 매 단계 후 FUN_00528B30() 체크 -> 실패 시 에러 핸들링
}
```

### 각 Stage 역할

| Stage | 호출 함수 | 역할 |
|-------|-----------|------|
| 0 | `SendC2S_0064_LocalBootstrapStatus()` | **Local bootstrap** - self 싱글톤 + entity + ready flag 생성 |
| 1 | vtable `(*piVar1+8)()` | Entity 유효성 검사. `entity == 0`이면 즉시 return (전체 중단) |
| 2 | `FUN_0060C6D0()` | `Data\Plaza\Mount\MiniCar.MDL` 등 탈것 모델 로드 |
| 3 | `FUN_006084A0()` | `Data\Plaza\Model\staff.MDL` 등 NPC/씬 모델 로드 (sky_MDL 포함) |
| 4 | `FUN_0060E510()` | 물/사운드/환경 효과 초기화 |
| 5 | `FUN_006104C0()` | `PLAZA_CHAIR` 등 가구/인터랙션 오브젝트 로드 |
| 6 | `FUN_00614720()` | **매니저 가상 호출 4종** - 카메라, 조명, UI, 씬 매니저 초기화 |
| 7 | `FUN_00611C40()` | 추가 씬 데이터 로드 |
| 8 | `FUN_0060D4C0() + FUN_0060D4F0(p1,p2)` | 최종 렌더링 설정 + param 전달 |
| 9 | `FUN_00619F40()` (nop) + `FUN_0050FE80(0x422, 1, -1)` | **완료 신호** 전송 |

### 중요 게이트

- **Stage 1**: entity가 null이면 전체 flow가 중단. `SendC2S_0064_LocalBootstrapStatus`이 성공적으로 entity를 생성해야 함.
- **Stage 3**: `sky_MDL_325` entity를 찾는데 실패하면 크래시 (`0x002084CD` 크래시 참조).
- **Stage 6**: `FUN_00614720`에서 `param_1+8`이 null이면 모든 가상 호출을 스킵. non-null일 때 4개의 간접 호출 실행.
- **Stage 9**: `FUN_0050FE80(0x422, 1, -1)` -> `FUN_005101F0({0x422, 1, -1})` 로딩 완료 이벤트 발행.

### 에러 핸들링

매 stage 후 `FUN_00528B30()` 체크:
- 반환값 0이면: `FUN_005303D0(0x11)` + `FUN_00508F20()` + `FUN_005BF2C0(0x11)` (에러 리포트)

---

## 4. S->C 0x0066 핸들러: HandleS2C_0066_BatchRemoteActorSpawn

### 페이로드 구조

0x1A(26)바이트 레코드의 배열. 핸들러가 `payload_size / 0x1A`만큼 반복.

### 레코드 레이아웃 (0x1A 바이트)

| 오프셋 | 크기 | 필드 | 용도 |
|--------|------|------|------|
| `+0x00` | 1 | action byte | `0x0A` -> scene code 0x2E, `0x0B` -> scene code 0x2F |
| `+0x01` | 4 | actor id (u32) | entity의 `+0x2F8`에 저장 |
| `+0x05` | 1 | species byte | entity `+0x9D` (0x14 이상이면 -0x14 보정, `+0x9D` 용 flag 설정) |
| `+0x06` | 1 | subtype byte | entity `+0xA1` |
| `+0x07` | 13 | name (C string) | 이름 버퍼 복사 |
| `+0x14` | 1 | appearance byte 1 | `+0x314` |
| `+0x15` | 1 | appearance byte 2 | `+0x315` |
| `+0x16` | 1 | appearance byte 3 | `+0x316` |
| `+0x17` | 1 | appearance byte 4 | `+0x317` |
| `+0x18` | 1 | extra pair byte 1 | `0xFF`이면 스킵; else `FUN_00527A70(val, +0x19)` |
| `+0x19` | 1 | extra pair byte 2 | |

### 처리 흐름

1. 각 레코드에 대해 `FUN_0050D790(record, 1)` 호출:
   - self actor id와 비교 (`FUN_0050D8E0` -> `player+0x2F8`)
   - **self id와 같으면**: `local_c = 0` 반환 (self에 대해서는 스킵)
   - **다른 actor**: 기존 actor-list에서 동일 id 검색 -> 없으면 `FUN_0050D690()`으로 새 슬롯 할당
   - 새 슬롯에 `RemoteActor_InitFrom0066Record(record)` 호출:
     - `actor+0x9D = species`, `actor+0xA1 = subtype`, `actor+0x2F8 = id`
     - 이름 복사, appearance bytes 4개 저장
     - `actor+0x2F6 = 0` (0x00524280에서는 1, 여기서는 0 - self vs other 구분)
   - `FUN_00524620(1)` + `GetTickCount()` -> `FUN_00524CF0`
   - `FUN_0050F0A0(slot)`
2. self id와 다른 actor만 처리한 후, action byte에 따라:
   - `0x0A`: `FUN_00527A40(0x2E)` + 환경 5종 리셋 + `FUN_00526E80(1, 0)`
   - `0x0B`: `FUN_00527A40(0x2F)` + 환경 5종 리셋 + `FUN_00526E80(1, 1)`
   - 기타: `+0x18 != 0xFF`이면 `FUN_00527A70(+0x18, +0x19)`
3. 루프 완료 후 `FUN_0050DA70()` -> `FUN_00520C40()` finalize

### Self Entry 구성

0x0066은 **self actor id와 동일한 레코드를 건너뛴다**. 즉:
- 0x0066은 **다른 플레이어/NPC**를 actor-list에 추가하는 패킷
- self 플레이어는 0x0064에 의해 별도 경로로 처리됨
- 그러나 0x0066의 action byte `0x0A`/`0x0B`에 의한 환경 설정(scene code, weather)은
  self가 아닌 actor에 대해서도 실행되므로 씬 전체 환경에 영향

---

## 5. 로딩 완료 게이트

### gm+0x31946 Ready Latch

`FUN_006133E0`이 읽는 값: `gm+0x3179A` (이전 문서에서 0x31946으로 추정했으나,
실제 Ghidra 디컴파일에서는 `param_1 + 0x3179A`).

- `FUN_00613410(0)`: `gm+0x3179A = 0` (bootstrap 시작 시 0으로 초기화)
- bootstrap 종료 시 `FUN_006133E0()` 반환값이 `local_30`에 합산
- `FUN_005AB710(local_30)`: 이 값을 기반으로 후처리 결정

이 latch는 scene bootstrap(`SendC2S_0064_LocalBootstrapStatus`)의 결과 플래그 중 하나이며,
직접적인 로딩-화면-닫기 gate는 아니다.

### popup+0x9C Close Flag

기존 연구(03_loading_popup_and_close_path.md)에서 확인:
- `popup+0x9C = 1`: close request path가 발동됨
- `popup+0x9C = 0`: 아직 close 미실행 또는 close 실패 후 리셋

로딩 종료의 실제 게이트 체인:
1. `FUN_00614370` stage 0-9 모두 완료
2. Stage 9에서 `FUN_0050FE80(0x422, 1, -1)` 발행
3. 0x0064 핸들러 끝에서 `FUN_0050A840()` 호출
4. popup close 경로 도달 -> `popup+0x9C = 1`

### player+0x31A Ready Flag

- `FUN_005247F0(1)` 또는 `FUN_00525A60` 내부에서 `player+0x31A = 1`
- entity가 성공적으로 생성되었을 때만 설정
- 이 값이 0이면 self 싱글톤이 아직 미완성

---

## 6. 전체 State-1 전환 흐름 (종합)

### 정상 부트스트랩 순서 (추정)

```
[State-0]
  C->S 0x0000 (login)
  S->C heartbeat
  C->S 0x0004 (char select)
  S->C 0x0002 (transition trigger)
  S->C 0x0003("Data\Space\Plaza") (scene path)
  C->S 0x0007 (char creation/select)
  S->C 0x0007 (full char data - byte1=species, byte2=subtype)
  S->C 0x0005, 0x0010 (wire: 0x000A), 0x0011 (wire: 0x000B) (stats/resources)
  C->S 0x0001
  C->S 0x0017 (state transition request)

[State-0 -> State-1 전환]
  S->C opcode 100 (= 0x0064) -> CLogicManager::0x594310이 logic state를 1로 설정

[State-1 진입 직후]
  gm+0x31C72 플래그 검사 (HandleS2C_0007_EmitPostSetupStateRequest):
    != 0 -> FUN_0050A7F0(0x6E) -> Plaza 분기
    == 0, gm+0x31C73 == 0 -> FUN_0050B090() -> FUN_0050A7F0(100) -> PatHouse 분기
    == 0, gm+0x31C73 != 0 -> FUN_0050A7F0(0x6F) -> 다른 분기

[Plaza 분기 (0x6E)]
  FUN_0050B400(0x6E) -> FUN_0050B700(0x6E)로 초기화
  switch(0x6E) -> FUN_00614370(param1, param2)으로 scene stage flow 진입
  -> Stage 0: SendC2S_0064_LocalBootstrapStatus() - local bootstrap (self 싱글톤 생성)
  -> Stage 1~8: scene asset 로드
  -> Stage 9: 완료 신호

[State-1 패킷 처리 (DispatchState1_S2C)]
  0x0064 -> HandleS2C_0064_ApplyAuthoritativeSelf: self entry + entity 생성 + 좌표 + 로딩 완료
  0x0065 -> FUN_00615B20 -> FUN_0050D5D0: actor-list finalize
  0x0066 -> HandleS2C_0066_BatchRemoteActorSpawn: actor-list 레코드 추가 (0x1A bytes/record)
  0x0068 -> HandleS2C_0068_BatchActorState: actor 위치 업데이트 (0x18 bytes/record)
  0x0069 -> HandleS2C_0069_ApplyActorActionState: actor 위치 커밋
```

### 현재 서버의 문제

현재 서버는 C->S 0x0017 수신 시 다음을 전송:
```
0x0064(entry_mode=0x00) + 0x0065 + 0x0066 + 0x0068 + 0x0069
```

**문제 1: entry_mode=0x00은 Plaza 환경 초기화를 하지 않음**
- `0x0A`를 사용해야 `player+0x107 = 0x2E` (Plaza scene code), weather 초기화,
  `player+0x324/0x325` 활성화가 실행됨

**문제 2: 타이밍**
- 0x0064는 0x00594310에서 logic state를 1로 전환하는 트리거 역할도 함
- state-1 전환 후 `HandleS2C_0007_EmitPostSetupStateRequest` -> `FUN_0050A7F0(0x6E)` -> `FUN_00614370`이
  scene stage flow를 시작하는데, 이 flow의 Stage 0에서 `SendC2S_0064_LocalBootstrapStatus`이 먼저
  local bootstrap을 완료해야 함
- 0x0064의 핸들러 `HandleS2C_0064_ApplyAuthoritativeSelf`은 이미 생성된 entity의 좌표를 설정하고
  `FUN_0050A840`으로 로딩 종료를 트리거
- 즉 **scene stage flow와 0x0064 핸들러는 별개 경로**이며, 둘 다 필요

**문제 3: gm+0x31C72 플래그**
- `HandleS2C_0007_EmitPostSetupStateRequest`에서 `gm+0x31C72 != 0`이어야 Plaza(0x6E) 분기를 탐
- 이 플래그는 state-0에서 설정되어야 하며, 현재 서버가 이를 설정하는 패킷을
  보내고 있는지 확인 필요

### 권장 수정 사항

1. **0x0064 entry_mode를 `0x0A`로 변경**: Plaza scene code 및 환경 초기화 활성화
2. **gm+0x31C72 설정 확인**: 이 플래그가 0이면 PatHouse(100) 분기로 빠짐 -
   Plaza를 원하면 이 플래그가 non-zero여야 함
3. **0x0066 action byte `0x0A`**: 현재 서버의 actor_0066 빌더에서 이미 action=0x0A
   사용 중이므로 OK
4. **scene stage flow 완료 보장**: Stage 0의 `SendC2S_0064_LocalBootstrapStatus`이 정상 완료되려면:
   - `0x0007 byte1` (species)이 0~3 범위여야 모델 경로 선택 성공
   - `0x0007 byte2` (subtype)이 0~4 범위여야 모델 파일 선택 성공
   - `FUN_005270D0` 이름 중복 체크 통과 (기존 entity 없어야 새로 생성)

---

## 7. FUN_00614720 (Stage 6) 상세

Stage 6은 scene 매니저 가상 호출 4종을 실행:

```c
void FUN_00614720(int param_1) {
    param_1+8 = FUN_004ED7B0();  // 매니저 객체 획득
    if (param_1+8 != 0) {
        // 가상 호출 1: FUN_005CE000 계열
        // 가상 호출 2: (**(piVar2+4))() - FUN_0050C430에서 획득
        // 가상 호출 3: (**(piVar2+4))() - FUN_0050C160에서 획득
        // 가상 호출 4: (**(piVar2+4))() - FUN_0050C190에서 획득
        // 추가: FUN_005F38B0, FUN_005F3910, FUN_005F2110
        // FUN_005AFDD0, FUN_0050DCA0
        // 가상 호출 5: (**(piVar2+4))() - FUN_0050C310에서 획득
        // FUN_0060A900
    }
}
```

`param_1+8 == 0`이면 전체 스킵. 크래시 이력(`unknown+0x00000002`)은
여기서 가상 호출 대상이 null/invalid일 때 발생.

---

## 8. FUN_00524280 vs RemoteActor_InitFrom0066Record 비교

| 항목 | FUN_00524280 (self) | RemoteActor_InitFrom0066Record (other actor) |
|------|---------------------|---------------------------|
| 호출 경로 | `SendC2S_0064_LocalBootstrapStatus` | `FUN_0050D790` (0x0066) |
| `+0x9D` 설정 | `param_2+5` | `param_2+5` (0x14 보정 포함) |
| `+0xA1` 설정 | `param_2+6` | `param_2+6` |
| `+0x2F8` 설정 | `param_2+1` | `param_2+1` |
| `+0x2F6` | `= 1` | `= 0` |
| `+0x301` | 미설정 | `= param_2+1` |
| `+0x314~0x317` | 미설정 | `= param_2[0x14..0x17]` |
| 이름 복사 | `FUN_00527C00` | `FUN_00527C00` + `FUN_006543B0` |

핵심 차이: `+0x2F6 = 1`은 self 표시, `= 0`은 other actor 표시.

---

## 9. FUN_00521E90 (장비 슬롯 설정)

```c
void FUN_00521E90(slot, value, param_3) {
    if (value == 0xFF) {
        FUN_00522AE0(slot);  // clear/sentinel
        return;
    }
    switch(slot) {
        case 0: value += 10000; if (value < 10000 || value > 10009) return; break;
        case 1: value += 20000; if (value < 20000 || value > 20006) return; break;
        case 2: value += 30000; if (value < 30000 || value > 29987) return; break;
        case 3: value += 40000; if (value < 40000 || value > 39975) return; break;
    }
    FUN_00521FF0(slot, value, param_3);
}
```

유효 범위 (0x0007 `+0x1D4..+0x1D7` 에서 옴):
- slot 0: value 0~9 (-> 10000~10009) - 0x2719 = 10009
- slot 1: value 0~6 (-> 20000~20006) - 0x4E26 = 20006
- slot 2: value 0~51 (-> 30000~30051) - 0x7533 = 29987... 범위 검증 필요
- slot 3: value 0~71 (-> 40000~40071) - 0x9C47 = 39975... 범위 검증 필요

`0xFF`는 명시적 클리어. `0x00`은 각 버킷의 첫 번째 유효 아이템 선택.
