# Azrok Plaza 최신 세션 핸드오프 — 2026-07-17 23:45 KST

이 문서는 새 세션이 가장 먼저 읽어야 하는 실행용 핸드오프다.
연구 사실의 권위 인덱스는 `docs/research/INDEX.md`, 종합 현황은
`docs/research/00_current_status.md`다. 그 다음 이 문서의 절차대로 실제
런타임을 다시 올린다.

## 1. 현재 종료 상태 (VERIFIED)

사용자 요청으로 클라이언트와 서버를 모두 정상 종료했다.

- `Azrok.exe`: 0개
- TCP `9207`: listen 없음
- TCP `9300`: listen 없음
- `Azrok-Plaza-Launch`: Ready
- `Azrok-Plaza-Stop`: Ready, 마지막 결과 0
- 남은 `REQUEST_*` one-shot marker: 없음
- 서버 GUI 탭을 새로 열지 말 것. 사용자가 필요하면 기존 주소
  `http://127.0.0.1:9300/`를 새로고침한다.

새 세션은 런타임이 살아 있다고 가정하지 말고 직접 시작·검증해야 한다.

## 2. 절대 조건

- 바이너리 파일 패치는 0개로 유지한다.
- 현재 지원 실행은 Acknex 네이티브 `-NX200`이다. 이것은 바이너리
  메모리 패치가 아니라 엔진 명령행 옵션이다.
- `Nexus=40` 비교 기준선은 계속 보존하지만, 같은 콘텐츠 프로파일의
  자연 진화에서 E1201이 실증됐으므로 기본 복원 실행은 200이다.
- 임의 ACK나 메모리 shortcut으로 성공을 합성하지 않는다.
- Ghidra 정적 분석과 x32dbg/Frida/실제 플레이 동적 분석을 병행한다.
- 게임 창은 항상 화면 맨 왼쪽 위 `(0,0)`에 둔다. 다른 위치에서는
  클릭 좌표가 어긋나는 엔진/게임 입력 문제가 있다.
- 서버 GUI를 실행 때마다 새 브라우저 탭으로 자동으로 열지 않는다.

## 3. 이번 세션의 가장 큰 VERIFIED 결과

### 3.1 자연 성장 → 실제 문 → Plaza 반복 성공

Restart 4의 PID `138892`와 보조 PID `60884`가 각각 다음 자연 경로를
완주했다.

```text
bootstrap evolution 0
-> Frida exact sleep button (ButtonId 33, caller 0x005E3F14)
-> 자연 Redron 성장 (+0x130=1)
-> C2S 0x0007 +0x05 = 1 저장
-> 사용자가 실제 PatHouse 출구 문 클릭
-> C2S 0x0019[00]
-> S2C 0x000D[00]
-> C2S 0x0016[01] / S2C 0x0004[01+timestamp] 5회
-> C2S 0x0064[01]
-> S2C 0x0064 27B (0064-only, 006E 없음)
-> scene=110 / phase=4 / dispatch_mode=1 / self_actor_id=1
-> heartbeat 재개
```

Restart 4 primary의 정확한 full 0064 payload:

```text
0a01000000007b0f0000c3000000000000000202ea070611170b2b
```

Restart 2에서 같은 의미의 0064 뒤 한 번 클라이언트 엔진이 멈췄지만,
Restart 3/4는 정상 생존했다. 패킷 malformed로 단정하지 말고 note 63의
간헐 post-load race/deadlock 비교를 먼저 읽는다.

### 3.2 두 클라이언트 실제 멀티플레이 수명주기

Restart 4의 두 클라이언트가 같은 9207 서버와 Plaza에 들어갔다.

- 양쪽 `peer_count=1`, `visible_remote_actor_count=1`
- 양쪽 S2C `0x0066` actor upsert 1회
- 양쪽 S2C `0x0068` position 1회
- 두 실제 화면에 `Guest`와 `Player`가 동시에 렌더됨
- primary C2S `0x0066` 증가와 secondary S2C `0x0068` 증가가 함께 발생해
  이동 relay wire path가 검증됨
