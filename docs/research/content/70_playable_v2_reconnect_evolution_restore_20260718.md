# 70 — playable-v2 재접속 진화 복원과 측정 격리 (2026-07-18)

## 결론

- **VERIFIED:** 저장된 C2S `0x0007 +0x05`는 진화 단계입니다.
- **VERIFIED:** 재접속 S2C `0x0007 +0x02`가 `ProtocolState+0x130`에 기록됩니다.
- **VERIFIED:** 따라서 서버 복원 매핑은 `C2S +0x05 -> S2C +0x02`입니다.
- **VERIFIED:** 이 매핑 누락 때문에 저장값/API는 1인데 재접속 클라이언트는 0이었습니다.
- **VERIFIED:** 한 바이트 복원 수정 뒤 실제 wire와 클라이언트 메모리 모두 1입니다.

## 실패 재현

Player 저장본:

```text
server_state/profile_playable_v2/506c61796572_c2s0007.bin
length=196
snapshot[0x05]=1
SHA256=4C0BBC503EA1B6FF7E5A021F269E86162D8E8EF76C85481D593CF7E8DDCD85A3
```

`captures/packets_20260718_032715.txt`의 S2C #6은 payload 시작이
`00 02 00 ...`이었습니다. 같은 세션 API는 `saved_state_loaded=true`,
`persisted_evolution=1`이었지만 read-only Frida observer는
`evolutionGateRead value=0`을 반복 측정했습니다.

## 정적 직접 증거

Ghidra `Azrok.exe`/`Azrok_original.exe`에서 확인했습니다.

1. `DispatchState0Specific_S2C @ 0059DD20` case 7
2. `HandleS2C_0007_LoadSetupBlob @ 0059E330`
3. `0059E37C`가 payload `+0x02`를
   `ProtocolState_SetField130Value @ 00599150`에 전달
4. C2S serializer `FUN_00598EA0`은 getter 결과를
   `object+0x5FD @ 00598ECE`에 저장
5. snapshot 시작은 `object+0x5F8`이므로 wire offset은 정확히 `+0x05`
6. `FUN_005A4770`은 그 시작점부터 `0xC4` 바이트를 전송

역방향 로컬 snapshot importer `FUN_00599050`도 `snapshot+0x05`를 같은
setter에 넣습니다. `ReconnectEvolution` Ghidra bookmark 7개를 저장했습니다.

## 서버 수정과 회귀검사

`azrok_server.py::_apply_saved_character_state()`가 저장본을 찾으면 다음을
먼저 적용합니다.

```python
zone_payload[0x02] = snapshot[0x05]
```

기존 스탯/튜플 매핑 외의 바이트는 복사하지 않습니다. 방향별 레이아웃이
다르므로 C2S prefix 전체를 S2C에 복사하는 방식은 계속 금지합니다.

`tools/test_content_builders.py`에는 evolution 1 round-trip 테스트를 추가했고
`python -m py_compile` 및 13/13 단위 테스트가 통과했습니다.

## 수정 후 실전 검증

저장 파일을 삭제하거나 변경하지 않고 playable 프로파일로 서버/클라이언트를
깨끗하게 재시작했습니다.

- **VERIFIED wire:** `captures/packets_20260718_033343.txt` S2C #9 payload
  시작 `00 02 01 ...`, 즉 `+0x02=1`
- **VERIFIED client:**
  `artifacts/dynamic-analysis/playable_v2_reconnect_field130_20260718_0335.txt`
  에서 `evolutionGateRead value=1` 반복, 최종 owner 값도 1
- **VERIFIED health:** PID 82128 생존, scene 100/phase 2, heartbeat 지속,
  engine error 없음

## 디버거 측정 격리

이전 PID 32624에서 x32dbg가 붙은 동안 Frida agent DLL을 로드하자 x32dbg가
TLS/loader breakpoint를 새로 만들었고, 이후 Frida agent의 `0x80000003`에서
클라이언트가 종료됐습니다.

- **VERIFIED:** 이는 동일 프로세스에 두 디버거를 겹친 측정 충돌입니다.
- **VERIFIED:** 사용자 PC 먹통이나 사용자 입력과는 무관합니다.
- **규칙:** x32dbg와 Frida를 같은 클라이언트에 동시에 attach하지 않습니다.
- **구현:** x32dbg interaction observer는 active profile에 없는 breakpoint를
  semantic checkpoint로 해석하지 않고 즉시 제거한 뒤 재개합니다.

## 현재 경계

- **VERIFIED:** 재접속 뒤 외출 진화 게이트는 1입니다.
- **NOT VERIFIED:** 이 새 세션에서 실제 출구 클릭 이후 Plaza까지의 반복 완주.
> **SUPERSEDED by 79.** `0x41`은 팔굽 popup이고, 자연 아령은 popup `0x42` → action `F8/F9/FA`다.

- **VERIFIED (79):** Gym 아령 자연 실행 두 번으로 stat `0x20`이 `0→8→16`, 각 완료 직후 C→S `0x0007` 저장,
  서버/클라이언트 완전 재시작 뒤 S→C `0x0007 +0x4B=16` 복원까지 end-to-end 완료.
