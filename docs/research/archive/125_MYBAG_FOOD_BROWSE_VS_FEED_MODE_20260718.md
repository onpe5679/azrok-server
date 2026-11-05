# MyBag 음식 열람 모드와 실제 먹이기 모드 분리

> **SUPERSEDED by 649.** The description of event type2 as a generic release/click is superseded: the original dispatcher emits type2 only for a same-slot double-click within500ms. The browse/feed distinction and historical capture facts remain valid.

Date: 2026-07-18

## 결론

- **VERIFIED (static):** `메뉴 -> 내가방` 진입은 `CPopupMyBag + 0xB6`을 `0`으로 설정하는 일반 열람 경로입니다. 이 상태에서는 음식 슬롯을 눌러도 실제 먹이기 동작으로 이어지지 않습니다.
- **VERIFIED (static):** PatHouse의 `BtnEat` 버튼 ID `0x2B/0x2C`는 `CPopupMyBag + 0xB6 = 1`을 설정하고 food tab 0을 엽니다. `BtnEatStudy` ID `0x3D`도 같은 food-use flag를 켭니다.
- **VERIFIED (static):** MyBag food tab은 `Refri_0..Refri_32` 33개 자산을 로드하고, 현재 보유 food ID 목록을 최대 15개 슬롯 버튼 `0x189..0x197`에 배치합니다.
- **VERIFIED (static):** 슬롯의 release/click event(type 2)는 `FUN_005D27C0`으로 들어갑니다. food mode(`+0xB2 == 3`)에서는 `+0xB6 != 0`일 때만 선택 음식 ID를 `FUN_0055CFA0`에 넘기고 먹이기 애니메이션을 시작합니다.
- **VERIFIED (dynamic):** clean run `20260718T200538_52232_e3b06bea`에서 S2C `0007`과 자연 C2S `0008` 모두 food1001 수량 1을 확인했습니다. 일반 MyBag에서 햄버거 툴팁/클릭 후 C2S `0014`, 추가 `0008`, canonical food 변화는 없었습니다.
- **VERIFIED (natural live):** 사용자가 직접 `식탁 -> 식사 -> 첫 번째 슬롯`을 클릭하자 hamburger가 테이블에 나타나고 먹이기 동작이 완료됐습니다. wire는 `0014[e9 03] -> 0008(food1001 1->0) -> 0012[40,2] -> 0011 -> 0007` 순서였습니다.
- **VERIFIED (UI symptom):** 첫 슬롯은 겉보기에는 비어 있지만 hover tooltip에는 hamburger가 표시되고 클릭/섭취도 정상입니다. 따라서 소유 데이터·tooltip·hit target·소비 경로는 살아 있고 **슬롯 아이콘 body만 보이지 않는 렌더링 결함**입니다.
- **VERIFIED (second clean natural live):** 별도 격리 namespace에서 사용자가 동일한 첫 blank 슬롯을 실제 마우스로 다시 클릭했고 `0014 -> 0008 -> 0012 -> 0011 -> S2C0005/990 -> 0007`을 재현했습니다. blank slot이 click을 차단한다는 가설은 REFUTED입니다.
- **VERIFIED (not protocol):** `Refri_1.wis` 자산, S2C0007 food 수량, local item/tooltip 매핑, `View_Cook -> SetBmp`, C2S0014가 모두 확인됐습니다. 별도 icon server opcode는 없습니다.
- **NOT VERIFIED:** 슬롯 아이콘이 보이지 않는 정확한 client BMAP/alpha/draw 원인과 2011년 원본 환경 재현 여부는 아직 확정하지 않았습니다. 현대 Acknex/DirectX 환경 호환성 가능성이 높지만 INFERRED입니다.

## 직접 근거

### 메뉴 MyBag은 browse-only

`FUN_005CC5C0`의 MainMenu button `0xBD` 분기:

1. `FUN_0050BE70()`로 `CPopupMyBag`을 얻습니다.
2. `FUN_005CD020(0)`으로 `+0xB6`을 끕니다.
3. `FUN_005D02E0(5)`로 가방을 엽니다.

따라서 사용자가 메뉴에서 요리 탭으로 바꾼 뒤 햄버거를 눌러도 소비되지 않는 것은 서버 실패가 아니라 원본 클라이언트의 의도된 열람 모드입니다.

### 실제 먹이기 진입

`FUN_005E1090`은 다음 버튼 자산을 등록합니다.

- `0x2B`, `0x2C`: `Data\\button\\BtnEat*.wis`
- `0x3D`: `Data\\button\\BtnEatStudy*.wis`

`FUN_005E3EE0`의 `0x2B/0x2C` 및 `0x3D` 분기는 `FUN_005CD020(1)`을 호출하고 `FUN_005D02E0(0)`으로 food tab을 엽니다.

### 슬롯 렌더와 클릭

- `FUN_005CEE90`: `Data\\Inventory\\Food\\Refri_%d.wis`, index `0..32`를 전부 로드합니다.
- `FUN_005D0730`: 보유 food ID 목록을 조회하고 최대 15개를 슬롯 `0x189..0x197`에 연결합니다.
- `FUN_005CFCA0`: slot release/click event(type 2)를 확인한 뒤 조건이 맞으면 `FUN_005D27C0`을 호출합니다.
- `FUN_005D27C0`: food mode에서 `+0xB6`이 켜져 있을 때만 선택 ID와 애니메이션을 연결하고 플래그를 다시 0으로 내립니다.

## 동적 상태

- run: `20260718T200538_52232_e3b06bea`
- profile: `playable / profile_playable_v2`
- baseline canonical SHA: `d190456272d19d182fb9aa69f405373c31c13393f24a706ff190e71b35b0e31f`
- baseline: food1001=1, food sum=1, ingredient sum=0
- 일반 MyBag 클릭 결과: item packet 0, inventory delta 0, food transaction 0
- 탭 전환 부수 C2S `006C[00000000]`은 PatHouse pet/community toggle이며 inventory fetch가 아닙니다.

## 자연 먹이기 실측 종결

- 정확한 사용자 경로: `식탁 클릭 -> 식사 -> 첫 번째 빈칸처럼 보이는 슬롯`.
- seq339: C2S `0014[e903]` (food1001 action witness)
- seq340: C2S `0008`, food1001 `1 -> 0`
- seq341: C2S `0012[2800000002]` = FunCorn 40, reward channel 2
- seq342: C2S `0011`; 완료 행은 kind만 `0x00FF`, aux/value는 stale
- seq343: C2S `0007`

구 서버는 0008만 commit하고 0012를 무시했으며 stale-tail 0011을 거부했습니다. 이 후속 서버 결함과 원본 심볼/ACK 계약은 126에서 종결합니다.

## 2차 clean natural live와 표시 결함 정정

- run: `20260718T215018_108820_3f54c45a`
- seq135..140: `0014[e903] -> 0008[food0] -> 0012[40,2] -> 0011 -> S2C0005[0012,990] -> 0007`
- screenshot: `artifacts/dynamic-analysis/FUNCORN_ICON_QA_NATURAL_USER_CLICK_SUCCESS.png`
- 사용자의 실제 mouse hover/click은 정상 소비됐습니다. 자동 helper의 hover 없는 즉시 클릭이 한 차례 실패한 사실을 client hit-target 차단으로 일반화하면 안 됩니다.
- 표시 원인 경계와 clean restart는 127을 따릅니다.