- secondary 종료 시 primary S2C `0x0067[03 00 00 00]`가 0→1,
  peer/visible이 1/1→0/0, 화면의 `Player`가 사라지고 self는 생존

핵심 캡처:

- `captures/packets_20260717_230719.txt`
- `artifacts/dynamic-analysis/restart4_multiplayer_primary.bmp`
- `artifacts/dynamic-analysis/restart4_multiplayer_secondary.bmp`
- `artifacts/dynamic-analysis/restart4_multiplayer_after_leave.bmp`

주의: 사용자가 다른 창을 클릭했는데 Azrok 캐릭터가 움직인 현상이
관측됐다. 따라서 이동 relay 자체는 VERIFIED지만, 그 이동을 발생시킨
물리 입력 창의 귀속은 CONTAMINATED / NOT VERIFIED다. 한 클라이언트의
스폰 위치와 카메라 각도도 사용자 조작으로 원본 기준에서 벗어났으므로
초기 좌표/카메라 계약 증거에 쓰지 않는다.

### 3.3 S2C 0x0065와 leave 계약

- 현재 self 확정 뒤 S2C `0x0065` 자동 전송은 금지한다.
- 이 패킷은 fixed self/full actor부터 teardown한 뒤 원격 목록을 비우며,
  active Plaza에서 늦게 보내면 다음 minimap frame이 크래시한다.
- 현재 roster는 `0x0066` upsert + `0x0068` position + targeted `0x0067`
  leave로 운영한다.
- 클라이언트 원격 actor pool은 100명, 한 화면의 물리 상한은 self 포함
  101명이다.

## 4. 서버 GUI/API 변경

수정 파일:

- `azrok_server.py`
- `azrok_control_page.py`

적용 내용:

- 전환 상태를 `scene/phase + dispatch mode + self actor + heartbeat +
  engine error`로 판정
- `pathouse_stable`, `pathouse_exit_ready`, `plaza_healthy`,
  `post_0064_stalled` 등 노출
- 멀티클라에서 primary memory watch와 secondary proto_state를 섞던
  attribution 버그 수정
- 각 player에 독립 `transition` 객체 추가
- 전역 multi-client 요약, `memory_watch_entity_id`, `active_entity_id` 추가
- 클라이언트 카드에 독립 전환 badge와 콘텐츠 저장/진화 요약 표시
- 성장 상세가 어느 active entity의 proto_state인지 표시
- 실제 출구 오브젝트를 `dm_door_0003_057 / dm_door_0003.MDL`로 교정;
  `mirror_01`은 옷장/거울이지 출구가 아님

LIVE VERIFIED:

- 전체 재시작 뒤 API가 per-player transition,
  `memory_watch_entity_id=2`, `active_entity_id=2`를 반환
- 새 HTML이 클라이언트별 귀속/active entity 문구를 실제로 제공

다음 시작 때 함께 활성화될 마지막 source-only 수정:

1. primary의 `scene=100/phase=2`를 room_kind 보고 전에도 PatHouse로 판정
2. per-player `last_content_save_payload`가 hex string일 때도 `+0x05`
   자연 진화를 파싱해 `pathouse_exit_ready`로 표시

이 두 줄은 마지막 서버 시작 뒤에 편집됐으므로 다음 시작이 첫 live
검증이다. 새 세션은 성장 후 player transition이
`pathouse_exit_ready`가 되는지 확인한다.

## 5. 예약 작업/UAC 안전 경계

`tools/stop_azrok_elevated.ps1`은 알 수 없는 `REQUEST_*` 파일이 있으면
기본 stop-all로 떨어지지 않고 fail-closed한다. 이 방어는 실제 PID/서버
보존 negative test를 통과했다.

정확한 요청 이름:

