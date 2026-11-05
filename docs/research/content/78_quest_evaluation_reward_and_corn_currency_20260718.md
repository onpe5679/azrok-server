# 퀘스트 평가·보상 엔진 + 콘(corn) 통화 정체 (2026-07-18)

> **PARTIALLY SUPERSEDED by 86, 87, 123 and 126.** base callback no-op 자체는 맞지만 실제 파생 `CJSLogic`은 C→S0011/0012 sender로 override합니다. kind0 natural reward와 FunCorn ACK의 현행 계약은 126이 권위입니다. 101은 archive되었습니다.

정적 분석(Ghidra, `Azrok_original.exe`). 퀘스트 완료 평가기·보상 지급·보상통화 "콘"을 확정.
**콘 스텁(vtable+0x20=FUN_005949c0)은 Claude 본인 디스어셈블로 재검증**(순수 no-op 확인). 0x0007 저장 내부는
Codex 영역이라 얕게만. VERIFIED=디컴파일/디스어셈, INFERRED=추론.

## 1. 퀘스트 시스템 아키텍처 (VERIFIED)

- "퀘스트" = **런타임 10행 테이블**. S→C 0x0007 offset 0x134(kind)/0x148(aux)/0x15c(value)에서 import
  (`HandleS2C_0007_LoadSetupBlob`@0x0059e330, 행 import `FUN_005a5ab0`), `CLogicManager+0x70c`(stride 0xc:
  kind/aux/value)에 저장. 만료 = PackedDate now+200.
- 완료 행 제거 뒤 base callback `00594980`은 no-op이지만, 실제 파생 `CJSLogic`은 이 slot을 C→S0011 80B sender로 override합니다(123).
  C→S0007 196B 범위에도 `logic+0x70C` 퀘스트 행은 포함되지 않습니다.

## 2. 카탈로그 DAT_006dae98 = 순수 텍스트 (VERIFIED)

- 하드코딩 텍스트만: [2]title / [3]보상텍스트("콘 N증가") / dialogue. food·content id(0x3e9=1001+)로 색인.
- **조건·보상 수치는 카탈로그에 없고 코드 스위치테이블에 있음.** 그룹A(1001-1006 음식)="콘 40증가",
  그룹B(1007+)="콘 38증가". title = "OO 먹고 싶어요" 음식 위시(1001=핫도그, 1002=라면 …).

## 3. 완료 평가기 = FUN_005a6910(logic, kind, value) @0x005a6910 (VERIFIED)

매 액션 후 호출(`FUN_005a67a0` 액션로거 + `FUN_005a1b90` 미니게임 경유 — content/76 리워드엔진과 동일 훅).
10행 스캔 → (kind, aux/value) 일치 행 완료·제거·보상. **완료 조건 = "액션 매칭"이지 stat 임계값이 아님**
(내 초기 가정 "stat 임계 검사" 정정). kind별:
- **kind0** → `FUN_005a6ce0`(aux=food/content id 0x3e9-0x404): stat7 += 음수 + 콘(stub). 트리거=아이템사용 0xd4/0xdb
- **kind1** → `FUN_005a7240`(aux=스킬stat 0x1f-0x3e): **stat[aux] += 양수(+0x10 등) via FUN_005a4ba0**. 트리거=미니게임/스킬훈련
- **kind2** → `FUN_005a7910`(급식/food id): stat7 += 음수 + 콘(stub). 트리거=급식 0xcf / 운동 0xdc-0xe2
- **kind3** → `FUN_005a7e40`(level): **진화 +0x130 승격**(0→1, 1-3→2, 4-6→3) = "크고 싶어요 성장" 퀘스트. 성장상태 getter `FUN_005465c0`
- **kind5** → `FUN_005a8790`(코드): **EXP(stat2) += delta via FUN_005a4ba0(2,..)** + 콘(stub). 튜토리얼 체인(진화==0일 때만)

## ★ 4. 콘(corn) = 서버 권위 통화, 스탯 아님 (VERIFIED — 가설 반증)

