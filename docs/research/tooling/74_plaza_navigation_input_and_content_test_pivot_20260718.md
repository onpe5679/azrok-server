# Plaza navigation input and content-test pivot (2026-07-18)

## 1. 조사 목적

Plaza에서 Gym까지 실제 사용자가 이동할 수 있는 입력 경로를 확인하되,
현재 복원 목표인 각 방·미니게임 내부 콘텐츠와 서버 계약 검증을 지연시키지
않도록 탐색 방법을 정리한다.

## 2. Plaza 미니맵과 WMB 지도

- **VERIFIED (화면 실측):** Plaza 오른쪽 위에 고정 미니맵이 렌더된다.
  `artifacts/dynamic-analysis/after_user_accidental_touch_plaza_20260718.bmp`와
  확대본 `plaza_minimap_zoom_20260718.png`에 보존했다.
- **VERIFIED (파일 파싱):** `Data/Space/Plaza/hansol.wmb`를 기존 WMB6
  파서로 읽어 `artifacts/minimap/plaza/hansol_minimap.{json,csv,svg}`를
  생성했다. WMB model `gym_MDL_066 / gym_3.MDL`의 배치 좌표는
  `(-839,-628,-28.176)`이다.
- **VERIFIED (디컴파일):** Plaza portal descriptor가 exact
  `GYM_3.MDL`을 비교해 selector `2`를 반환한다. portal commit 뒤
  Gym 진입 위치로 기록되는 `(533,1413)`은 WMB mesh 배치 좌표와 같지 않다.
- **주의:** 미니맵 아이콘의 외형만으로 건물 identity를 단정하지 않는다.
  이번 실행에서 미니맵 아이콘 클릭은 별도 경로 안내 UI를 열지 않았고,
  아래 월드 클릭으로 전달되어 캐릭터가 이동했다.

## 3. Plaza 입력 경로

- **VERIFIED (디컴파일):** `GameManager` input snapshot
  `FUN_00508FA0 -> FUN_005097F0` 뒤 Plaza scene은
  `FUN_00613C60`을 호출한다. `[ESP+8] == 0x80`인 DirectInput 좌클릭이
  주 click-to-move 입력이다.
- **VERIFIED (디컴파일):** click latch는 `0x00613E1A`, 실제 이동 호출은
  `0x00613F45 -> FUN_0061B510`이다. `[Hansol+8]+0x24C3`이 1이면
  modal 입력 경로로 빠지고 일반 이동이 차단된다.
- **VERIFIED (동적):** `click_rel_msg`의 `PostMessage`만으로는 Plaza
  이동이 일어나지 않았다. 실제 `SendInput`을 쓰는 `click_rel`은 채팅
  focus를 정리한 뒤 이동했다.
- **VERIFIED (동적):** `plaza_after_esc_hold_20260718.bmp`에서 채팅 패널이
  닫힌 뒤 `click_rel(0.28,0.30)`은
  `plaza_to_gym_after_chat_closed1_20260718.bmp` 위치로 이동했고,
  다음 왼쪽 클릭은 `plaza_to_gym_left_path2_20260718.bmp`의 OX 입구
  근처까지 이동했다. 따라서 DirectInput click-to-move 자체는 정상이다.
- **VERIFIED (도구 한계):** 현재 Frida `worldInputFrame` 관측 주소
  `0x00532980`은 PatHouse scene 2용이다. Plaza 입력 관측은
  `0x00613C60`에 별도 훅/브레이크포인트를 사용해야 한다.

## 4. 채팅 패널 복구

- **VERIFIED (디컴파일):** Enter는 채팅 submit 후 panel-open 플래그
  `gm+0x31C75`를 닫지 않는다. 실제 종료는 ESC release branch
  `0x0050DDA0..0x0050DDE4`이며 `+0x31C75=0`, `+0x31C76=1`로 만든다.
- **VERIFIED (동적):** 즉시 down/up 하는 기존 키 도구의 ESC는 이번
  실행에서 패널을 닫지 못했다. 180ms ESC hold 뒤
  `plaza_after_esc_hold_20260718.bmp`에서 패널이 사라졌다.
- **구현:** `tools/auto_azrok_ui.py`에 bounded `key-hold`,
  `tools/stop_azrok_elevated.ps1` 요청 계약에 `key_hold`를 추가했다.
  허용 키는 기존 allowlist, hold는 20..2000ms로 제한한다.
- **정정:** 채팅 panel-open 자체는 전역 이동 차단으로 단정하지 않는다.
  채팅 text subsystem은 고정된 하단 UI 사각형 안 클릭만 소비하며,
  전역 modal lock은 별도 `+0x24C3`이다.

## 5. 현재 탐색 전략 변경

- **VERIFIED:** 실제 PatHouse far-left 외부문은 자연 클릭으로
  `C2S 0x0019 -> S2C 0x000D -> C2S/S2C 0x0064`를 발생시켜 Plaza에
  진입했다. `true_far_left_exit_plaza_success_20260718.bmp`와
  `captures/packets_20260718_041857.txt` seq 172/179에 보존했다.
- **VERIFIED (정적):** Gym 문은 `GYM_3.MDL -> selector 2 ->
  FUN_006142C0(2) -> FUN_006122C0(2)`로 자연 진입한다.
- **결정:** 전체 이동 자동화의 완성은 후순위로 둔다. 방·미니게임 콘텐츠
  복원 실험에서는 서버/테스트 제어로 self actor를 목표 문 앞에 배치한 뒤,
  마지막 문 클릭·portal commit·방 로드·콘텐츠 action·저장은 원본 자연
  경로로 검증한다.
- **제약:** self 재배치는 호환성 분석용 최소 서버 동작으로 한정하고,
  바이너리 패치나 완성 판정의 대체 근거로 사용하지 않는다.

## 6. 남은 직접 검증

1. **NOT VERIFIED:** self에게 적용되는 최소 위치 재배치 S2C packet/function.
   `S2C 0x0066/0x0068`은 self 무시 가능성을 먼저 직접 확인한다.
2. **NOT VERIFIED:** 재배치 뒤 실제 `GYM_3.MDL` 클릭에서
   `0x00611F97 EAX==2`, commit, Gym room load를 한 실행에서 묶어 확인한다.
3. **NOT VERIFIED:** Plaza용 `0x00613C60` 관측 훅을 도구에 추가해
   UI 소비, modal lock, latch, movement call을 한 번에 기록한다.

