# 원본 심볼 → Plaza 1.3.1 이식 (append-only)

대상:
- 심볼 출처: `_img2011_extracted/Program Files/Hansol/Azrok_Naver/_ilk_symbols.txt` (4,553 심볼 / 177 클래스 / 120 모듈)
- 심볼과 짝인 빌드: `_unpacked/Azrok.exe` **Ver. Jr. Naver 1.4**, 2,461,759 B
- **이식 목표 빌드**: `Azrok_original.exe` **Ver. PLAZA 1.3.1**, 2,199,552 B

---

## [1] 방법 선택 — `.ilk` 주소 추출은 **포기했고, 그럴 필요가 없었다** — VERIFIED

### `.ilk` 에는 이름만 있고 주소 참조가 없다
- `Azrok.ilk` 헤더 = `"Microsoft Linker Database\n"` (VC6 링커, 임베드된 PE 헤더의 `0b 01`/`06 00` 확인).
- 맹글 이름 4,127개가 **널 구분 연속 문자열 영역** `0x26ef69..0x2cb3b9` 에 평평하게 저장돼 있다.
- 알려진 이름의 파일 오프셋(`?ShopBuyItem@CJSShop@@IAEHHH@Z` @ `0x2a75dd`)을 기준으로
  그 오프셋(및 여러 base 보정값)을 가리키는 u32 를 전수 검색 → **참조 0건.**
  → 이름 테이블이 주소와 오프셋으로 연결돼 있지 않다. VC6 .ilk 내부 인덱싱은 다른 구조다.
- `_ilk_symbols.txt` 자체에도 16진 주소가 **0건**.

### `.exp` / `.lib` 는 도움이 안 된다
`Azrok.exp`(COFF), `Azrok.lib`(`!<arch>`) 는 파싱했으나, Naver EXE 의 export 51개는
**전부 `eff_*` / `ptc_*` 파티클 스크립트 진입점**(`0x40150a`~`0x405c22`)이다.
C++ 메서드는 하나도 export 되지 않는다. 프로토콜 작업에 무가치. — VERIFIED

### ★ 방향 전환: Plaza 바이너리 자체가 실명을 갖고 있다
| 빌드 | RTTI 타입 디스크립터 | 그 중 `CJS*` |
|---|---|---|
| Naver 1.4 | 63 | **0** |
| **Plaza 1.3.1** | **235** | **15** |

**Naver 빌드는 게임 클래스 RTTI 가 없고(=`/GR-`), 우리 대상인 Plaza 빌드에는 있다.**
즉 "Naver 에 이름 붙이고 → Plaza 로 diff 이식" 이라는 원래 경로는 **불필요**하다.
Plaza 의 RTTI 를 직접 읽으면 클래스명이 바로 나온다. 크로스빌드 diff 의 오차를 통째로 회피한다.

**`.ilk` 의 역할은 「주소 공급원」이 아니라 「메서드 이름·시그니처 사전」이다.**

---

## [2] RTTI 파싱 — 1차 시도는 **틀렸고** 검증으로 잡았다 — VERIFIED

### 1차(폐기): 오탐이었다
`sig==0 && pTypeDescriptor ∈ 알려진TD` 만으로 COL 을 찾자
CJSShop/CJSMenu/CJSOutDoor/CJSStatus… 가 **완전히 동일한 슬롯 주소**를 갖고,
슬롯 값이 `0x004daee9` 처럼 **16바이트 정렬이 아니었다**. MSVC 함수 진입점은 정렬된다.
→ 함수 포인터가 아니라는 신호. 결론 보류하고 검증을 추가했다.

### 2차(채택): 전 체인 검증
```
TypeDescriptor.vfptr 일치성  →  COL  →  ClassHierarchyDescriptor(sig==0, 1≤numBases≤64)
                                     →  BaseClassArray 의 모든 항목이 유효한 BCD→TD 를 가리킬 것
```
결과: **type_info vftable `0x006b5968` 에 235/235 디스크립터가 전원 일치**,
검증 통과 COL **221개**, vftable 221개. 주소는 1차와 동일 → **vftable 자체는 진짜였다.**

### 비정렬 슬롯의 정체 = 증분 링크 점프 썽크 — VERIFIED
슬롯이 가리키는 곳의 바이트가 `E9 xx xx xx xx` (`jmp rel32`) 였다:
```
0x004d7fb4: e9 c7 c9 0b 00   JMP -> 0x00594980   (16B 정렬 ✓)
0x004daee9: e9 b2 9a 0b 00   JMP -> 0x005949a0   (16B 정렬 ✓)
0x004dc8d4: e9 e7 80 0b 00   JMP -> 0x005949c0   (16B 정렬 ✓)
```
`0x004d7000~0x004e2000` 은 **썽크 테이블**이다. 5바이트 간격이라 비정렬로 보였던 것.
썽크를 따라가면 전부 정렬된 실제 함수. 여러 클래스가 같은 슬롯 주소를 공유한 것도
**정상**이다 — 상속받은 가상함수를 오버라이드하지 않았다는 뜻.

**교훈**: Plaza 1.3.1 의 vtable 을 읽을 때는 반드시 썽크를 1단 해석해야 한다.
이 단계를 빼면 모든 주소가 40KB 썽크 영역에 뭉쳐 나오고 앵커와 하나도 안 맞는다.

---

## [3] 앵커 자가검증 — 2/13 적중, 나머지는 **비가상 함수** — VERIFIED

썽크 해석 후 13개 검증 앵커를 vtable 타깃 전체와 대조:

| 앵커 | 결과 |
|---|---|
| `0x005949c0` 콘 보상 스텁 | ★ **적중** — CJS 공통 베이스 **슬롯[2]**, 9개 클래스(`CJSCommand/Inventory/Marumong/Menu/OutDoor/Property/QuestList/Shop/Status`)가 공유 |
| `0x00591cd0` CClientPeer::OnConnect | ★ **적중** — **`.?AVCClientPeer@@` 슬롯[1]**. RTTI 가 클래스명을 독립 확증 |
| 나머지 11개 | vtable 타깃 아님 |

### 11개가 안 잡히는 것은 실패가 아니다 — 맹글링이 설명한다
`.ilk` 맹글 접미사가 가상 여부를 말해준다:
- `UAE` / `MAE` / `EAE` = **virtual** → vtable 에 나타남
- `QAE`(public) / `IAE`(protected) / `AAE`(private) = **비가상** → vtable 에 없음

예: `?ShopBuyItem@CJSShop@@IAEHHH@Z` = protected **비가상** `int CJSShop::ShopBuyItem(int,int)`.
따라서 `0x005a95b0`(구매 검증) 같은 앵커는 원래 vtable 에 있을 수 없다.
→ **vtable 슬롯 매칭은 가상함수 전용 기법**이며, 비가상 함수에는 다른 근거가 필요하다. — VERIFIED

**적중한 2건이 방법의 정당성을 입증한다**: 무작위로 맞출 확률이 없는 위치에서 맞았고,
특히 `CClientPeer` 는 문서 22 의 명명(`CClientPeer::OnConnect`)을 RTTI 가 **독립적으로 재확인**했다.

---

## [4] 클래스 목록 대조 — Plaza 는 Naver 의 구버전이 **아니다** — VERIFIED

| | 개수 |
|---|---|
| Plaza RTTI 단순 클래스 | 188 |
| `.ilk` 클래스 | 177 |
| **양쪽 공통** | **124** |
| Plaza 에만 | 64 |

### Plaza 에만 있는 클래스 — 앵커와 정확히 대응한다 ★
```
CConnection   CNetwork   TcpPeer   CLogicManager   CMultiGame
CGameOXQuiz   CGameOXQuizUI   CPopupOXQuestion  CPopupOXResult
CPopupOXTimer CPopupOXTitle   CPopupOXNPC
CPopupAccessory   CMountItem   CPlayerInfo   CItemInfo   CDataMgr
```