세 보상함수 모두 콘 금액을 `logic->vtable[+0x20](amount, 2)`로 넘김. **vtable(0x006A618C)+0x20 = FUN_005949c0
= 순수 스텁** (Claude 디스어셈 재검증: `PUSH EBP; SUB ESP,0x44; … XOR AL,AL; … RET 0xc` — 0x44 프레임 잡고
아무것도 안 하고 0 반환). 인접 +0x28도 스텁 = **CLogicManager 가상메서드 스텁 클러스터**(서버 권위 작업의
클라측 no-op 훅; 미사용 0x44 프레임 = 원본은 실동작이었음 시사).
- **정합성**: `FUN_005a6ce0`의 amount가 카탈로그와 정확 일치 — food 1001→0x28(40)="콘40증가", food 1007→0x26(38)="콘38증가". → 이 함수들이 콘 보상 적용부 확정.
- **결론(가설 반증)**: 콘은 FUN_005a4ba0로 **어떤 lgc.tmp 스탯에도 안 써짐**. **콘 ≠ 봉에너지(stat9)** — content/65·71의
  "콘=봉에너지 유력(INFERRED)"을 REFUTED. 콘 ≠ stat7. **콘 = 서버측 통화**(스텁이 이 빌드에서 비활성 → 서버
  재구현이 콘 크레딧 담당, 클라는 0x0007 동기값으로 표시만).
- **소지금 model 위치 VERIFIED**: model `0x001911A9`, vtable `0x006A6478`, `model+0x1F0`.
  S→C0007 +7과 구매 ACK 0005 +2가 같은 setter로 들어가며 실제 구매 1000→950을 확인했습니다.
- **★ 콘 = 펀콘(FunCorn) = 소지금. 통화는 하나다 — VERIFIED (원본 심볼 전수 스윕)**
  근거는 2011년 하드 덤프에서 복원한 Naver 배포판 `Setup.zip` 내 `Azrok.ilk`(MSVC 증분 링크 파일)의 디맹글 심볼
  4,553개다. 덤프: `docs/research/_img2011_extracted/Program Files/Hansol/Azrok_Naver/_ilk_symbols.txt`
  - **잔액 접근자는 `FunCorn` 계열 하나뿐이다**: `CJSUser::{Add,Get,Set}FunCorn`, `CJSQuestList::AddFuncorn`,
    `CPopupPopcornInterface::{Get,Set}FunCorn`.
  - 명사 전수 스윕: `Gold`/`Cash`/`Coin`/`Balance`/`Wallet`/`Cost`/`Fee` **0건**. `Money` 2건은 **둘 다 표시 함수**
    (`CPopupItemShop::ViewMyMoney`, `::ViewBuyMoney`)이며 자체 잔액이 없다 → 읽어올 잔액은 `CJSUser::GetFunCorn()` 뿐.
  - → **`소지금`은 통화명이 아니라 "가진 돈"이라는 UI 라벨이고, 그 실체가 FunCorn(콘)이다.**
  - **결정타**: 위 §4 말미대로 `S→C 0x0007 +7`과 구매 ACK `0x0005 +2`가 **같은 setter**로 들어간다. 즉 0x0007이
    복원하는 통화 필드는 **하나뿐**이다. 콘이 별개 통화라면 재접속 시 복원할 두 번째 필드가 있어야 하는데 없다.
- **`0x0012` 계약(동적 실측)**: `[amount:u32][channel:u8]`. 퀘스트 보상 시 `[40, 2]` 관측.
  `vtable[+0x20](amount, 2)`의 상수 2와 일치하나, 이는 **통화 종류가 아니라 보상 채널 판별자**다
  (보상 3함수 FUN_005a6ce0/005a7240/005a7910이 전부 상수 2를 넘기고, 인접 vtable `+0x28`도 스텁 = 채널이 여럿
  설계됐던 흔적). → 서버는 `0x0012`를 **소지금(=FunCorn)에 그대로 입금**하고, channel은 필드로 보존하되 별도
  잔액을 파생시키지 않는다.
