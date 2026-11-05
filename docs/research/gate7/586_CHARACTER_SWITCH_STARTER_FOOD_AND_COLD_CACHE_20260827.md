# 586. Character switch, starter food, and cold cache (2026-08-27)

> **RUNTIME REGRESSION FIXED by 594.** 이 문서의 동일-root 선행 캐시 설계는 유효하지만,
> 이후 `azrok_launch.js`가 구 root로 회귀해 빈 origin에서 159.43 MiB를 중복 수신했다.
> #594가 선행 캐시와 실행 URL을 다시 같은 `xim25koreanlocale2` root로 고정했다.

> **STARTER-FOOD CLAIM SUPERSEDED by 642.** 이 문서가 `food1001`/slot 1을
> 이유식으로 잘못 명명했습니다. 직접 파싱한 Azrok.dat 기준 이유식은 ID 1000/slot 0,
> ID 1001/slot 1은 햄버거입니다. 캐시·로그아웃 결론은 영향을 받지 않습니다.

## Scope

게임 내부 `옵션 → 로그아웃`을 웹 서버 선택 화면이 아니라 원본 캐릭터 선택 화면으로
연결하고, 신규 캐릭터의 첫 이유식 퀘스트에 필요한 이유식 1개를 지급한다. 다른
브라우저·origin의 긴 최초 부팅과 반복 부팅을 분리해 측정하고 안전한 캐시를 적용한다.

## VERIFIED — 원본 로그아웃 계약과 캐릭터 전환 설계

- 원본 옵션 메뉴에서 `로그아웃`을 눌러 `C2S 0007 → C2S 0002 → S2C 0002 →
  C2S 0007 → C2S 0001 → S2C 0001[00]` 및 클라이언트 종료를 라이브 관측했다.
- 명시적 로그아웃 때 서버는 계정 roster/canonical을 지우지 않고 캐릭터 session lease,
  actor, room만 해제한다.
- 서버는 account raw id를 cross-connection latch에 1회 넣는다. 같은 계정의 다음 로그인은
  `auto_select_existing_sent=True`로 시작해 브라우저용 자동 선택을 1회 억제한다.
- 웹 실행기는 clean exit 또는 이미 열렸던 게임 WebSocket close를 감지하면
  `/api/private-session`에서 새 account-bound ticket을 발급받고 같은 실행 페이지를
  `characterSelect=1`로 다시 연다. 티켓 실패 때만 서버 선택 화면으로 폴백한다.
- 라이브 실행 중 게임 socket을 종료한 뒤 7초 안에 브라우저 URL이 새 account-bound
  ticket과 `characterSelect=1`을 포함한 실행 URL로 바뀌고, 새 클라이언트의 부팅 오버레이가
  다시 나타나는 것까지 직접 확인했다.
- cross-connection 단위 테스트는 로그아웃 계정만 다음 자동 선택이 억제되고 다른 계정은
  영향을 받지 않음을 검증했다.

## VERIFIED — 신규 캐릭터 이유식

- item registry의 `food1001`은 food quantity array index 1이다.
- 신규 canonical 생성 시 서버 지급분을 `SERVER_GRANTED_STARTER_ITEMS={'food': (1,)}`로
  분리하고 `food[1]=1`을 기록한다. 클라이언트 기본 장비/활성 loadout에는 넣지 않는다.
- 신규 상태에서 생성한 실제 zone payload의 `S2C 0007[0x0EA+1]`이 1임을 테스트했다.
- 수정 전부터 존재한 캐릭터에는 소모 여부를 알 수 없으므로 소급 지급하지 않는다.

## VERIFIED — 신규 브라우저 PatHouse

- 원본 클라이언트의 신규 캐릭터 경로에서 한솔 로고, 캐릭터 선택, PatHouse 3D,
  baby BlueRon, HUD, `이유식을 먹여보자` 퀘스트 UI를 라이브 확인했다.
- 따라서 신규 상태의 packed date 0 튜토리얼 경로가 PatHouse 3D까지 진입하는 것은
  현재 배포 코드에서 확인됐다.

## VERIFIED — 캐시 구현과 실측 경계

- 실행 전 앱 ZIP(157,274,502 B), root ZIP(167,825,891 B), grouped JIT archive를
  Cache Storage `azrok-runtime-archives-v1`에 미리 저장한다.
- BoxedWine `loadFile`도 같은 캐시를 먼저 조회하고 miss만 네트워크 fetch 후 저장한다.
- HTTP 서버 클래스에 중복 정의된 `end_headers()` 때문에 처음 구현한 캐시 헤더가 실제로
  덮어써졌음을 HEAD 실측으로 찾았다. 두 정의를 합쳐 HTML/API는 `no-store`, ZIP/WASM/JS와
  정적 미디어는 `public, max-age=31536000, immutable`이 되게 수정했다. 재시작 뒤 앱 ZIP
  HEAD 응답에서 해당 값과 `Content-Length: 157274502`, HTML에서 `no-store`를 재확인했다.
- 별도 `127.0.0.1` origin의 빈 캐시 첫 실행은 실제 첫 D3D draw까지 약 130초였다.
  이미 아카이브가 저장된 `localhost` 반복 실행은 첫 D3D draw까지 약 50~55초였다.
- origin(`localhost`, `127.0.0.1`, LAN, Tailscale)이 바뀌면 브라우저 캐시는 공유되지 않는다.

## NOT VERIFIED / remaining boundary

- 이번 브라우저 자동화의 반복 좌표 입력 중 BoxedWine JIT가 `unwind`를 보고해 마지막
  `옵션 → 로그아웃` 뒤 재부팅된 원본 클라이언트의 최종 4슬롯 GUI까지 같은 자동화
  세션에서 캡처하지는 못했다. 새 ticket/`characterSelect=1` 재실행과 부팅 시작은 라이브
  VERIFIED이고, 다음 연결의 auto-select 억제는 cross-connection 계약 테스트 VERIFIED이다.
- 영구 캐시는 약 325 MB의 재다운로드를 제거하지만 ZIP 해제, grouped JIT replay, Wine과
  원본 엔진 초기화까지 제거하지 않는다. 따라서 반복 실행도 현재 약 50초이며 즉시 부팅은
  아니다. 더 줄이려면 slim root/app 아카이브 또는 추출된 파일시스템 영속화가 필요하다.

## Automated verification

- `tools.test_server_contract_layers`, `tools.test_azrok_home_contract`,
  `tools.test_d3d9web_page_contract`: 147 tests pass.
- `.tmp_pydeps`의 기존 `websockets` 의존성을 포함한 전체 `tools/test_*.py`: 278 tests pass.
- Node syntax: `azrok_launch.js`, `boxedwine-shell.js` pass.
