# 585. Fresh-browser PatHouse and logout completion (2026-08-27)

> **PARTIALLY SUPERSEDED by 586.** 로그아웃 뒤 서버 선택 화면으로 보내던 임시 웹 UX는
> #586의 새 티켓 재발급 + 캐릭터 선택 전용 재부팅으로 대체됐다. 신규 PatHouse 실측과
> 원본 로그아웃 패킷 순서 결론은 그대로 유효하다.

## Scope

다른 브라우저의 첫 캐릭터 생성 뒤 PatHouse 3D가 나오지 않는 회귀와, 게임 메뉴의
로그아웃 뒤 로딩 화면이 끝나지 않는 문제를 원본 클라이언트와 현재 브라우저 실행
경로에서 확인하고 최소 수정한다.

## VERIFIED — fresh character PatHouse regression and repair

- 신규 상태를 현재 날짜로 보내던 회귀에서는 캐릭터 생성 뒤 보라색 캐릭터 선택
  배경에 머물렀고 `C2S 0x0011` 및 원본 튜토리얼 진입 패킷이 나오지 않았다.
- `playable` 신규 캐릭터가 원본의 packed date 0을 다시 받도록 기본값을 복구했다.
  `AZROK_NATIVE_FRESH_TUTORIAL=0`만 명시적 진단 opt-out으로 남겼다.
- 수정하지 않은 원본 클라이언트로 신규 캐릭터 슬롯의 접속을 누른 뒤 PatHouse
  3D 방, baby Azron, HUD 및 퀘스트 UI를 실제로 확인했다.
- 같은 세션의 제어 API는 `room_kind=-1`, `room_name=PatHouse (local)`,
  transition `pathouse_stable`, `C2S 0x0011` 1회를 보고했다.

## VERIFIED — logout infinite loading

- 원본 메뉴 로그아웃에서 `C2S 0007 -> C2S 0002 -> S2C 0002 -> C2S 0007 ->
  C2S 0001` 순서를 실제 관측했다. canonical 상태와 계정 roster는 정상 보존됐다.
- 빈 `S2C 0002` 뒤 원본 클라이언트는 로딩/팁 화면에 머물렀다. 다음 heartbeat에
  계정 `S2C 0000` roster를 한 번 더 보내도 팁 이미지만 바뀌고 4슬롯 UI는
  나타나지 않았다. 따라서 #564의 same-process roster-return 가정은 기각한다.
- 제어 API로 `S2C 0001[00]`을 보냈을 때 원본 클라이언트 연결이 즉시 종료됐다.
  이는 해당 응답이 현재 클라이언트의 유효한 종료 경로라는 동적 근거다.

## Implementation

- 명시적 로그아웃의 마지막 빈 `C2S 0001`에 `S2C 0001[00]`을 응답한다.
- 보존 서버는 계정, 브라우저 바인딩, 4슬롯 roster, canonical 캐릭터 파일을
  삭제하지 않는다.
- D3D9Web 페이지는 BoxedWine의 clean `Module.onExit(0)`과, 실제 9201 게임
  WebSocket이 한 번 열린 뒤 닫히는 사건을 함께 감지해 서버 선택 화면으로
  돌아간다. 라이브 `S2C 0001[00]`에서는 게임 연결과 Present는 끝났지만 셸의
  `Module.onExit`이 호출되지 않았으므로 WebSocket close fallback이 필요했다.
  페이지 자체 이동 중 close는 `beforeunload` guard로 무시한다.
- 이는 원본 공식 웹페이지 동작이라고 단정하지 않는 보존용 UX다. 원본 클라이언트의
  확인된 종료 handler와 현재 웹 실행기의 재접속 구조를 연결한 것이다.

## VERIFIED — cold first load boundary

- 다른 origin의 첫 실행에서 grouped JIT replay 30,550 entries / 94 groups를
  등록한 뒤 Wine과 원본 앱이 시작됐다. WebGL2 FFP 초기화도 확인됐다.
- optional `<app>-jit-modules.zip` 404와 ScriptProcessorNode 경고 뒤에도 실제
  D3D 렌더가 시작됐으므로 두 메시지는 이번 멈춤의 원인이 아니다.
- `localhost`, `127.0.0.1`, LAN IP, Tailscale IP는 브라우저 저장소와 캐시가
  origin별로 분리된다. 첫 실행의 긴 대기는 네트워크 ZIP 다운로드만이 아니라
  브라우저별 JIT replay와 guest/Wine 시작 비용을 포함한다.

## Automated verification

- `tools.test_content_builders`, `tools.test_server_contract_layers`,
  `tools.test_azrok_home_contract`: 139 tests pass.
- 전체 tools suite와 clean-exit 브라우저 자동 복귀의 최종 실측은 아래 상태를 따른다.

## NOT VERIFIED

- 원본 공식 홈페이지가 로그아웃 때 정확히 어느 URL로 이동했는지.
- 전체 튜토리얼을 끝까지 진행한 뒤 Plaza까지 이어지는 신규 계정 전체 수락.