- `0x0061e340 CConnection::Connect` → **`CConnection` 클래스가 Plaza RTTI 에 실존** ✓
- `0x006069a0 S2C 0x00CE OX 질문` → **`CGameOXQuiz` 계열 6종 실존** ✓
- `0x005ab2b0 / 0x005b2cb0 액세서리` → **`CPopupAccessory` / `CMountItem` 실존** ✓

**결론: Plaza 1.3.1 은 Naver 1.4 에 없는 기능(OX퀴즈·액세서리·멀티플레이 Plaza)을 가진 별개 브랜치다.**
버전 번호가 낮다고 구버전이 아니다. 추가 증거:
- Plaza RTTI 에 `CStringT`/`StrTraitMFC`/ATL 템플릿 → **MFC7+ / VS2003 이상 툴체인**
- Naver 는 MFC42 + VC6 iostream → **VC6 툴체인**

→ **두 빌드는 툴체인이 다르다. 바이트 단위 함수 유사도 매칭은 신뢰할 수 없다.** — VERIFIED
   `EXACT` 등급을 바이트 일치로 부여하는 것은 이 쌍에서는 원칙적으로 불가능하다.

---

## [5] 구조체 ↔ 핸들러 — 심볼만으로 42쌍 확정 — VERIFIED

주소 없이도 확정 가능한 부분이다. 맹글 이름 자체가 인자 타입을 담고 있다.
`_ilk_symbols.txt` 에서 `C2G_`/`G2C_`/`S2C_` 를 포함한 심볼 **전수 42개**:

```
?AckCreateEgg@CJSLogic@@IAEXPAUG2C_CREATEEGG_ACK@@@Z
?AckFunCorn@CJSLogic@@QAEXPAUG2C_FUNCORN_ACK@@@Z
?AckLevelUpBasis@CJSLogic@@QAEXPAUG2C_LEVELUPBASIS_ACK@@@Z
?AckLogin@CJSLogic@@IAEXPAUS2C_LOGIN_ACK@@@Z
?AckLogout@CJSLogic@@IAEXPAUS2C_LOGOUT_ACK@@@Z
?AckPrice@CJSLogic@@QAEXPAUG2C_PRICE_ACK@@@Z
?AckResult@CJSLogic@@IAEXPAUG2C_RESULT_ACK@@@Z
?AckSelectPet@CJSLogic@@QAEXPAUG2C_SELECTPET_ACK@@@Z
?AddPlayer@CPlazaManager@@QAEXPAUS2C_PLAYERENTER_ACK@@@Z
?FileLoadProperty@CJSCommand@@QAE_NPAUC2G_UPDATEPROPERTY_REQ@@@Z
?FileLoadQuestList@CJSQuestList@@QAE_NPAUC2G_UPDATEQUESTLIST_REQ@@K@Z
?FileSaveBookShelf@CJSInventory@@QAE_NKPAUC2G_UPDATEBOOK_REQ@@@Z
?FileSaveGym@CJSInventory@@QAE_NKPAUC2G_UPDATEGYM_REQ@@@Z
?FileSaveMarumong@CJSMarumong@@QAE_NKGKPAUC2G_USEMARUMONG_REQ@@@Z
?FileSavePlay@CJSInventory@@QAE_NKPAUC2G_UPDATEPLAY_REQ@@@Z
?FileSaveQuestList@CJSQuestList@@QAE_NPAUC2G_UPDATEQUESTLIST_REQ@@@Z
?FileSaveRefrigerator@CJSInventory@@QAE_NKPAUC2G_UPDATEREFRI_REQ@@@Z
?FileUpdateProperty@CJSProperty@@QAE_NPAUC2G_UPDATEPROPERTY_REQ@@_N1@Z
?GetLoginAck@CLobby@@QAEPAUS2C_LOGIN_ACK@@XZ
?Init@CPLPlayer@@QAEXPAUS2C_PLAYERENTER_ACK@@@Z
?OnAckResult@CGameManager@@IAEXPAUG2C_RESULT_ACK@@@Z
?OnCreatEggAck@CGameManager@@IAEXPAUG2C_CREATEEGG_ACK@@@Z
?OnDelectPetAck@CGameManager@@IAEXPAUG2C_DELETEPET_ACK@@@Z
?OnFunCornAck@CGameManager@@QAEXPAUG2C_FUNCORN_ACK@@@Z
?OnLoginAck@CGameManager@@IAEXPAUS2C_LOGIN_ACK@@@Z
?OnLogoutAck@CGameManager@@IAEXPAUS2C_LOGOUT_ACK@@@Z
?OnNoticeAck@CGameManager@@IAEXPAUS2C_NOTICE_ACK@@@Z
?OnSelectPetAck@CGameManager@@IAEXPAUG2C_SELECTPET_ACK@@@Z
?SendMarumong@CJSLogic@@UAE_NPAUC2G_USEMARUMONG_REQ@@K@Z
?SendMarumong@CJSMarumong@@UAE_NPAUC2G_USEMARUMONG_REQ@@K@Z
?SendQuest@CJSLogic@@UAE_NPAUC2G_QUEST_REQ@@K@Z
?SendQuest@CJSQuestList@@UAE_NPAUC2G_QUEST_REQ@@K@Z
?SendQuestList@CJSLogic@@UAE_NPAUC2G_UPDATEQUESTLIST_REQ@@K@Z
?SendQuestList@CJSQuestList@@UAE_NPAUC2G_UPDATEQUESTLIST_REQ@@K@Z
?SendShop@CJSLogic@@UAE_NPAUC2G_SHOP_REQ@@K@Z
?SendShop@CJSShop@@UAE_NPAUC2G_SHOP_REQ@@K@Z
?SendUpdateProperty@CJSLogic@@UAE_NPAUC2G_UPDATEPROPERTY_REQ@@K@Z
?SendUpdateProperty@CJSProperty@@UAE_NPAUC2G_UPDATEPROPERTY_REQ@@K@Z
?SetLobbyAck@CLobby@@QAEXPAUS2C_LOGIN_ACK@@@Z
?SetVectorMove@CPLPlayer@@QAEXPAUS2C_MOVE_ACK@@@Z
?SetVectorStop@CPLPlayer@@QAEXPAUS2C_STOP_ACK@@@Z
```

### 즉시 읽히는 구조 — VERIFIED (맹글링 문법)

**(a) 송신 5쌍은 전부 `CJSLogic` 에 가상 선언 + 파생 클래스 오버라이드**
```
SendShop           : CJSLogic(UAE) / CJSShop(UAE)
SendQuest          : CJSLogic(UAE) / CJSQuestList(UAE)
SendQuestList      : CJSLogic(UAE) / CJSQuestList(UAE)
SendMarumong       : CJSLogic(UAE) / CJSMarumong(UAE)
SendUpdateProperty : CJSLogic(UAE) / CJSProperty(UAE)
```
시그니처는 전부 `bool __thiscall Send*(STRUCT* , unsigned long)` — **(패킷버퍼, 크기/키) 2인자 일관 패턴.**

**(b) 수신은 두 계층으로 갈린다**
- `CGameManager::On*Ack(STRUCT*)` — 네트워크 계층 진입점 (`IAE` 대부분 = protected)
- `CJSLogic::Ack*(STRUCT*)` — 스크립트/로직 계층 반영

`G2C_RESULT_ACK` 은 `CGameManager::OnAckResult` 와 `CJSLogic::AckResult` **양쪽에 모두** 나타난다
→ **`CGameManager::On*Ack` 가 받아서 `CJSLogic::Ack*` 로 넘기는 2단 파이프라인.** — INFERRED (강함)

