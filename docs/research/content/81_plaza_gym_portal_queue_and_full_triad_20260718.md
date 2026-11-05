# Plaza→Gym 문 이벤트 직접 전환과 Gym 3종 완주 (2026-07-18)

상태 표기: **VERIFIED** = 디컴파일 또는 실제 클라이언트/패킷 실측,
**INFERRED** = 직접 증거를 조합한 추론, **NOT VERIFIED** = 후속 동적 확인 필요.

## 결론

- **VERIFIED:** 화면 이동·카메라 탐색 없이 원본 문 클릭의 마지막 commit만 재현해
  Plaza에서 Gym을 정상 로드할 수 있다. 최소 경계는
  `FUN_006142C0(PortalMgr, 2)`이며 이 함수는 `PortalMgr+0x314=2`만 기록한다.
- **VERIFIED:** 다음 원본 메인 틱이
  `FUN_00611CD0 → FUN_006122C0(PortalMgr,2)`를 실행해 `gym.wmb`를 로드하고
  자연 경로와 동일한 C→S `0x0065` payload
  `08 15 15 02 00 00 85 05 00 00`를 보낸다.
- **VERIFIED:** 실제 결과는 서버 `room_kind=8`, 클라이언트
  `scene=0x66 / phase=2 / dispatch_mode=0`, 원본 Gym 안내 화면이다.
- **VERIFIED:** 같은 실행에서 팔굽혀펴기와 줄넘기를 원본 화면 버튼으로 완료했다.
  stat31은 `0→7`, stat33은 `0→5`, 기존 stat32는 `16`을 유지했고 각 완료 직후
  196바이트 C→S `0x0007` 저장이 한 번씩 발생했다.
- **VERIFIED:** 최종 공통 스탯
  `(stat3,4,5,6,7,9)=(3,41,50,100,0,30)`과 Gym 스킬
  `(stat31,32,33)=(7,16,5)`는 사전 정적 계산과 정확히 일치한다.

## 1. 화면 좌표가 아닌 원본 portal commit

정적 분석에서 Plaza 객체와 portal subsystem 관계를 다음과 같이 확정했다.

```text
GameManager                 = gm
CPlazaManager               = gm + 0x348F9
PortalMgr                   = gm + 0x348F9 + 0xDB0
                            = gm + 0x356A9
pending selector            = PortalMgr + 0x314
Gym selector/local index    = 2
portal commit thunk         = 0x004DBD99 -> FUN_006142C0
```

자연 mouse-release 경로도 정확히 같은 setter를 호출한다.

```text
FUN_00613C60 mouse release
  -> FUN_006142C0(PortalMgr, selected_key)
  -> [PortalMgr+0x314] = selected_key

next Hansol_PerFrameUpdate
  -> FUN_00611CD0(PortalMgr)
  -> pending 2 consume
  -> FUN_006122C0(PortalMgr, 2)
```

`FUN_006122C0` 내부에서만 좌표 회수, local loader, 원격 actor/UI 정리,
direction 계산, C→S `0x0065`, 후속 phase 정리가 모두 연결된다. 따라서
`FUN_0050A7F0(0x66)`, `FUN_0050B400(0x66)`, `FUN_00530FE0(2)`,
`FUN_005AB760(...)` 중 하나만 단독 호출하는 방식은 원본 전환의 일부를 빠뜨린다.

## 2. Gym descriptor와 두 좌표의 구분

`FUN_00610B90`이 등록한 Gym descriptor는 다음과 같다.

```text
model       GYM_3.MDL
selector    2
hit rect    (0xD5,0x835,0x2BD,0x605)
entry       (0x215,0x585) = (533,1413)
six-vector  (193,1801,-30,298,2111,250)
```

사용자가 화면에서 Gym 앞에 직접 둔 직후 서버가 실측한 self C→S 이동 좌표는
`(521,1741)`이었다. 이것은 **현재 avatar의 실제 문 앞 위치**다. 반면
`(533,1413)`은 Gym descriptor에 저장된 **방 전환 entry/report 좌표**이며,
`FUN_006122C0`이 C→S `0x0065`에 넣는 값이다. 두 값을 같은 “Gym 앞 좌표”로
부르면 안 된다.

## 3. 안전장치와 실제 직접 전환

