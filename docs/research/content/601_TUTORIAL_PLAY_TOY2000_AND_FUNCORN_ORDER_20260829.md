# 601 — 튜토리얼 놀기 toy2000과 FunCorn 보상 순서 복구 (2026-08-29)

## 증상

- 신규 stage-0 PatHouse에서 퀘스트 `아즈론이랑 놀자`가 활성인데 아즈론을
  클릭한 원형 메뉴에는 용변/식사/목욕/수면만 보이고 놀기가 없었다.
- 앞의 튜토리얼 퀘스트를 세 번 완료해도 `콘 100증가`가 UI 소지금에 반영되지
  않았다.

## VERIFIED — 놀기 메뉴의 원본 gate

- 원본 `FUN_005A05B0(category=100)` stage0 분기는 기본 네 항목만 만들고,
  `FUN_0059C3D0(6) != -1`일 때만 `0x71` 놀기를 삽입한다.
- group6 association은 item `2000`이고 `FUN_0059C3D0`은 그 수량이 0이 아닌지
  검사한다. item2000은 Azrok.dat의 유아용 `딸랑이`다.
- 원본 신규 초기화 `FUN_0059A390`도 toy container에 `2000,1`을 직접 지급한다.
- `BtnPlay*.wis` control ID는 `0x36`; 클릭하면 submenu category `0x71`을 열고
  stage0에서는 `BabyToy` control `0x34`/action `0xE3`을 제공한다.
- 숨겨진 BtnPlay는 visible flag 0에서 hit-test도 실패하므로 보이지 않는 버튼을
  추측 클릭해 진행할 수 없다.
- 서버 canonical은 toy2001/2004/2007만 1이고 toy2000은 0이었다. authoritative
  S2C0007이 원본 local grant를 0으로 덮어쓴 것이 직접 원인이다.

## VERIFIED — 콘의 정체와 운영 보상 실패

- `콘`은 경험치가 아니라 유일 서버 통화 **FunCorn**, 즉 UI의 `소지금`이다.
- kind5 튜토리얼은 별도로 EXP(stat2)를 212/202/203/227/201 순서에서
  +40/+50/+60/+70/+80 올리고, 각 단계 FunCorn +100을 보고한다.
- 운영 18:52:59, 18:54:35, 18:55:00에 실제 자연 순서는 세 번 모두
  `0011 old-row retire -> 0012 [100,channel2] -> 0011 next-row -> 0007`이었다.
- 서버는 food quest에서 확인한 반대 순서 `0012 -> 0011 retire`만 허용해 세
  0012를 `no active runtime row`로 거부했다. S2C0005 subtype12 ACK는 0건,
  canonical currency는 0, completed rows는 0이었다. EXP는 50→105→170으로
  클라이언트 로컬 적용됐다.

## 수정

- 신규 canonical의 `SERVER_GRANTED_STARTER_ITEMS`에 `toy[0]=1`을 추가했다.
- kind5의 정확한 one-row retirement를 잠시 buffer하고 바로 다음 0012/100과
  row removal/FunCorn/completion을 한 durable transaction으로 commit한다.
  그 다음 0011 next-row 발행은 기존 경로로 저장한다. food quest의 기존
  `0012 -> 0011` 계약은 유지한다.
- 회귀 테스트는 `212 -> empty 0011 -> 0012/100 -> next 202 0011`과 즉시
  S2C0005 subtype12/balance100, food reward 기존 순서, fresh toy2000을 함께
  검증한다. 전체 **297 tests PASS**.

## 운영 복구

- 정확한 세 rejected tx와 revision/SHA/currency0/active aux227/toy2000=0을
  precondition으로 고정한 fail-closed recovery를 실행했다.
- canonical revision 13→14, FunCorn 0→300, toy2000 0→1,
  completed kind5 aux212/202/203 세 건을 한 transaction으로 기록했다.
- 배포 후 core/web/bridge/cloudflared 모두 active, warning 0, 공개 HTTPS 200,
  status API 200, WSS 101 및 무인증 차단을 확인했다.

## NOT VERIFIED

- 사용자가 재접속한 실제 모바일/데스크톱 화면에서 `놀기 -> 딸랑이`가 보이고
  aux227 완료 뒤 소지금 300→400 ACK가 표시되는 최종 수용.