- UI: `REQUEST_AZROK_UI_ACTION.json`
- 보조 클라이언트: `REQUEST_LAUNCH_ALT_INSTANCE.json`
- 클라이언트 하나만 종료: `REQUEST_CLOSE_AZROK_INSTANCE.json`
- Frida: `REQUEST_FRIDA_INPUT.json` (보통 wrapper가 생성)

과거 오타 `REQUEST_UI_ACTION.json`은 절대 쓰지 않는다. 이 오타가 한 번
default stop-all을 유발했으며 현재 guard로 재발을 막았다.

UAC 없이 Frida 입력:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\invoke_azrok_frida_elevated.ps1 `
  -ProcessId <PID> -PushButton -ButtonId 33 -Repeat 120 `
  -TargetCaller 0x005E3F14 -Param2 1 -Param3 -1 -SettleMs 3000
```

캐릭터 slot/connect 자동화:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\invoke_azrok_frida_elevated.ps1 `
  -ProcessId <PID> -ClickSequence `
  -X1Ratio 0.145 -Y1Ratio 0.655 -X2Ratio 0.075 -Y2Ratio 0.925 `
  -SequenceHoverMs 350 -SequenceHoldMs 180 -InterClickMs 1500 -SettleMs 3000
```

간혹 click-sequence는 실제 입력을 완료한 뒤 예약 작업 wrapper가 45초
timeout으로 남았다. 이 경우 먼저 API/화면으로 실제 효과를 확인하고,
게임을 죽이지 말고 `Stop-ScheduledTask -TaskName Azrok-Plaza-Stop`으로
보조 task runner만 정리한다. exact push-button 경로는 정상 종료했다.

## 6. 새 세션 시작 절차

1. 반드시 `docs/research/INDEX.md`와 이 문서를 읽는다.
2. 현재 종료 상태를 다시 확인한다.
3. 다음으로 주 런처/서버를 시작한다.

```powershell
Start-ScheduledTask -TaskName Azrok-Plaza-Launch
```

4. `http://127.0.0.1:9300/api/state`가 응답하고 Azrok PID가 1개인지 확인.
5. 창을 `(0,0)`에 유지하고 캐릭터 선택/접속을 완료.
6. PatHouse에서 exact sleep button으로 자연 Redron 성장.
7. 다음 세 가지를 확인:
   - `content.natural_evolution=1`
   - per-player `protocol.natural_evolution=1`
   - per-player/global transition=`pathouse_exit_ready`
8. 성장/퀘스트 대화를 닫고 사용자가 실제 출구 문 클릭.
9. `C2S 0019 -> S2C 000D -> 5x0004 -> C2S/S2C0064`와
   `plaza_healthy`를 확인.
10. 서버 GUI 브라우저는 새로 열지 말고 기존 탭을 한 번 새로고침한다.

## 7. 종료 직전 런타임 (이제 종료됨)

종료 전 마지막 세션은 capture
`captures/packets_20260717_233509.txt`였다.

- PID `65288`
- native Nexus 200, binary patch 0
- PatHouse `scene=100 / phase=2 / mode=0`
- Redron 자연 성장 완료
- `C2S 0x0007 +0x05=1`, save sum 5040 일치
- `content.outside_gate_ready=true`
- heartbeat 정상, engine error 없음
- 실제 출구 문은 아직 클릭하지 않은 상태에서 사용자가 핸드오프를 요청

서버 state store에는 evolution 1이 저장돼 있지만 안전 부트스트랩은 항상
evolution 0이다. 따라서 새 재접속 뒤에는 sleep/care를 한 번 자연 실행해
이번 세션의 `+0x130`을 다시 1로 올려야 실제 외출 준비가 된다.

## 8. 다음 우선순위

### P0 — 새 시작에서 GUI 최종 live 확인

- 위의 마지막 두 source-only 수정이 실제로
  `pathouse_exit_ready`를 클라이언트별로 표시하는지 확인
- 보조 클라이언트를 다시 붙여 global badge가
  `2 clients · Plaza N / PatHouse N`으로 합성되는지 확인