`tools/azrok_input_hook.js`의 `queuegym(gm)` RPC는 다음 조건만 허용한다.

```text
phase gm+0x31792 == 4
PortalMgr vtable != NULL
PortalMgr+0x314 == -1
selector == hard-coded 2
```

주소나 selector를 외부 입력으로 임의 지정할 수 없고, 프로세스 PID와 시작 시각,
workspace 실행파일, 결과 경로는 기존 elevated request 경계가 다시 검증한다.

실제 실행 결과:

```text
05:59:19 C→S #246 opcode 0x0065
payload = 08 15 15 02 00 00 85 05 00 00
server  = room_kind 8, x 533, y 1413
client  = scene 0x66, phase 2, dispatch_mode 0
```

화면 `gym_direct_portal_queue_success_20260718.bmp`에는 원본 Gym 실내와
“어서와라~ 어서 운동을 시작해 보자구~!” 안내가 직접 표시됐다.

첫 도구 실행은 selector commit 자체는 약 3초 안에 성공했지만 Frida 세션을
12초 settle 동안 유지해 진단 helper가 종료 대기 상태에 남았다. 관련 helper만
정리했고 client PID `80208`은 계속 `Responding=True`로 유지됐다. 코드는 selector
commit 결과를 받은 즉시 `session.detach()`한 뒤 별도로 settle하도록 교정했다.
이 교정된 즉시-detach 형태도 `06:19:09`에 다시 실행했다. 명령은 9초 안에
종료되고 Frida 잔존 프로세스가 없었으며, 새 C→S `0x0065`와 서버
`room_kind=8`, 클라이언트 `scene=0x66 / phase=2`, 원본 Gym 안내 화면이 다시
나왔다. 따라서 **교정된 즉시-detach 반복도 VERIFIED**다.

## 4. 팔굽혀펴기와 줄넘기 실제 플레이

Gym 안내 feather를 진행한 뒤 원본 3종 선택 링이 열렸다. 화면 좌표를 정확히
누른 실제 이벤트 관측은 다음과 같다.

```text
아령         visible ring event: ButtonQueue id 0x5C, param2=1
팔굽혀펴기 visible ring event: ButtonQueue id 0x5D, param2=1
줄넘기     visible ring event: ButtonQueue id 0x5E, param2=1
```

이 `0x5D/0x5E`는 정적 문서의 Gym popup/action code `0x41/0x43`과 같은 숫자층이
아니다. 전자는 보이는 선택 링의 UI event이고, 후자는 Gym 결과/콘텐츠 상태머신
식별자다.

팔굽혀펴기 완료 저장:

```text
C→S #286 opcode 0x0007 payload 196B
stat31=7, stat32=16, stat33=0
(stat3,4,5,6,7,9)=(17,49,55,100,0,35)
save sum=23, calculated=23
```

줄넘기 완료 저장:

```text
C→S #293 opcode 0x0007 payload 196B
stat31=7, stat32=16, stat33=5
(stat3,4,5,6,7,9)=(3,41,50,100,0,30)
save sum=28, calculated=28
```

두 결과 모두 서버의 `content_save_count`를 `0→1→2`로 증가시켰고
`profile_playable_v2/506c61796572_c2s0007.bin`에 마지막 상태를 저장했다.

후속 직접 이벤트 A/B에서 오래된 문서의 “Gym exit=0x5C”를 재검증했다.
`0x005DB4D4`에 `0x5C`를 전달하자 출구가 아니라 아령이 실행되어 stat32가
`16→21`, `content_save_count 2→3`, 196바이트 C→S `0x0007`로 즉시 저장됐다.
따라서 `0x5C=아령`, `0x5D=팔굽혀펴기`, `0x5E=줄넘기`, `0x1AA=나가기`가
정적·동적 증거가 일치하는 현행 매핑이다.

## 5. Gym 나가기 정지와 Plaza 복귀 경계

**VERIFIED:** Gym의 보이는 `나가기`는 `FUN_005DB1E0`이 등록하는
`Data\\OutMap\\Out*.wis` 버튼이며 실제 event는 `0x1AA`다. 처리 경로는
`FUN_005DB4A0`의 `0x005DB89B` branch에서 cleanup 후
`Plaza_TransitionFromRoom@0x00568770`을 호출하고, 이것이
`GameManager_EnqueueRoomCode(0x6E)@0x0050A7F0`으로 Plaza scene request를
기록한다. 로딩 카드의 “아이템상점” 문구는 랜덤 Plaza 팁 아트워크일 뿐 Shop
전환의 증거가 아니다.