**(c) `S2C_*` 는 게임로직이 아니라 월드/세션 계층이 소비한다**
```
S2C_LOGIN_ACK       → CLobby::GetLoginAck / CLobby::SetLobbyAck / CGameManager::OnLoginAck / CJSLogic::AckLogin
S2C_PLAYERENTER_ACK → CPlazaManager::AddPlayer / CPLPlayer::Init
S2C_MOVE_ACK        → CPLPlayer::SetVectorMove
S2C_STOP_ACK        → CPLPlayer::SetVectorStop
S2C_LOGOUT_ACK      → CGameManager::OnLogoutAck / CJSLogic::AckLogout
S2C_NOTICE_ACK      → CGameManager::OnNoticeAck
```
`CPlazaManager`/`CPLPlayer`(PL_ = PlaZa Player 모듈군) 가 소비 → **`S2C_*` = 광장(멀티플레이) 계열**.
`C2G_*`/`G2C_*` 는 `CJS*`(게임스크립트) + `CGameManager` 가 소비 → **미니게임/집안 계열**.

### `C2G/G2C` vs `S2C` 는 다른 소켓인가? — 현 시점 **NOT VERIFIED**
접두사 분리와 소비 클래스 분리는 명확하지만, 그것이 **별도 연결**을 뜻하는지
**한 연결 위의 메시지 분류**인지는 이 심볼들만으로 판정할 수 없다.
판정 근거가 될 것: Plaza RTTI 에 `CConnection` / `CNetwork` / `TcpClient` / `TcpPeer` /
`CClientPeer` / `CGamePeer` 가 **동시에** 존재한다는 사실 — 소켓 추상이 2계열로 보인다.
→ 다음 단계에서 `CClientPeer` 와 `CGamePeer` 의 vtable·인스턴스 수를 실측해 판정한다.

### 주의 — 이 42쌍의 적용 범위
이름쌍 자체는 **Naver 1.4 기준 VERIFIED** 다.
**Plaza 1.3.1 에도 같은 이름·같은 시그니처로 존재하는지는 별도 확인이 필요하다.**
[4] 에서 본 대로 두 빌드는 기능이 다르다. 다만 `CJSLogic/CJSShop/CJSQuestList/CJSMarumong/
CJSProperty/CJSInventory/CJSCommand/CGameManager/CLobby/CPlazaManager` 는 **124개 공통 클래스에 모두 포함**되므로
클래스 존재는 양쪽 VERIFIED 다.

---

## [6] ★ vtable 기준주소 교정 — 문서 78 의 `0x006A618C` 는 **다른 클래스의 vtable** 이다 — VERIFIED

문서 78 은 콘 스텁을 `vtable(0x006A618C)+0x20 = FUN_005949c0` 으로 기술한다.
내 RTTI 파싱은 `CJSCommand` vftable 을 `0x006a61a4` 로 준다. 0x18 차이라 슬롯 인덱스가 6칸 어긋난다.
`.rdata` 원시 덤프로 판정했다(썽크 해석 포함):

```
[0x006a6188] = 0x006c1bb0                      ← COL 포인터 (다른 클래스)
[0x006a618c] = -> 0x005940b0   ┐
[0x006a6190] = -> 0x00593e40   │ 4슬롯 vtable (다른 클래스)
[0x006a6194] = -> 0x005927d0   │
[0x006a6198] = -> 0x00594310   ┘
[0x006a619c] = 0x00000000                      ← 종료
[0x006a61a0] = 0x006c1c10                      ← CJSCommand 의 COL 포인터
[0x006a61a4] = -> 0x00594980   ← CJSCommand vftable 슬롯[0]  ★진짜 시작
[0x006a61a8] = -> 0x005949a0        슬롯[1]
[0x006a61ac] = -> 0x005949c0        슬롯[2]   ← 콘 스텁
 ...
[0x006a61d0] = -> 0x00594ac0        슬롯[11]
[0x006a61d4] = 0x00000000                      ← 종료 (총 12슬롯)
```

**두 vtable 이 인접해 있고, 문서 78 은 앞 vtable 의 시작을 기준으로 삼았다.**
`0x006A618C + 0x20 = 0x006a61ac` 로 **함수는 우연히 맞았지만 슬롯 인덱스 해석은 틀렸다.**

→ 정정: **콘 스텁 `FUN_005949c0` 은 `CJSCommand` 계열 vtable 의 슬롯 [2]** 다(`+0x08`).
   `+0x20`(슬롯 8)이 아니다. 인접 vtable 을 슬롯으로 세는 오류를 반복하지 말 것.
   COL 포인터(`vftable-4`)와 종료 NULL 로 경계를 확인하는 것이 안전한 방법이다.

## [7] ★★ `CJS*` 는 **단일 상속 선형 체인**이고 `CJSLogic` 이 최종 파생 클래스다 — VERIFIED

RTTI BaseClassArray 실측(자기 자신 다음이 직계 base):

```
CJSLogic(13) ← CJSOutDoor ← CJSMenu ← CJSCommand ← CJSShop ← CJSQuestList
             ← CJSStatus ← CJSProperty ← CJSScheduler ← CJSMarumong
             ← CJSInventory ← CJSUser(mdisp=4) + CUtil(mdisp=4)
CJSCommand(10) ← CJSShop ← ... (동일 꼬리)
CJSShop(9)     ← CJSQuestList ← ... (동일 꼬리)
```
`CJSScheduler` 만 `mdisp=1495`, `CJSUser`/`CUtil` 은 `mdisp=4`, 나머지 전부 `mdisp=0`
→ 같은 주소를 공유하는 **단일 상속 사슬**. 다중 상속이 아니다.

### 이것이 확정하는 것
1. **런타임 객체는 `CJSLogic` 하나다.** 게임 스크립트 시스템 전체가 기능별 mixin 을 선형으로
   쌓아 만든 **단일 객체**이며, 실제 vtable 은 **`CJSLogic` 의 `0x006a6478`** 이다.
2. 문서 78 의 *"소지금 model vtable `0x006A6478`, `model+0x1F0`"* 와 **정확히 일치** →
   **그 "model" 의 실명은 `CJSLogic`** 이다. — VERIFIED (RTTI 가 독립 확증)
3. `CJSShop`/`CJSCommand` 등 중간 클래스의 vtable 은 **사슬 중간 시점의 스냅샷**이며
   런타임에 쓰이지 않는다. 중간 vtable 주소로 런타임 동작을 논하면 안 된다.

### 런타임 vtable (`CJSLogic` 0x006a6478) vs 베이스 구현
| 슬롯 | 베이스 구현(CJSCommand) | **CJSLogic 오버라이드(런타임)** |
|---|---|---|
| 0 | 0x00594980 | **0x0059dc50** |
| 1 | 0x005949a0 | **0x0059dba0** |
| 2 | 0x005949c0 ← 콘 스텁 | **0x0059dbe0** |
| 3 | 0x005949e0 | **0x0059db70** |
| 4 | 0x00594a00 | **0x0059da90** |
| 5 | 0x00594a20 | **0x0059dcd0** |
| 6 | 0x00594a40 | **0x0059db40** |
| 7 | 0x00594a60 | **0x0059dad0** |
| 8 | 0x00594a80 | **0x0059dc90** |
| 9 | 0x00594aa0 | 0x00594aa0 (동일) |
| 10 | 0x00598ea0 | 0x00598ea0 (동일) |
| 11 | 0x00594ac0 | **0x0059dc20** |

**`CJSLogic` 은 12슬롯 중 10개를 오버라이드한다.**
→ 문서 78 의 SUPERSEDED 배너(*"실제 파생 CJSLogic 은 이 slot 을 override"*)를 RTTI 가 뒷받침한다.
   **런타임에 콘 경로는 스텁 `0x005949c0` 이 아니라 `0x0059dbe0` 으로 간다.** — VERIFIED