- **⚠ 2026-07-18 왕복 기록**: 한때 `G2C_FUNCORN_ACK` ≠ `G2C_PRICE_ACK`만 보고 "통화 2종"으로 오판했다.
  `AckPrice`는 지갑이 아니라 **가격 카탈로그**다(`CJSShop::{Set,Get,Reset}Price` 3종 세트). 구조체가 다르다는
  사실만으로 통화 분리를 단정하지 말 것 — **접근자 전수 스윕이 판정 근거다.**

## 5. FUN_005a4ba0 경유 실제 클라 스탯 보상 (VERIFIED)

- **stat2(EXP)**: kind5 튜토리얼, +40~80. 체인 테이블 DAT_006e0d80(212→202→203→227→201, 각 콘100).
- **stat7**: 음식퀘스트(kind0/2), 음수 -10~-30(need/조건 스탯, lgc.tmp명 x32dbg 필요 — 배고픔 추정).
- **스킬스탯**: kind1, 0x1f-0x27(gym/놀이/마술 31-39)·0x28-0x2c(요리 40-44)·0x31-0x35·0x3a-0x3e, +~16.
- **진화 +0x130**: kind3, 직접 write(스탯 아님).

## 6. 서버 evidence 정책 정정 (VERIFIED static, 구현 contract)

- kind1은 미니게임 정상 보상 뒤 `QuestEval(kind=1, resolved_skill_stat)`이 호출되지만, 일반 sys.tmp 행동도
  같은 stat을 올릴 수 있어 C→S0007 delta는 완료 provenance가 아닙니다. 또한 max clamp와 봉에너지 gate로
  퀘스트 보너스가 일부/전부 보이지 않을 수 있습니다. 따라서 delta 크기만으로 콘을 지급하지 않습니다.
- kind3은 aux `0→evo1`, `1..3→evo2`, `4..6→evo3`이며 commit writer의 실제 호출자가 평가기입니다.
  서버 발행 generation/행 index/발행 당시 stage와 exact monotonic stage edge를 결합하면 reconnect echo를
  제외할 수 있습니다. 가장 앞 행 하나만 retire하고 통화는 지급하지 않습니다.
- 완료 행과 snapshot baseline은 canonical JSON 한 commit에 저장하며 동일 generation replay를 거부합니다.
- exact bucket은 aux1(40/44/6/18..24), aux2(42/43 및 31+32+33), aux3(43/20/21),
  aux4(35/33/53 및 18..24), aux5(36/32/52 + canonical 쇼파/침대), aux6(34/31/51/7) 조건으로
  검증합니다. 같은 stage의 후보 선택은 원본 서버 입력이라 호환 route env(기본 1→4)로 명시했습니다.
- kind0/1/2/5는 C→S0012의 exact amount/channel2와 바로 뒤 C→S0011의 exact one-row retire를 결합해 server-visible provenance를 얻습니다. food1001 kind0은 126에서 natural live·구현·회귀까지 확인했고, 나머지 kind의 자연 표본은 NOT VERIFIED입니다.

## 확정 못한 것 (x32dbg — Codex 동적영역)

1. universal 완료 C→S 신호가 없으므로 kind0/1/2/5를 서버가 정확히 판정할 별도 evidence.
2. **stat7 lgc.tmp 이름**(음식퀘스트 need 스탯, 배고픔 추정).

주요 주소: FUN_005a6910(평가기)·FUN_005a6ce0/7240/7910/7e40/8790(kind0/1/2/3/5 보상)·FUN_005949c0(콘 스텁
vtable+0x20)·FUN_005a5ab0(0x0007 행 import)·FUN_005465c0(진화stage getter). 데이터: DAT_006dae98(텍스트카탈로그)·
DAT_006e0d80(kind5 콘/EXP 체인).

Related: [[content/76_minigame_reward_engine_and_bong_energy_gate]](FUN_005a1b90 훅·봉에너지 게이트), [[content/66_shop_item_economy_and_money_offset]](소지금 model+0x1F0),
[[content/71_azrok_dat_item_catalog]](콘=봉에너지 반증), [[content/65_action_stat_deltas_sys_lgc]](콘 가설 반증), protocol/75, INDEX.