실제 클릭에서는 `scene_opcode=0x6E`, `phase=2`, 이전 room code `0x66`인 채
20초 이상 로딩 카드가 유지됐고 새 C→S `0x0064`가 없었다. 이는 정상이라면
약 3 frame에 `100→104→108`로 진행한 뒤 `FUN_0050A880`에 도달해야 하는
loading callback이 실행되지 않은 것이다. 정적 경로상 1차 판별 필드는
`gm+0x31946`; 이 값이 0이면 `GameManager_PerFrameUpdate@0x00509200`가 로딩
progress callback 자체를 호출하지 않는다.

**VERIFIED:** 이 정지 상태에서 서버가 S→C `0x000D[00]`를 한 번 보내자 5개의
S→C `0x0004[01]` calibration, 새 C→S `0x0064`, S→C `0x0064` 응답이 이어졌고
클라이언트는 `scene=0x6E / phase=4 / dispatch_mode=1`, 서버
`room_kind=27`의 건강한 Plaza로 복귀했다.

**INFERRED:** 원본 전환을 더 좁게 보존하는 복구는 `gm+0x31946==0`을 확인한
뒤 생성자 원래값 `0xFFFFFFFF`를 런타임 1회 복원하여 원본 per-frame callback과
ButtonQueue `0x0B`를 진행시키고, 그 다음에 calibration을 공급하는 방식이다.
이 gate 복원 형태는 아직 동적 실측 전이다.

## 6. 전체 Plaza portal descriptor 안전 allowlist

`FUN_00610B90`의 14개 slot과 `FUN_00530FE0`/`FUN_006122C0`을 함께
디컴파일한 결과, 일반 portal commit에 허용 가능한 selector는 다음 8개다.

| selector | room | WMB | wire kind | entry |
|---:|---|---|---:|---:|
| 0 | pathouse | `room.wmb` | 1 | `(626,4216)` |
| 1 | playroom | `playroom.wmb` | 6 | `(-3762,-3920)` |
| 2 | gym | `gym.wmb` | 8 | `(533,1413)` |
| 3 | magic | `magic.wmb` | 9 | `(2129,1034)` |
| 4 | cook | `cook.wmb` | 7 | `(-3707,-2817)` |
| 5 | shop | `shop.wmb` | 11 | `(-2058,-671)` |
| 6 | library | `library_1.wmb` | 10 | `(-1806,567)` |
| 10 | ground | `ground.wmb` | 12 | `(-2879,2923)` |

**VERIFIED:** selector `7,8,11`은 descriptor도 room-code switch도 초기화되지 않아
금지해야 한다. selector `9`는 pet mapper만 있고 자연 descriptor가 없으며,
`13`은 selector 13이 아니라 slot 13에 복제된 selector 0의 두 번째 hit geometry다.
selector `12`는 유효한 `GATE.MDL` descriptor지만 OX 전용 special handshake라
일반 room queue에서 분리한다. 도구의 generic allowlist도 정확히
`{0,1,2,3,4,5,6,10}`으로 제한했다.

## 증거

- `captures/packets_20260718_052925.txt` — #246 direct Gym `0x0065`,
  #286 pushup save, #293 rope save
- `artifacts/dynamic-analysis/plaza_user_exact_gym_front_521_1741_20260718.bmp`
- `artifacts/dynamic-analysis/gym_direct_portal_queue_success_20260718.bmp`
- `artifacts/dynamic-analysis/gym_direct_portal_queue_immediate_detach_20260718.bmp`
- `artifacts/dynamic-analysis/gym_exit_to_plaza_20260718.bmp`
- `artifacts/dynamic-analysis/gym_exit_000d_recovery_20260718.bmp`
- `artifacts/dynamic-analysis/gym_pushup_popup_after_exact_click_20260718.bmp`
- `artifacts/dynamic-analysis/gym_rope_result_20260718.bmp`
- `tools/azrok_input_hook.js`
- `tools/azrok_frida_input.py`
- `tools/stop_azrok_elevated.ps1`
- `tools/invoke_azrok_frida_elevated.ps1`