`CJSQuestList`/`CJSShop` 만 슬롯[10]이 `0x005a5620` 으로 다르다(다른 클래스는 `0x00598ea0`).
중간 사슬에서 한 번 오버라이드됐다가 `CJSLogic` 에서 다시 베이스값으로 돌아온 것은 불가능하므로,
**슬롯[10] 해석은 보류한다** — NOT VERIFIED, 재확인 필요.

## [8] 가상함수 도입 개수 = vtable 슬롯 증가 — 구조가 맞물린다 — VERIFIED(개수) / NOT VERIFIED(슬롯↔이름)

`.ilk` 맹글링에서 가상(`UAE`/`MAE`/`EAE`)만 추출, 체인 순서로 정렬:

| 클래스 | 새로 도입한 가상함수 | 누적 | **실측 vtable 슬롯 수** |
|---|---|---|---|
| CJSUser / CUtil | 0 | 0 | (vtable 없음) |
| CJSInventory | `SendInventory`, `SendInventoryApply`, `SendUseItem` (3) | 3 | **3** ✓ |
| CJSMarumong | `SendMarumong` (1) | 4 | **4** ✓ |
| CJSScheduler | 0 | 4 | — |
| CJSProperty | `SendErrorReport`(MAE), `SendUpdateProperty` (2) | 6 | **6** ✓ |
| CJSStatus | 0 | 6 | **6** ✓ |
| CJSQuestList | `AddFuncorn`, `SendGame`, `SendQuest`, `SendQuestList` (4) | 10 | **11** ✗(+1) |
| CJSShop | `SendShop` (1) | 11 | **12** ✗(+1) |
| CJSCommand | 0 | 11 | **12** ✗(+1) |
| CJSMenu / CJSOutDoor | 0 | 11 | **12** ✗(+1) |
| CJSLogic | `OnReceive`(MAE) (1) | **12** | **12** ✓ |

앞 5개 클래스가 **정확히 일치**한다. 우연이 아니다 — 체인 순서와 도입 개수 모델이 옳다.

### 남은 +1 불일치 — 단정하지 않는다
`CJSQuestList` 부터 실측이 예상보다 1 많다. 두 해석이 가능하다:
- (a) Plaza 1.3.1 의 `CJSQuestList` 가 Naver 1.4 에 없는 가상함수를 하나 더 도입했다
      ([4] 대로 Plaza 는 기능이 더 많은 별개 브랜치다), 그리고 `CJSLogic` 은 `OnReceive` 를 도입하지 않는다.
- (b) `OnReceive` 가 실제로는 체인 더 아래에서 도입됐다.

**어느 쪽인지 확정 전까지 슬롯 인덱스에 메서드 이름을 붙이지 않는다.** — NOT VERIFIED

추가로, 각 클래스 내부의 **선언 순서를 심볼 목록만으로는 알 수 없다**(알파벳 정렬이지 선언순이 아님).
따라서 `CJSInventory` 의 3개가 슬롯 0/1/2 중 어디인지도 미확정이다.
→ 확정 수단: 각 슬롯 함수의 **인자 바이트 수(`RET imm16`)** 와 본문 동작.
  (바이트 스캔으로 `C2`/`C3` 를 세는 방식은 피연산자 오탐이 심해 **폐기**했다. Ghidra 디컴파일 결과로 판정한다.)

## [9] 네트워크 클래스 계층 — `C2G/G2C` vs `S2C` 소켓 판정의 1차 증거 — VERIFIED

```
CClientPeer(5) ← CGamePeer ← TcpClient , CPacket(mdisp=23) , CThreadBase(mdisp=16486)
CGamePeer(3)   ← TcpClient , CPacket(mdisp=23)
TcpPeer(2)     ← Monitor
CConnection(1) : base 없음 (독립)
CNetwork(1)    : base 없음 (독립)
CPacket(1)     : base 없음
TcpClient(1)   : base 없음
```

### 읽히는 것
1. **`CClientPeer` 와 `CGamePeer` 는 같은 소켓 계보다.** `CClientPeer` IS-A `CGamePeer` IS-A `TcpClient`.
   두 개의 독립적인 TCP 스택이 아니라 **한 계보의 특수화**다.
2. `TcpPeer ← Monitor` 는 **별개 계보** — 게임 소켓이 아닐 가능성이 높다(모니터링/리스너 성격).
3. `CThreadBase` 가 `mdisp=16486`(0x4066) 에 있다 → `CClientPeer` 객체가 **16KB 이상**이다.
   문서 22 의 *"dispatch flag at `this+0x4076`"* 와 자릿수가 정합한다(0x4066 + 0x10). — INFERRED (강함)

### 판정 — 아직 못 한다
클래스 계보가 하나라는 것은 **소켓이 하나**임을 뜻하지 않는다(같은 클래스를 두 번 인스턴스화할 수 있다).
`C2G/G2C` 와 `S2C` 가 별도 연결인지 한 연결의 메시지 분류인지는
**`CGamePeer`/`CClientPeer` 인스턴스 개수와 `connect()` 호출 횟수의 실측**으로만 갈린다.
— **NOT VERIFIED. 현 시점 미판정.**

보조 정황(단정 아님): `.ilk` 소비 클래스 분리가 뚜렷하다.
- `C2G_*`/`G2C_*` → `CJS*`(게임스크립트) + `CGameManager`
- `S2C_*` → `CLobby`, `CPlazaManager`, `CPLPlayer`(광장 플레이어)
`CPlazaManager`/`CPLPlayer` 는 멀티플레이 광장 계열이고, Plaza 빌드에만 있는 `CMultiGame` 과 묶인다.

---

## [10] ★★★ C→S opcode 를 **Plaza 바이너리에서 직접** 읽어냈다 — VERIFIED

`CJSLogic` vtable 의 12개 슬롯은 전부 **얇은 래퍼**이고, 대부분 opcode 가 **상수로 박혀 있다**.
Ghidra 디컴파일 원문(발췌):

```c
FUN_0059dc50(u16 a)             { local=a;            Send(0x14, &local, 2); }   // slot 0
FUN_0059db70(a, b)              {                     Send(0x15, a, b);      }   // slot 3
FUN_0059dcd0(u8 a, u8 b, u32 c) { pack{a,b,c};        Send(0x17, &pack, 6);  }   // slot 5
FUN_0059db40(a, b)              {                     Send(0x11, a, b);      }   // slot 6
FUN_0059dad0(this, a, b)        { if(*(a+1)==1){ vt[0x28](); helper(0,1,7); }
                                                      Send(0x10, a, b);      }   // slot 7
FUN_0059dc90(u32 a, u8 b)       { pack{a,b};          Send(0x12, &pack, 5);  }   // slot 8
FUN_0059dc20(a, b)              {                     Send(0x13, a, b);      }   // slot 11
FUN_0059dba0/0059dbe0/0059da90(op, buf, len) { Send(op, buf, len); }             // slots 1,2,4
```

### 송신 체인 전체 — VERIFIED
```
CJSLogic::vtable[slot](args)
  -> FUN_0059d760(opcode, buf, len)
  -> FUN_00593d10(opcode, buf, len)
        게이트: FUN_00592a50(peer) = *(peer+0x4076)      <- 문서 22 의 dispatch flag
        -> FUN_004fca60 / FUN_004fcc40   (로깅 2종)
        -> FUN_00592600(peer, ...)   게이트 재확인 *(peer+0x4076)
              -> FUN_00592140(...)   실제 패킷 기록
```
`peer+0x4076` 이 문서 22 의 "dispatch flag at this+0x4076" 와 **정확히 일치** — 독립 확증. — VERIFIED