### P1 — 전체 로컬 공간 실제 플레이 조사

공간 로더 계약:

| selector | WMB | room code |
|---:|---|---:|
| 1 | `playroom.wmb` | `0x65` |
| 2 | `gym.wmb` | `0x66` |
| 3 | `magic.wmb` | `0x67` |
| 4 | `cook.wmb` | `0x68` |
| 5 | `shop.wmb` | `0x69` |
| 6 | `library_1.wmb` | `0x6A` |

문/월드 이동은 로컬 loader다. 각 방에서 실제 오브젝트/버튼을 누르고
새 C2S opcode와 payload를 capture별로 분리한다. 서버 무응답이라고 먼저
가정하지 않는다.

알려진 로컬 콘텐츠 버튼:

- Gym: `0x41` 팔굽혀펴기, `0x42` 아령, `0x43` 줄넘기
- Gym exit: `0x5C`, caller `0x005DB4D4`
- Magic: `0x3E`, `0x3F`, `0x40`
- Library: `0x44`; level `0x45..0x47`
- Cook: `0x48..0x56`

Gym action은 local consumer `FUN_005E3EE0` 경로이고 서버 ACK 대기라는
옛 가설은 폐기됐다. 실제 완료 시 발생하는 `0x0007/0x0010/0x0009/...`
저장 연쇄를 관측한다.

### P2 — 다중 창 입력 누수 재현

- Azrok 한 개/두 개 각각에서 다른 앱 창 클릭 대조
- Frida hook 미부착/부착 대조
- 어떤 HWND/focus/global cursor 조건에서 Azrok world movement가 생기는지
  캡처와 함께 판정
- 이 조사가 끝나기 전 다른 창 클릭으로 생긴 이동 좌표는 gameplay
  baseline에서 제외

### P3 — 콘텐츠 프로토콜 복원

- Shop 구매, 요리 소비, 마법/독서/놀이 보상, 장비 `0x000C`, 채팅
  `0x006A`를 실제 플레이 + x32dbg sender/consumer 추적으로 확정
- 방향이 같은 번호라도 의미가 다르므로 C2S/S2C를 항상 별도 분석
- 근거 없는 echo/ACK를 추가하지 않는다

## 9. 핵심 문서

- `docs/research/INDEX.md`
- `docs/research/00_current_status.md`
- `docs/research/world/63_plaza_post_0064_stall_and_clean_retry_20260717.md`
- `docs/research/tooling/64_scheduled_task_request_guard_and_restart4_20260717.md`
- `docs/research/multiplayer/67_restart4_natural_two_client_plaza_and_transition_attribution_20260717.md`
- `docs/research/world/43_static_local_loader_and_content_descriptors_20260717.md`
- `docs/research/world/36_manual_playback_packet_correlation_2026-07-17.md`
- `docs/research/world/32_popup_ring_gym_buttons_41_42_43_2026-07-17.md`
- `docs/research/tooling/62_acknex_native_nx_and_e1201_allocator_20260717.md`

## 10. 이번 세션의 주요 변경 파일

- `azrok_server.py`
- `azrok_control_page.py`
- `tools/stop_azrok_elevated.ps1`
- `tools/invoke_azrok_frida_elevated.ps1`
- `tools/azrok_frida_input.py`
- `tools/azrok_input_hook.js`
- `tools/x32dbg_hang_snapshot.py`
- `tools/invoke_x32dbg_hang_snapshot.ps1`
- `tools/PrintContainingFunctions.java`
- 위 63/64/67 연구 문서와 INDEX/00/README

마지막 정적 검증:

```text
python -m py_compile azrok_server.py azrok_control_page.py  PASS
node --check (dashboard extracted JS)                       PASS
python -m unittest tools.test_content_builders              9/9 PASS
```

새 세션은 계획만 쓰고 멈추지 말고, 6절의 시작 명령부터 실제 실행한다.
