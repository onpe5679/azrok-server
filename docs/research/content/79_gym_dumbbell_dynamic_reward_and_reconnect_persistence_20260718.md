# Gym 아령 자연 실행 보상·저장·재접속 검증 (2026-07-18)

상태 표기: **VERIFIED** = 클라이언트 디컴파일 또는 실제 패킷/x32dbg 실측, **INFERRED** = 직접 확인 전 추론.

## 결론

- **VERIFIED:** Plaza의 Gym 문을 실제 클릭했을 때 C→S `0x0065` payload
  `08 15 15 02 00 00 85 05 00 00`가 발생했고 Gym이 자연 로드됐다.
- **VERIFIED:** Gym 원본 선택 링은 `팔굽혀펴기 / 아령 / 줄넘기`이며 아령 popup ID는 `0x42`다.
- **VERIFIED:** 자연 아령 경로는 `FUN_00596690`의 sys.tmp `+3` 경로가 아니라
  `FUN_0055e020 → FUN_0055e380(scene 0x66) → FUN_005a1b90(domain 2)` 공유 미니게임 리워드 경로다.
- **VERIFIED:** 현재 상태의 아령 보상은 결정론적 `stat32 +8`이다. 같은 세션에서 두 번 실행해
  `0 → 8 → 16`을 실측했다.
- **VERIFIED:** 각 완료 직후 C→S `0x0007` 196바이트 저장이 발생했고, 서버/클라이언트 완전 재시작 뒤
  S→C `0x0007 +0x4B`가 `16`을 복원했다.

## 1. 자연 입장과 UI

이 실행에서 Gym descriptor의 entry/report 좌표 `(533,1413)` 부근에 도달한 뒤
마지막 문 클릭은 원본 UI로 수행했다. 후속 수동 실측에서 실제 avatar 문 앞
C→S 이동 좌표는 `(521,1741)`이었으며, `(533,1413)`은 portal entry/report
좌표임이 분리 확인됐다(81).

```text
C→S 0x0065 payload: 08 15 15 02 00 00 85 05 00 00
room_kind: 8
room_name: gym
```

Gym 안내 대화를 원본 feather 버튼으로 진행하면 선택 링이 열렸다. 화면에 직접 표시된 세 항목 중
왼쪽 `아령` 버튼을 클릭했다. 정적 경로의 popup `0x42`, local sequence `0x0C`,
action family `F8/F9/FA → stat32`와 일치한다.

## 2. `+3` 가설 반증과 실제 `+8` 공식

sys.tmp의 아령 행에 `+3`이 존재한다는 사실 자체는 맞지만, 자연 Gym 미니게임은 그 executor를 사용하지 않는다.
자연 경로의 Gym domain 2 기본 벡터와 현재 스탯 티어 보정은 다음과 같다.

두 번의 관측된 자연 사이클에서는 x32dbg의 `FUN_00596690` breakpoint가 한 번도 적중하지 않았고,
결과 대화 종료 후 선택 링으로 돌아갈 때도 추가 저장이 없었다. 정적 상태머신에는 다른 최종 sentinel 조합이
sys.tmp executor에 도달할 가능성이 남아 있으나, 그 별도 `+3` 실행은 이번 실제 플레이에서 **NOT VERIFIED**다.

```text
대상 stat:       3    4    5    6    7    9   32
Gym 기본:      -10   -5   -5   +5   -5   -5   +5
stat5=70 보정:   0   -2    0   +2   -2    0   +2
stat3=51 보정:  -1   -2    0   +2    0    0   +1
합계:          -11   -9   -5   +9   -7   -5   +8
```

두 번의 실제 저장 스냅샷도 이 벡터와 정확히 일치했다.

```text
stat3   51 → 40 → 29
stat4   75 → 66 → 57
stat5   70 → 65 → 60
stat6   80 → 89 → 98
stat7    0 →  0 →  0  (최솟값 clamp)
stat9   50 → 45 → 40
stat32   0 →  8 → 16
```

x32dbg 두 번째 실행 실측:

```text
0055BDB0 local_sequence=0x0C
005A4BA0 stat_index=0x20, stat_delta=8, stat_current_before=8
         return_address=005A2084  (FUN_005A1B90 내부)
005A4770 args=(0,1,7), payload stat32=16
00593D10 opcode=0x0007, payload_length=196
```

따라서 이 `+8`은 난수나 레벨 보너스가 아니라 현재 허기(stat3)·에너지(stat5)의 20단위 티어가 더해진 값이다.

## 3. 저장과 재접속

첫 실행 전 저장 파일 `506c61796572_c2s0007.bin`의 C2S `+0x4A` stat32는 `0`이었다.

```text
첫 완료:  C→S #472 opcode 0x0007, stat32=8,  content_save_count=1
둘째 완료: C→S #492 opcode 0x0007, stat32=16
```

두 번째 저장 SHA-256:

```text
EC538EF2B77A7AD8901E9B4AE5D337FB7D6EED5ABF70BEBBD57B1B0C01F57A3D
```

서버와 클라이언트를 완전히 다시 시작하고 같은 `playable / profile_playable_v2` 프로필의 `Player`로 접속했다.
새 캡처 `packets_20260718_052925.txt`의 최초 S→C `0x0007`을 직접 파싱한 결과:

```text
payload bytes = 472
evolution     = 1
stat31        = 0
stat32        = 16
stat33        = 0
```

즉 C2S `+0x4A` → 저장 파일 → 재접속 S2C `+0x4B` 왕복이 실제 사용자 플레이 경로에서 VERIFIED다.

## 4. 기존 문서 교정

- content/69의 `0xDC-E2=체육` 분류는 잘못됐다. Gym 자연 action family는 `F6-FD`다.
- content/70의 `Gym action 0x41 + stat0x20 +3`은 popup/action/보상 경로가 모두 잘못됐다.
  아령 popup은 `0x42`, action family는 `F8/F9/FA`, 현재 자연 보상은 `+8`이다.
- content/76의 공유 엔진과 기본 `+5`는 맞지만, 자연 완료 후 네트워크 전송이 없다는 결론은 틀렸다.
  `FUN_005A4770(0,1,7)`이 C→S `0x0007` 저장을 즉시 전송한다.

## 증거

- `captures/packets_20260718_041857.txt` — Gym 자연 입장, #472/#492 저장
- `captures/packets_20260718_052925.txt` — 재접속 S2C stat32=16
- `artifacts/dynamic-analysis/gym_ready_for_action_20260718.bmp`
- `artifacts/dynamic-analysis/gym_after_dumbbell_select_20260718.bmp`
- `artifacts/dynamic-analysis/x32dbg_gym_plus8_recheck_pid41844_20260718.jsonl`