### 슬롯별 인자 개수 (`RET imm16` 실측, 베이스 스텁과 CJSLogic 오버라이드가 **전 슬롯 일치**)

| 슬롯 | 베이스 스텁 | RET | 인자 | **CJSLogic(런타임)** | **C→S opcode** | 페이로드 |
|---|---|---|---|---|---|---|
| 0 | 0x00594980 | 4 | 1 | **0x0059dc50** | **0x14** | 2B (u16) |
| 1 | 0x005949a0 | 12 | 3 | 0x0059dba0 | 호출자 지정 | — |
| 2 | 0x005949c0 | 12 | 3 | 0x0059dbe0 | 호출자 지정 | — |
| 3 | 0x005949e0 | 8 | 2 | **0x0059db70** | **0x15** | 호출자 지정 |
| 4 | 0x00594a00 | 12 | 3 | 0x0059da90 | 호출자 지정 | — |
| 5 | 0x00594a20 | 12 | 3 | **0x0059dcd0** | **0x17** | 6B {u8,u8,u32} |
| 6 | 0x00594a40 | 8 | 2 | **0x0059db40** | **0x11** | **0x50 = 80B** |
| 7 | 0x00594a60 | 8 | 2 | **0x0059dad0** | **0x10** | 호출자 지정 |
| 8 | 0x00594a80 | 8 | 2 | **0x0059dc90** | **0x12** | 5B {u32,u8} |
| 9 | 0x00594aa0 | 4 | 1 | (오버라이드 없음) | — | 빈 스텁 |
| 10 | 0x00598ea0 | — | — | (오버라이드 없음) | — | 상태 직렬화기 307B |
| 11 | 0x00594ac0 | 8 | 2 | **0x0059dc20** | **0x13** | **0x2d = 45B** |

슬롯 10 의 중간 사슬 변형 `0x005a5620` 은 `return 1` (21B) 스텁이고,
`CJSCommand` 부터 `0x00598ea0`(플레이어 상태를 `+0x5f8`~`+0x6bc` 로 패킹) 으로 오버라이드된다.
→ [7] 에서 "보류" 로 남긴 슬롯[10] 의문 해소. 파생이 스텁을 실구현으로 덮은 정상 패턴이다. — VERIFIED

## [11] ★ 문서 78 정정 — 콘 스텁은 `FUN_005949c0` 이 **아니다** — VERIFIED

문서 78 은 "콘 스텁(vtable+0x20 = FUN_005949c0)" 이라 기록했다. **틀렸다.**

### 세 갈래 독립 증거
1. **vtable 기준주소**: 보상 코드가 부르는 것은 `logic->vtable[+0x20]` 이고 `logic` 은 `CJSLogic` 이다.
   `CJSLogic` vftable = `0x006a6478` → `+0x20` = **슬롯[8]**.
   문서 78 이 쓴 `0x006A618C` 는 [6] 에서 밝힌 대로 **인접한 다른 클래스의 4슬롯 vtable** 이라
   `+0x20` 이 엉뚱하게 `CJSCommand` 슬롯[2]에 떨어졌다.
2. **인자 개수 (`RET imm16`)** — 결정적:
   ```
   0x005949c0 (슬롯2): 55 8b ec 83 ec 44 ... c2 0c 00   RET 0xc -> 인자 3개
   0x00594a80 (슬롯8): 55 8b ec 83 ec 44 ... c2 08 00   RET 0x8 -> 인자 2개  OK
   ```
   보상 호출부는 `(amount, 2)` **2인자**다. `FUN_005949c0` 은 3인자라 **애초에 호출될 수 없다.**
3. **호출부 전수 검색**: `vtable+0x20` 호출자 = `FUN_005a6ce0`(kind0), `FUN_005a7240`(kind1),
   `FUN_005a8790`(kind5) — 전부 `(uStack_10, 2)`. 문서 78 이 지목한 kind0/1/2 보상함수와 일치.

### 정정된 사실
- **콘/보상 슬롯 = 슬롯[8]** (`vtable+0x20`).
- 중간 사슬 스텁 = `FUN_00594a80` (2인자), **런타임 실구현 = `FUN_0059dc90`**.
- `FUN_0059dc90` 은 **C→S `0x12`** 를 `[u32 amount][u8 channel]` **5바이트**로 송신한다.
- 문서 78 의 동적 실측 "0x0012 계약: [amount:u32][channel:u8], 퀘스트 보상 시 [40, 2] 관측" 과
  **정적 디컴파일이 완전 일치** → 상호 확증. (동시에 이 일치가 `Send(opcode, buf, len)` 인자 순서를 확정한다.)
- `FUN_005949c0` 은 **무관한 3인자 가상함수의 중간 스텁**일 뿐이다.

`0x005949c0`/`0x00594a80` 등 23바이트 스텁들은
`55 8b ec 83 ec 44 53 56 57 89 4d fc 32 c0 5f 5e 5b 8b e5 5d c2 NN 00` 로
**RET 즉값만 다른 동일 본문**이다. 문서 78 의 "인접 +0x28 도 스텁 = 스텁 클러스터" 관찰은 맞지만,
**본문이 같으므로 주소만 보고 어느 슬롯인지 판별하면 안 된다. RET 즉값이 유일한 구분자다.**

## [12] 2인자 STRUCT sender 식별 — 호출부 페이로드 크기로 2건 확정

### `opcode 0x11` (슬롯6, 80B) = **`SendQuestList(C2G_UPDATEQUESTLIST_REQ*, unsigned long)`** — STRUCT
호출자 `FUN_005a5bc0`:
```c
for (i = 0; i < 10; i++) {                       // 10행
  kind  = param_1[i*3 + 0x1c3];                  // 0x1c3*4 = 0x70c
  aux   = param_1[i*3 + 0x1c4];
  value = param_1[i*3 + 0x1c5];
  ...pack u16 kind, u16 aux, u32 value...        // 8B x 10행 = 80B
}
(**(code **)(*param_1 + 0x18))(local_5c, 0x50);  // 슬롯6, 0x50 = 80
```
`param_1 + 0x70c` = 문서 78 의 **`CLogicManager+0x70c`(stride 0xc: kind/aux/value) 퀘스트 10행 테이블**과
오프셋·stride·행수가 **정확히 일치**. 페이로드 80B 도 문서 123 의 "C→S0011 80B sender" 와 일치.
→ 퀘스트 목록 업로드가 확실하고, 이름 후보는 `SendQuestList` 하나뿐(구조체명 `C2G_UPDATEQUESTLIST_REQ`).

### `opcode 0x13` (슬롯11, 45B) = **`SendShop(C2G_SHOP_REQ*, unsigned long)`** — STRUCT
호출자 `FUN_005a9a10`:
```c
iVar2 = FUN_005a95b0(param_1, param_2);          // <- 구매 검증 앵커!
if (0 < iVar2) {
  local_40 = (u8)param_2;                        // 개수
  for (i = 0; i < param_2; i++) { ...u32/u16 항목 복사... }
  local_3f = iVar2;                              // 검증 결과(가격/수량)
  (**(code **)(*local_c + 0x2c))(&local_40, 0x2d);  // 슬롯11, 0x2d = 45
  if (ok) FUN_005a9540(1, local_10);
}
```
**검증 앵커 `0x005a95b0`(소지금<cost 체크)를 직접 호출한 뒤 송신**한다 → 상점 구매 확정 경로.

