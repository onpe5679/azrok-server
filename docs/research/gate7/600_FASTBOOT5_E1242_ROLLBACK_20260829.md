# 600 — fastboot5 E1242/INT99 회귀와 fastboot4 롤백 (2026-08-29)

## 증상

- 모바일은 부팅 약 56초에 BoxedWine fatal 창을 표시했다. 저해상도 원본과 소스
  문자열 대조상 `Uknown int 99 call: 2897`과 일치한다.
- 데스크톱은 `Error E1242: Can't open video device. Try -W3D command line
  option.`을 명확히 표시했다.
- fastboot5 페이지/런타임/WASM 요청 뒤 운영 core/bridge에는 WS accept,
  TCP connect, login, heartbeat가 모두 0건이었다. 서버 접속 전 실패다.

## VERIFIED — fastboot5 패키징 회귀

- fastboot4와 fastboot5의 ZIP 4,269개 member 중 다른 파일은 `d3d9.dll` 하나다.
- fastboot4의 24,576-byte DLL은 기존 rsdefaults1 production
  `d3d9_web.guesttexrecycle1.dll`과 동일하다.
- fastboot5의 23,040-byte DLL은 일반 `build.bat` 산출물과 동일하다. production의
  `D3D9WEB_TRANSIENT_TEXTURE_RECYCLE=1` 변형을 유지하지 않은 잘못된 계보다.
- 두 PE의 x86/export/import 기본 계약은 정상이라 PE 형식 실패로 단정하지 않는다.
  잘못된 variant 교체와 E1242/INT99의 정확한 내부 stack 귀속은 NOT VERIFIED다.

## VERIFIED — 롤백

- 신규 캐릭터 name-only legacy snapshot 차단 서버 수정은 유지했다.
- guest Reset seed와 host INIT Map/colorMask 변경을 모두 철회했다.
- 홈페이지·서버 선택·로그아웃 재진입의 current app을 검증된 fastboot4로 복구했다.
- fastboot5 URL은 fastboot4로 승격하며, 서버 선택 JS를 `restore10`으로 올려 기존
  immutable `restore9` 캐시를 우회했다.
- 잘못 만든 fastboot5는 public apps 경로에서 제거하고 로컬/운영 quarantine으로
  이동했다. 재생성 builder와 불충분한 MZ-only 테스트도 제거했다.
- 공개 server list가 `restore10`, launcher가 fastboot4, runtime page가
  current fastboot4 + retired fastboot5임을 확인했다. fastboot4 Range 206,
  홈페이지 200, 4서비스 active, 운영 warning 0건이다.
- 전체 tools suite **295 tests PASS**.
- 계정/서버 상태를 쓰지 않는 공개 fastboot4 격리 프로브를 실제 Chrome에서
  56초 이상 실행했고 `D3D9WEB_FIRST_PRESENT presents=4`까지 도달했다.
  같은 시점의 브라우저 console error/warning은 0건이어서 E1242 발생 구간의
  D3D 첫 프레임 복구는 VERIFIED다.

## 보존된 수정

- #599에서 직접 재현한 신규 `Azrok1`/`Player` 이름의 cross-account legacy
  snapshot 침범 차단은 fastboot4와 독립적인 서버 수정이므로 운영에 유지한다.
- 로그아웃 뒤 base startersplash1 404를 만들던 재진입 경로도 current fastboot4
  root/runtime/JIT 조합으로 유지한다.

## NOT VERIFIED

- 롤백 뒤 제보 모바일·데스크톱의 실제 account-bound 세션에서 E1242/INT99가
  사라지고 PatHouse 3D까지 도달하는 최종 사용자 수용.
- Reset stale-state 방어의 올바른 production-variant 재구현. 다시 시도하려면
  일반 `build.bat`가 아니라 guest texture recycle 빌드와 실제 브라우저 A/B가 필요하다.
