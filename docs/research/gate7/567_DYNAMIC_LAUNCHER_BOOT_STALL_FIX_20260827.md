# 567. Dynamic account launcher boot-stall fix (2026-08-27)

## 증상과 경계

- **VERIFIED:** 신규 기기는 `dynamicaccounts1` 앱, `run_azrok_account.bat`,
  정상 v2 ticket 및 계정 인자를 받았고 JS/WASM/app/root 자산도 HTTP 200으로
  내려받았습니다.
- **VERIFIED:** 같은 시점 WSS bridge에는 accept/reject가 전혀 없고 core/GUI의
  client 및 packet 수도 0이었습니다. 따라서 정지는 계정 서버 응답 이후,
  원본 클라이언트의 첫 WSS 접속 이전입니다.
- 선택적 app JIT module 및 source-map 404는 기존 fallback 경로이며 직접 원인이
  아닙니다.

## 근본 원인

- **VERIFIED (source + deployed ZIP):** `dynamicaccounts1`의 첫 명령은
  `findstr /r /x "[A-Za-z0-9_][A-Za-z0-9_]*"` 실패 시 `exit /b 87`입니다.
- **VERIFIED (Wine 11 source):** 포함된 Wine `findstr`는 `/X`를 구현하지 않고
  문자 클래스 범위도 구현하지 않습니다. 따라서 정상 계정
  `adCqFPNGR_0jT`도 매치되지 않으며 `Azrok.exe`에 도달하지 않습니다.
- **VERIFIED:** BoxedWine의 `args` 전달은 landing URL에서 shell parser를 거쳐
  `/bin/wine cmd /c run_azrok_account.bat <account>` 단일 인자로 정상 전달됩니다.
  `CR CR LF`도 Wine cmd가 제거하므로 직접 원인은 아니지만 표준화했습니다.
- `@echo off` 뒤 즉시 종료되므로 UI가 마지막 단계인 "원본 Azrok 클라이언트
  부팅 중"에 고착되고 guest console 및 WSS 기록이 비는 관측과 일치합니다.

## 수정

- 새 불변 앱
  `Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts2.zip`
  을 생성했습니다. 원본 utf8ime2의 모든 엔트리는 byte-identical이며 새 launcher
  하나만 추가됩니다.
- Wine 비호환 `findstr`를 제거했습니다. 빈 인자만 batch에서 거부하고,
  `run_azrok_account.bat` 실행 직전 페이지가
  `/^[A-Za-z0-9_]{3,13}$/`로 fail-closed 검증합니다. 발급 서버와 WSS 첫 로그인도
  같은 계정 경계를 독립 검증합니다.
- launcher 줄바꿈을 기존 정상 launcher와 같은 표준 CRLF로 바꿨습니다.
- 사설 landing은 `dynamicaccounts2`와 `autorun=1`을 전달합니다. `autorun`은
  기존 runtime stem을 바꾸지 않고 준비 완료 직후 `startAzrok()`만 호출합니다.
  구형 `pathouseav` 진단 표식과는 분리했습니다.

## 라이브 검증

- **VERIFIED:** 새 브라우저 ID에 신규 계정 `a9E9x1IbVKDOQ`와 v2 ticket을 발급한
  뒤 실제 in-app browser에서 `dynamicaccounts2&autorun=1`을 열었습니다.
- **VERIFIED:** 자동으로 JIT/guest 준비가 시작되었고 WSS bridge가 accept한 뒤
  `TCP_CONNECTED ... account=a9E9x1IbVKDOQ`를 기록했습니다.
- **VERIFIED:** 원본 클라이언트의 첫 `C2S 0x0000`, heartbeat `0x0016`, server
  lobby/calibration 응답이 왕복했습니다. 관제 실측은 `clients=1`, `rx=3`,
  `tx=4`, structured capture 7건입니다.
- **VERIFIED:** 전체 `python -m unittest discover -s tools -p 'test_*.py'`는
  254/254 통과했습니다. 계약은 dynamicaccounts2, Wine `findstr` 부재,
  표준 CRLF, 페이지 계정 정규식, landing autorun을 고정합니다.
- **VERIFIED:** 사설 landing 루트에서 기존 사용자 브라우저 binding(`player`)으로
  다시 진입시켜 `dynamicaccounts2&autorun=1` URL, WSS/TCP 연결, 원본 첫 화면을
  연속 확인했습니다. 캡처에는 원본 Azrok 단축키 안내 화면과 FPS 76.1이 표시되어
  부팅 진행 overlay를 실제로 벗어났습니다.
- **NOT VERIFIED:** 이번 수정 수락 범위에서 캐릭터 선택 이후 PatHouse/Plaza까지
  새로 조작하지는 않았습니다. 사용자가 이어서 플레이 시험합니다.