### `0x005a95b0` 의 이름 — **WEAK (확정 불가)**
`(int* 배열, int 개수) -> int` 형태다. `.ilk` 후보 중 시그니처가 **완전히 동일한 것이 둘**이다:
```
?ShopAddToCart@CJSShop@@QAEHPAHH@Z   int ShopAddToCart(int*, int)
?ShopPayInCart@CJSShop@@QAEHPAHH@Z   int ShopPayInCart(int*, int)
```
역할(결제 직전 소지금 검증)로는 `ShopPayInCart` 가 유력하나 **시그니처만으로는 가를 수 없다.**
→ **WEAK. 이름 확정하지 않는다.** 클래스가 `CJSShop` 인 것까지만 STRUCT 등급.

### 나머지 2인자 슬롯 3(0x15) / 7(0x10) — **미확정**
남은 이름 후보는 `SendQuest`, `SendMarumong`, `SendUpdateProperty` 3개인데 슬롯은 2개다.
[8] 의 도입 개수 모델과 결합하면 슬롯3 = `CJSMarumong` 이 도입한 유일한 가상함수 =
`SendMarumong` 이 되지만, **모델 자체가 아직 +1 불일치를 안고 있어 단정하지 않는다.**
→ **WEAK.**

## [13] S→C 디스패처 `0x00613740` — opcode 스위치 전문 — VERIFIED

```c
void __thiscall FUN_00613740(this, opcode, buf, len) {
  *(int *)(this + 0x12a8) += len;            // 누적 수신 바이트 카운터
  if (opcode < 0x3e9) {
    if (opcode == 1000) FUN_006167e0();
    else switch (opcode) { ... }
  }
}
```

| opcode | 핸들러 (Plaza 1.3.1) | 인자 |
|---|---|---|
| `0x03` | `FUN_00615610` | buf+1 |
| `0x0C` | `FUN_006165b0` | buf |
| `0x64` (100) | `FUN_00615650` | buf |
| `0x65` | `FUN_00615b20` | — |
| `0x66` | `FUN_00615b50` | buf, len |
| `0x67` | `FUN_00615d00` | buf |
| `0x68` | `FUN_00615d50` | buf, len |
| `0x69` | `FUN_00615e70` | buf |
| `0x6A` | `FUN_00615ff0` | buf |
| `0x6B` | `FUN_00615340` | buf |
| `0x6C` | `FUN_00615410` | buf |
| `0x6D` | `FUN_006154e0` | buf |
| `0x6E` | `FUN_006169d0` + `FUN_00627560(0,0)` + `FUN_00627630` | buf |
| `0x6F` | `FUN_00616b20` | buf |
| `0x70` | `FUN_00616860` | buf |
| `0x71` | `FUN_00616510` | buf |
| `0x3E8` (1000) | `FUN_006167e0` | — |

**주의**: 이 디스패처의 opcode 대역(`0x03`,`0x0C`,`0x64`~`0x71`,`0x3E8`)은
기존 문서의 S→C `0x0007` / `0x00CE` 와 **겹치지 않는다.**
→ **S→C 디스패처가 여러 개 있다.** `0x00613740` 은 그 중 하나("DispatchState1")일 뿐이며,
이 표를 S→C 전체로 착각하면 안 된다. — VERIFIED (부재 확인)

## [14] 산출물 — 프로토콜 레지스트리 표 (현 시점 확정분)

등급: `VERIFIED`=Plaza 디컴파일 직접 근거 / `STRUCT`=구조·호출관계 일치 / `WEAK`=정황만 / `NONE`=미매칭

### C→S (Plaza 1.3.1, `CJSLogic` vtable `0x006a6478`)

| opcode | 방향 | 구조체 실명 | 핸들러 실명 | Plaza 1.3.1 주소 | 등급 |
|---|---|---|---|---|---|
| `0x10` | C→S | ? | ? (슬롯7) | `0x0059dad0` | 주소·opcode **VERIFIED** / 이름 **NONE** |
| `0x11` | C→S | `C2G_UPDATEQUESTLIST_REQ` | `CJSLogic::SendQuestList` | `0x0059db40` (송신자 `0x005a5bc0`) | **STRUCT** (80B·10행·`+0x70c` 일치) |
| `0x12` | C→S | (Plaza 전용, `.ilk` 에 없음) | 콘/보상 송신 (슬롯8) | `0x0059dc90` | 주소·opcode·페이로드 **VERIFIED** / 이름 **NONE** |
| `0x13` | C→S | `C2G_SHOP_REQ` | `CJSLogic::SendShop` | `0x0059dc20` (송신자 `0x005a9a10`) | **STRUCT** (구매검증 직후 45B) |
| `0x14` | C→S | — (스칼라 u16) | `CJSLogic::SendUseItem` | `0x0059dc50` | **STRUCT** (유일한 1인자 u16 가상함수) |
| `0x15` | C→S | ? | ? (슬롯3) | `0x0059db70` | 주소·opcode **VERIFIED** / 이름 **WEAK**(`SendMarumong` 후보) |
| `0x17` | C→S | — (스칼라 3개) | `CJSLogic::SendErrorReport` | `0x0059dcd0` | **STRUCT** (3인자→`{u8,u8,u32}` 6B 일치) |
| (호출자 지정) | C→S | — | 슬롯1 / 슬롯2 / 슬롯4 | `0x0059dba0` / `0x0059dbe0` / `0x0059da90` | 주소 **VERIFIED** / opcode·이름 **NONE** |

### S→C (디스패처 `0x00613740` 한정)
[13] 표 참조. 구조체 실명은 **하나도 매칭되지 않았다** — `.ilk` 의 `S2C_*` 는
`CLobby`/`CPlazaManager`/`CPLPlayer` 가 소비하는데, 이 디스패처의 핸들러들과 아직 연결하지 못했다. — **NONE**

### 매칭 실패를 명시한다 (부재 증명)
- `.ilk` 의 23개 구조체 중 **Plaza 주소까지 연결된 것은 2개**(`C2G_UPDATEQUESTLIST_REQ`, `C2G_SHOP_REQ`)뿐이다.
- `S2C_LOGIN_ACK` / `S2C_MOVE_ACK` / `S2C_STOP_ACK` / `S2C_PLAYERENTER_ACK` / `S2C_NOTICE_ACK` /
  `S2C_LOGOUT_ACK`, `G2C_*` 8종, 나머지 `C2G_*` — **전부 Plaza 주소 미매칭 (NONE).**
- 이유: 이들을 소비하는 `CGameManager::On*Ack` / `CJSLogic::Ack*` 는 **전부 비가상**(`IAE`/`QAE`)이라
  vtable 슬롯 기법이 통하지 않고, 두 빌드 툴체인이 달라 바이트 매칭도 불가([4]).
- **다음 단계 제안**: S→C 수신 경로(`CClientPeer` → `CGamePeer::OnReceive` → 디스패처들)를 추적해
  나머지 디스패처를 전수 확보한 뒤, 각 핸들러가 읽는 **필드 오프셋 패턴**으로 구조체를 대조하는 것이
  유일하게 남은 신뢰 가능한 경로다. 억지 이름 부여 금지.

## [15] 사용한 방법 기록 (재현 절차)

1. `rtti2.py` / `vtab.py` — PE 에서 MSVC RTTI 를 검증 파싱(TypeDescriptor vfptr 일치 → COL → CHD → BaseClassArray 전수 검증),
   `[vftable-4]` 가 COL 을 가리키는 위치를 vftable 로 확정, 슬롯의 `jmp rel32` 썽크를 1단 해석.
2. `hier.py` — BaseClassArray 를 읽어 상속 체인 복원.
3. `analyzeHeadless` + `DumpAll.java` — Plaza/Naver 전 함수 디컴파일 + 문자열 xref 덤프
   (Ghidra MCP 는 이 세션 내내 `Database is closed` 로 실패해 사용 불가. `run_script_inline` 은 지시대로 미사용).
