# Azrok Strong-Inference Game Flow

Date: 2026-04-01
Status: strongest defensible model from current binary + live-log evidence

## 1. 가장 강한 게임 흐름 모델

### Phase A: connect / login shell

```text
connect
-> C->S 0x0000
-> heartbeat starts
-> S->C 0x0000 (0x183 sparse-cache blob)
-> client enters lobby/pet shell
```

### Phase B: room-entry arming

```text
S->C 0x0003
-> path/root stored
S->C 0x0007
-> setup blob imported
-> default room enqueue
S->C 0x0005
S->C 0x000A
S->C 0x000B
```

### Phase C: PatHouse bootstrap

```text
room.wmb
-> room init 100
-> scene mode 2
-> stable room
```

### Phase D: in-room stable loop

현재 live session에서 실제로 이어진 것은 아래다.

```text
repeated C->S 0x0016
-> repeated S->C 0x0016
-> repeated C->S 0x000C
```

즉 현재 evidence 기준으로, stable room 이후 처음으로 반복 등장하는 gameplay candidate는 `0x000C`다.

## 2. “현재 관측상 playable한 흐름”과 “binary-faithful target 흐름”

### 2.1 현재 관측상 playable한 흐름

```text
C->S 0x0000
-> S->C 0x0000
-> S->C 0x0003
-> S->C 0x0007
-> S->C 0x0005
-> S->C 0x000A
-> S->C 0x000B
-> room init
-> stable room
-> C->S 0x000C repeated
```

이 흐름에는 아래가 **필수로 보이지 않았다**.

- `S->C 0x0002`
- `S->C 0x0064`
- `C->S 0x0017`
- `C->S 0x0008`

### 2.2 binary-faithful target 흐름

```text
C->S 0x0000
-> S->C 0x0000
-> S->C 0x0004(sample_kind=0x01, timestamp) x5
-> client internally rewrites fifth sample to 0xFF
-> readiness latch set
-> S->C 0x0003
-> S->C 0x0007
-> S->C 0x0005
-> S->C 0x000A
-> S->C 0x000B
-> room init
-> stable room
```

이 target 흐름은 binary와 더 잘 맞지만, 현재 live run이 이 fidelity를 전부 필요로 했다는 증거는 아직 없다.

## 3. `0x000C`의 위치

현재 evidence에서 `0x000C`는 다음 성격을 가진다.

- room이 안정된 뒤 반복해서 나옴
- 같은 세션에서 반복 관측된 유일한 post-entry gameplay opcode
- 현재 서버는 응답하지 않음
- blind echo를 해도 된다는 근거가 없음

따라서 strong inference는 아래다.

- `0x000C`는 **진짜 게임 상호작용/상태 변경의 첫 번째 서버 계약 후보**
- “정상 플레이”로 가는 다음 큰 구멍은 `0x0017`보다 `0x000C`

## 4. `0x0064`의 위치

binary와 HTTP xref 결과를 합치면 `0x0064`는 이렇게 보는 쪽이 가장 강하다.

- early bootstrap packet이 아님
- state-0 -> state-1 경계 packet
- Hansol stage 0 local bootstrap status 송신과 연결됨
- self/world authoritative sync가 필요한 늦은 단계 packet

즉 `0x0064`는 “아직 못 찾은 필수 login packet”이 아니라, **찾긴 찾았지만 너무 이른 타이밍에 쓰면 안 되는 packet**이다.

## 5. Hansol / Plaza 쪽 strong inference

현재 strongest inference:

```text
room mode 2
-> outdoor transition helper
-> readiness latch (gm+0x31C71) 필요
-> hansol flag (gm+0x31C72) 필요
-> hansol.wmb load
-> Hansol_SceneStageHandler
-> stage 0 emits local C->S 0x0064
-> later state-1 synchronization
```

아직 미완인 부분:

- 이 readiness/hansol flag를 순수 packet만으로 어떻게 자연스럽게 세우는가

## 6. 지금 기준 우선순위

1. `C->S 0x000C` producer/field meaning/server response contract
2. Hansol/Plaza packet-only 자연 전환
3. `C->S 0x0017`의 producer/strict consumer path
4. `C->S 0x0064` 송신측 full serialization

## 7. 최종 요약

현재 가장 정직한 모델은 아래다.

- PatHouse packet-only first entry는 꽤 단단하게 닫혔다
- 그 다음 정상 플레이 확장의 첫 목표는 `0x000C`다
- `0x0064`는 최소 bootstrap이 아니라 늦은 state-1 경계 packet이다
- Hansol/Plaza는 부분 복원 상태이며, 완전한 packet-only recipe는 아직 남아 있다