4. 인자 개수는 **함수 크기 범위 내 첫 `RET imm16`** 으로 판정(전역 바이트 스캔은 피연산자 오탐이 심해 폐기).
5. 슬롯 식별은 **호출부의 상수 페이로드 크기**와 **호출자가 읽는 구조체 오프셋**을 근거로 삼음.

**기존 Ghidra 프로젝트 `azrok` 의 `Azrok_original.exe` 는 열지도 수정하지도 않았다.**
분석은 전부 스크래치패드 사본(`Azrok_plaza131.exe`, `Azrok_naver14.exe`)과 임시 프로젝트에서 수행했다.

---

## [16] 방법 보강 — Ghidra `CALLERS` 는 **썽크 때문에 비어 보인다** — VERIFIED

`DumpAll.java` 의 `getCallingFunctions()` 가 거의 모든 함수에서 빈 목록을 냈다.
원인: 이 바이너리는 증분 링크 썽크(`0x004d7000~0x004e2000`)를 거쳐 호출하므로
호출자가 `thunk_FUN_XXXX` 로 잡히고, 원본 함수의 caller 목록에는 안 올라온다.

→ **호출자를 찾을 때는 `thunk_FUN_<addr>` 토큰을 본문에서 검색해야 한다.**
[10]~[12] 에서 vtable 슬롯 호출부를 찾을 때 이 방법을 썼고, 아래 [17] 도 마찬가지다.
`// CALLERS:` 가 비었다고 "호출자 없음" 으로 읽으면 안 된다. — VERIFIED

## [17] ★★ 소켓 판정 — **게임 연결은 하나다. `C2G/G2C` 와 `S2C` 는 같은 연결의 메시지 분류다** — VERIFIED

[9] 에서 "판정 못 한다"로 남긴 항목의 답이다.

### (a) 생성 사슬 — `CGamePeer` 는 독립 인스턴스가 없다
vftable 주소를 **.text 의 즉값**으로 전수 검색했다(디컴파일 텍스트에는 안 나온다).
각 클래스마다 정확히 2곳 = MSVC 의 **생성자/소멸자** 쌍이다:

| 클래스 | 생성자 | 소멸자 |
|---|---|---|
| `CClientPeer` (vft ×3: `0x006a60b0`/`0x006a60c0`/`0x006a60cc`) | `FUN_005918d0` | `FUN_00591b60` |
| `CGamePeer` (vft ×2: `0x006af370`/`0x006af37c`) | `FUN_0061be80` | `FUN_0061c010` |
| `TcpClient` (`0x006af3d0`) | `FUN_0061e1e0` | `FUN_0061e2a0` |
| `TcpPeer` (`0x006af3ec`) | `FUN_0061eaf0` | `FUN_0061ec40` |
| `CJSLogic` (`0x006a6478`) | `FUN_0059ce80` | `FUN_0059d020` |
| `CLogicManager` (`0x006a618c`) | `FUN_00593f30` | — |

썽크 기준 호출자 추적 결과:
```
FUN_005926e0        →  FUN_005918d0 (CClientPeer ctor)
FUN_005918d0        →  FUN_0061be80 (CGamePeer ctor)      ← 기반 클래스 생성자로서만
FUN_00593f30        →  FUN_0059ce80 (CJSLogic ctor)
```
→ **`CGamePeer` 생성자의 호출자는 `CClientPeer` 생성자 하나뿐이다.
   독립적으로 만들어지는 `CGamePeer` 객체가 존재하지 않는다.** — VERIFIED

### (b) `CClientPeer` 생성자가 객체 레이아웃을 확증한다 — VERIFIED
```c
FUN_005918d0(this):
    FUN_0061be80(...);                       // CGamePeer 기반 생성자
    FUN_0061f4f0(...);                       // CThreadBase 생성자
    *this            = CClientPeer::vftable; // 주 vptr
    *(this + 0x17)   = CClientPeer::vftable; // CPacket 서브객체 vptr
    *(this + 0x4066) = CClientPeer::vftable; // CThreadBase 서브객체 vptr
    FUN_004eca70(this + 0x4085, 0x10d, 0x4b, ...);   // 송신 링: 75슬롯 × 269B
    FUN_004eca70(this + 0x9360, 0xa9,  300, ...);    // 수신 링: 300슬롯 × 169B
    *(this + 0x4079) = 0;
    *(this + 0x4076) = 0;                    // dispatch flag
```
`+0x17`(=23) 과 `+0x4066`(=16486) 은 [9] 에서 RTTI BaseClassArray 로 읽은
`CPacket mdisp=23`, `CThreadBase mdisp=16486` 과 **정확히 일치**한다.
[9] 에서 "정렬이 이상해 신뢰도 낮음"으로 유보했던 mdisp 값이 **생성자로 독립 확증**됐다. — VERIFIED

### (c) 두 번째 소켓 스택은 **죽어 있다**
소켓 API 호출 지점을 전수 조사하니 코드 영역이 둘로 갈린다:

| 영역 | 함수 | API | RTTI 클래스 |
|---|---|---|---|
| **`0x0061xxxx`** | `FUN_0061e340`, `FUN_0061dfd0`, `FUN_0061e7e0` | `gethostbyname`, `WSAEventSelect(0x10=FD_CONNECT)`, `WSAEventSelect(0x21=FD_READ\|FD_CLOSE)` | `TcpClient` / `CGamePeer` / `CClientPeer` / `TcpPeer` |
| **`0x0050xxxx`** | `FUN_00501260`, `FUN_00500c30`, `FUN_00501510` | **`listen(s,5)`**, **`accept()`**, `WSAEventSelect(0x28/0x30)` | `CConnection`(vft `0x0069cea4`) / `CNetwork`(vft `0x0069ceb0`) |

**`listen()` 을 가진 `FUN_00501260` 과 `accept()` 를 가진 `FUN_00500c30` 은
썽크 포함 전수 검색에서 호출자가 0개다.** — VERIFIED (부재 확인)
→ 리스너 스택(`CConnection`/`CNetwork`)은 이 빌드에서 **구동되지 않는다**(코드만 남아 있음).
   함수 포인터/가상 디스패치로 도달할 가능성은 배제하지 못하므로 "완전 사망"으로 단정하진 않는다. — INFERRED

### (d) 판정
1. 게임 서버 연결 계보는 **`CClientPeer` 단일**이고, 인스턴스도 하나의 생성 경로뿐이다.
2. `CGamePeer` 는 그 기반 클래스일 뿐 별도 연결이 아니다.
3. 두 번째 소켓 스택은 클라이언트가 **접속받는(listen/accept)** 쪽이라 애초에 "서버로의 두 번째 연결"이 아니며, 게다가 호출자가 없다.
4. 송신은 전부 `CJSLogic vtable → FUN_0059d760 → FUN_00593d10 → FUN_00592600 → FUN_00592140` 하나의 경로로 수렴하고, 게이트가 `peer+0x4076` **하나**다([10]).

→ **`C2G_`/`G2C_` 와 `S2C_` 는 별도 소켓·포트가 아니라 같은 연결 위의 메시지 계열 이름이다.** — VERIFIED
   (`.ilk` 의 소비 클래스 분리 — `CJS*`/`CGameManager` vs `CLobby`/`CPlazaManager`/`CPLPlayer` — 는
   **연결 분리가 아니라 서브시스템 분리**를 뜻한다. [5] 의 유보를 이것으로 해소한다.)

**서버 재구현 함의**: 포트를 하나만 열면 된다. `S2C_*` 계열을 위한 별도 리스너가 필요 없다.

## [18] ★★ 와이어 프레임 포맷 — `[u16 len][u16 opcode][payload]` — VERIFIED

`FUN_00592140` (248 B) 이 실제 패킷 기록부다:
```c
undefined1 __thiscall FUN_00592140(int peer, void *payload, undefined2 opcode, size_t len)
{
    idx = *(int *)(peer + 0x4081) + 1;
    if (idx >= 0x4b) idx = 0;                       // 링 버퍼 75슬롯
    if (*(char *)(peer + 0x4085 + idx*0x10d) == 0) {   // 슬롯 비어있음 플래그
        u16 *p = (u16 *)(peer + 0x4092 + idx*0x10d);
        p[1] = opcode;                              // byte +2
        p[0] = (u16)len;                            // byte +0
        memcpy(p + 2, payload, len);                // byte +4
        *(size_t *)(peer + 0x408a + idx*0x10d) = len + 4;   // 프레임 총 길이
        *(char  *)(peer + 0x4085 + idx*0x10d) = 1;          // 전송 대기 표시
    }
}
```

**확정 사실:**
- 헤더 4바이트: **`[u16 payloadLen][u16 opcode]`** — 길이가 먼저, opcode 가 뒤.
- 프레임 총 길이 = `payloadLen + 4`.
- 슬롯 크기 `0x10d`(269) = 헤더 4 + 페이로드 최대 **261바이트** + 관리 바이트.
- 송신 링 75슬롯(`0x4b`), 수신 링 300슬롯 × `0xa9`(169) B.

[10] 의 `Send(opcode, buf, len)` 3인자가 여기서 `opcode`/`payload`/`len` 으로 정확히 대응한다.
문서 78 의 동적 실측(`0x0012` 페이로드 `[40, 2]` = 5바이트)과 결합하면
그 프레임은 **`05 00 12 00 28 00 00 00 02`** (payloadLen=5, op=0x12,
payload 5B, total=9B)이다. — **VERIFIED (dynamic):**
`captures/packets_20260718_215018.txt` packet #69가 이 9바이트를 그대로 기록했다.
`09 00`은 총 프레임 길이와 헤더의 payload 길이를 혼동한 이전 예시였으며 폐기한다.

## [19] `0x006a618c` 의 정체 = **`CLogicManager` vtable** — 문서 78 혼선의 진짜 원인 — VERIFIED

[6] 에서 "인접한 다른 클래스의 4슬롯 vtable" 이라고만 했던 것의 이름이 나왔다.
RTTI: **`.?AVCLogicManager@@ vftable=0x006a618c, 4 slots**
```
[0] 0x005940b0   [1] 0x00593e40   [2] 0x005927d0   [3] 0x00594310
```
Ghidra 도 생성자에서 `*param_1 = CLogicManager::vftable` 로 이름을 붙였다.

### 객체 관계 — `CLogicManager` 가 `CJSLogic` 을 품는다
```c
FUN_00593f30 (CLogicManager ctor):
    *param_1 = CLogicManager::vftable;    // 자기 vptr (0x006a618c, 4슬롯)
    thunk_FUN_0059ce80();                 // ← CJSLogic 생성자 호출
    ...
```
RTTI 상 `CLogicManager` 의 base 는 `CLogicJSDB`, `CLogic` 뿐이고 `CJSLogic` 은 없다
→ **상속이 아니라 포함(멤버)** 이다. 즉 한 객체 안에 **vptr 이 둘** 존재한다.

### 이것이 문서 78 오류를 완전히 설명한다
- 보상 코드의 `logic->vtable[+0x20]` 에서 `logic` 은 **`CJSLogic` 서브객체 포인터**(vptr `0x006a6478`, 12슬롯)
  → `+0x20` = 슬롯[8] = `FUN_0059dc90` (C→S `0x12`). [11] 의 결론 그대로.
- 문서 78 은 **`CLogicManager` 의 vptr(`0x006a618c`, 슬롯 4개뿐)** 을 기준으로 삼아 `+0x20` 을 더했고,
  그 vtable 끝을 넘어 **바로 뒤에 붙어 있는 `CJSCommand` vtable 의 슬롯[2]** 에 떨어졌다.
- 즉 오류의 원인은 "주소를 잘못 봤다"가 아니라 **"같은 객체의 두 vptr 중 다른 것을 골랐다"** 이다.

→ **교훈**: 이 코드베이스에서 `logic` 이라는 이름의 포인터는 문맥에 따라
  `CLogicManager*` 일 수도 `CJSLogic*` 일 수도 있다. **vtable 슬롯을 세기 전에
  그 포인터의 vptr 값을 먼저 확정하라.** — VERIFIED

## [20] 문서 22 정정 후보 — `FUN_0061e340` 은 `CConnection::Connect` 가 아니다 — INFERRED

문서 22 는 `0x0061e340` 을 `CConnection::Connect` 로 명명했다. RTTI 는 그렇게 말하지 않는다:
- `CConnection` vftable = **`0x0069cea4`**, 슬롯[0] = `0x005005d0` → **`0x0050xxxx` 리스너 영역**
- `0x0061e340` 은 `TcpClient` vftable(`0x006af3d0`) 슬롯들(`0x0061e250`, `0x0061ea20`, `0x0061ea40`,
  `0x0061ea60`, `0x0061ea80`) 사이에 위치 → **`TcpClient` 계열 메서드**
- `0x0061e340` 호출자: `FUN_00591c70`, `FUN_00592920`(문서 22 의 "ConnectToServer")

→ **`0x0061e340` 은 `TcpClient::Connect` 로 보는 편이 근거에 맞다.** — INFERRED
  (`CConnection` 은 비가상 메서드를 `0x0050xxxx` 에 둘 수도 있으므로 단정하지 않는다.
   다만 문서 22 의 명명을 그대로 쓰면 [17] 의 두 스택 구분이 무너지므로 주의가 필요하다.)
  기능 자체(gethostbyname → socket → connect → WSAEventSelect(FD_CONNECT) → 대기)는 문서 22 서술 그대로 VERIFIED.

## [21] 남은 과제 — 이번 라운드에 **하지 못한 것**

정직하게 남긴다. 요청받은 3건 중 **1건만 완료**했다.

| 과제 | 상태 |
|---|---|
| ① `C2G/G2C` vs `S2C` 소켓 판정 | ★ **완료** — [17], 단일 연결로 VERIFIED |
| ② S→C 핸들러 ↔ opcode 표 완성 | **미완** |
| ③ [5] 42쌍이 Plaza 1.3.1 에 존재하는지 확인 | **미완** |

### ② 가 C→S 만큼 쉽지 않은 이유 — 구조적 차이 (부분 확인)
C→S 는 `CJSLogic` vtable 12슬롯이 **전부 얇은 래퍼**라 opcode 가 상수로 노출됐다([10]).
S→C 는 그런 단일 관문이 없다:
- 디스패처가 **여럿**이다([13] 의 `0x00613740` opcode 대역이 기존 문서의 `0x0007`/`0x00CE` 와 겹치지 않음).
- 수신 핸들러(`CGameManager::On*Ack`, `CJSLogic::Ack*`)는 `.ilk` 상 **전부 비가상**(`IAE`/`QAE`)이라
  vtable 슬롯 기법이 원리상 통하지 않는다([3]).
→ 남은 경로는 **수신 루프에서 디스패처를 전수 수집**한 뒤 각 핸들러가 읽는
  **필드 오프셋 패턴**으로 구조체를 대조하는 것뿐이다. 다음 라운드 1순위.

수신 링 버퍼 위치는 이번에 확보했다: `CClientPeer + 0x9360`, 300슬롯 × `0xa9`(169) B([17b]).
이것이 수신 경로 추적의 출발점이다.

### ③ 은 착수하지 못했다
[5] 의 42쌍은 여전히 **Naver 1.4 기준 VERIFIED / Plaza 1.3.1 기준 NOT VERIFIED** 다.
클래스 존재만 확인됐다(124개 공통 클래스에 전부 포함).
