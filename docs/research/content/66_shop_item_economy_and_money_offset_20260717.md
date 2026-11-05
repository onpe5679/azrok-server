# 상점 · 아이템 · 소지금 (2026-07-17)

> **PARTIALLY SUPERSEDED by 98.** `FUN_005BBC00`은 general toy/gym 슬롯 producer가 아니라 furniture `model+0x334`/ID `0..32` 전용이고, `FUN_005BC970`은 energy UI입니다. shipped toy/gym UI에는 C2S `000D/000E` producer가 없습니다. sender body와 wire 형식 자체는 유효합니다.

정적 분석(Ghidra, `Azrok_original.exe`)으로 상점 경제 + 아이템 데이터 + **소지금 위치** 복원.
프로그램이 전부 thunk 처리돼(0x004Dxxxx) RTTI + thunk-caller 체인으로 항해. VERIFIED = 디컴파일
본문, INFERRED = 추론.

## ★ 소지금(money) = model + 0x1F0 (VERIFIED) — INDEX "money 미발견" 해결

구매 검증 `FUN_005a95b0` @ `0x005A95B0`:
```c
// Azrok.dat 가격 합산 → cost
if (*(int *)(model + 0x1F0) < cost) return -1;   // 자금 부족
// 이후 도메인 용량(-2..-5), 중복 소비재(-100) 체크, else cost 반환
```
- **소지금 = `[model + 0x1F0]`.** `model = *(CPopupItemShop + 0x4)` = 플레이어 데이터/네트워크 객체.
  8 인벤토리 도메인 서브객체(food@+0x334, toy@+0x3D4, gym@+0x426, energy@+0x3AB) + 스탯 서브객체
  보유. `DomainCode_EmitLocalEffect`의 this 와 동일.
- 오프셋 +0x1F0 VERIFIED. **절대주소/전역명은 x32dbg 필요**: bp `0x005A95B0`, read `ECX(=model)+0x1F0`.
  model 이 localPlayer/gm/logic 중 무엇인지 확인하면 컨트롤 패널 워치로 상시 판독 가능(값 확인 가치).

## 1. 상점 시스템 — 로컬 씬 (VERIFIED)

- 클래스: CPanelManager ⊃ CInventory ⊃ CPopupItemShop. RTTI `.?AVCPopupItemShop@@`@0x006e1848,
  vtable@0x006a88cc. CPopupItemShop 은 CInventory+0x378.
- **로컬 씬**(팝업링 아님): bootstrap `FUN_004ecab0` 가 `add_folder("Data\Space\ItemShop")`.
  자산 shop.wmb, `Data\sound\BingbingShop.mp3`, `Data\Inventory\ItemShop\*.wis`(Buy/Cart/Drop/…).
- **서버 독립 카탈로그** (INFERRED, 강): S2C 핸들러가 0x00-0x71+0x03E8 전부인데 상점-카탈로그 opcode
  없음. 가격은 로컬 Azrok.dat.
- 클릭 디스패처 = vtable slot6 `FUN_005c3f50`. 버튼 ID: 0x13A 닫기 · 0x13B 카트 · 0x13C 버리기 ·
  0x13D 되돌리기 · **0x13E 구매 → FUN_005c8620** · 0x141-0x14C 카테고리 탭 · 0x14D-0x179 아이템 슬롯.
- 탭 → 도메인 코드 3(가구)/4(재료)/1(장난감)/2(체육)/5(책)/6(약). 음식(0)/에너지(7)는 상점 탭 아님.

## 2. 아이템 데이터 — Azrok.dat (VERIFIED)

- 아이템 .csv/.txt 없음. 정의는 Azrok.dat, item ID 로 조회. finder `FUN_0061fcd0`.
  레코드: domain @+0x8, **가격 @+0x44**. 가격 API `FUN_005aa300(bucket,itemID)` → price/-1.
- **아이템 ID → 도메인 범위** (`DomainCode_ClassifyBucket`@0x0059a460):
  **⚠ 가구 0-32 · 음식 1000-1032** · 재료 1500-1502 · 장난감 2000-2009 · 체육 2500-2507 · 책 3000 ·
  약 4000-4005 · 에너지 5000-5002. (⚠ 가구↔음식 라벨은 content/71 Azrok.dat 파일 파싱으로 정정;
  DomainCode 범위 숫자 자체는 정확. 도메인별 아이템 수: dom0 33/dom4 3/dom1 10/dom2 8/dom5 1/dom6 6/dom7 3.)

## 3. 구매/판매 프로토콜 (VERIFIED)

- **★ 상점 = 구매 전용, 판매(sell) 경로 없음 (2026-07-18 완결, VERIFIED).** 카트/버리기/되돌리기는 전부 로컬 상태 조작이고
  **네트워크 전송은 구매 확정 45B 딱 하나뿐.**
- **클릭 디스패처 `FUN_005c3f50`**(vtable slot6): button id + click type(2=우클릭). 아이템슬롯 **좌클릭=선택만(FUN_005c6ee0)**,
  **우클릭=행동**(0x14d-15b→카트담기, 0x16b-179→버리기). 0x13A 닫기·0x13B 카트담기·0x13C 버리기·0x13D 되돌리기·0x13E 구매·0x141-14c 탭.
- **카트담기 `FUN_005c76c0`**(0x13B): 선택→검증(FUN_005a95b0)→성공시 진열(+0x136)→카트(+0x460) 이동. 실패시 롤백+에러패널. **로컬.**
- **버리기 `FUN_005c7ed0`**(0x13C): 카트 아이템 제거(FUN_005c7570)→진열대 복원(FUN_005c7fc0). **판매 아님, 로컬(패킷 없음).**
- **되돌리기 `FUN_005c8460`**(0x13D): 순수 UI 리셋(선택/카트 원복, 첫 탭 복귀). **로컬.**
- **구매 커밋 `FUN_005a9a10`**: `ECX=model=*(shop+0x4)`(네트워크 객체, shop 자신 아님) → **45바이트(0x2D) 패킷 = [+0 count:u8][+1 cost:u32][+5 itemId:u16 ×20]**,
  `model->vtable[+0x2C](buf, 0x2D)` @0x005A9AB7 로 전송. **구매 C→S opcode = 폴리모픽 슬롯이라 정적 미확정**(x32dbg bp 0x005A9AB7, CALL EAX).
- **★ 소지금(model+0x1F0) 즉시 차감 안 함** — 전송 후 `FUN_005a9540(1,cost)`가 락(this+0x808=1, 응답대기) 설정, **서버 응답으로 확정**.
  즉 구매는 낙관적 반영 아니라 **서버 권위**. (중복전송 방지: FUN_005a95b0 첫 줄에서 락이면 cost=0.)
- **검증 `FUN_005a95b0` 반환코드**(본인 재검증): **>0=총비용** · 0=무료/빈카트/구매중 · **-1=소지금<비용** · -2/-3=가구·음식·재료 용량초과 · -4=장난감·체육 용량초과 · -5=책 용량초과 · **-100=중복불가 아이템 중복**.
  - **bucket 0/1/2/5(가구·장난감·체육·책)=유니크(중복시 -100)**, **3/4/6(음식·재료·약)=스택 허용**. 용량 = FUN_00598ca0(현재)+신규 vs FUN_0059b7d0(최대).

## 4. 인벤토리 추가 / 아이템 사용 (VERIFIED)

- 구매 시 인벤토리 추가 = **서버 권위** (INFERRED): 클라 인벤토리 write 없음. 서버가 소지금 차감+아이템
  추가 후 S→C 0x0007/0x000A 로 리싱크.
- 아이템 사용 `DomainCode_EmitLocalEffect` @0x0059a6e0 (this=model, `model->vtable[+0x8]`로 전송).
  **⚠ 정정(2026-07-18 디컴파일 재확인):** switch(bucket) 는 **case 0/1/2/7 만** 처리 —
  `DomainCode_ClassifyBucket` 지상진실로 bucket0=가구·1=장난감·2=체육·7=에너지 (66§2 표와 일치):
  - **가구(0): 로컬, 패킷 없음. 스탯델타 아님 → 보관용량 세팅** (`FUN_0059ab40`=`*(model+0x19)=cap`).
    냉장고=음식보관, 금고=장난감/운동기구 2종 용량(이중 호출), 책꽂이=책 용량(단일). (구 "음식0/스탯델타"는 오류)
  - **장난감(1): C→S 0x0D (4B)** @0x0059A8CD · **체육(2): C→S 0x0E (3B)** @0x0059A926 ·
    **에너지(7): C→S 0x0F (1B)** @0x0059A991. opcode 는 콜사이트 하드코딩.
  - **음식(3)/재료(4)/책(5)/약(6)은 EmitLocalEffect 에 case 없음** → 소비재는 별도 경로:
    음식=주방 식사 액션(sys.tmp 허기델타, content/65/69), **약=서버권위 추정**(EmitLocalEffect 호출자에
    `HandleS2C_0007_LoadSetupBlob`@0x0059e330 포함 → 0x0007 블롭 계열; 정확 경로 미확정, Codex 0x0007 영역과 겹쳐 보류).
- EmitLocalEffect 호출자(thunk 0x004d746a xref): `HandleS2C_0007_LoadSetupBlob`@0059e330,
  인벤토리 슬롯핸들러 `FUN_005bbc00`(버튼0xee-0x103)·`FUN_005bc970`(버튼0x104-0x107).

## 5. C→S opcode 맵 (send `FUN_00593d10` caller 열거, VERIFIED)

- 핸드셰이크/셋업(`FUN_0059d760` 계열): 0x03,0x04,0x05,0x06,0x10,0x11,0x12,0x13,0x14,0x15,0x17
  → **해결(protocol/82): `FUN_0059d760(op,0,0)` = 빈페이로드 전환 ack(C→S 0x01/0x02), 0x16은 시간동기 핑(1B)/하트비트. 전체 연결 부트스트랩은 protocol/82.**
- 아이템사용(model vtable+0x8): 0x0D,0x0E,0x0F
- 기타: 0x16 heartbeat, 0x18 펫 상호작용, **0x19 문 클릭**(FUN_00594820), 0x00 & 0x68 채팅
- 액터/멀티(`FUN_005ab6a0` 계열): 0x64,0x65,0x66,0x67,0x69,0x6A,0x6B,0x6C · 0xC8(200) 씬 진입

## 확정 못한 것 (정적 한계 — x32dbg 필요)

1. 정확한 구매 opcode (런타임 폴리모픽) → x32dbg bp 0x005A9AB7
2. money 객체(model) 절대주소/전역명 → x32dbg bp 0x005A95B0, ECX+0x1F0. model==localPlayer/gm/logic 확인
3. 카탈로그 아이템 목록이 하드코딩인지 Azrok.dat 열거인지 (popup+0x136 로더 미확정)
4. ~~Drop/RollBack 정확한 프로토콜~~ **→ 해결(§3): 버리기/되돌리기/카트 전부 로컬(패킷 없음), 판매경로 부재.**

> **ITEM-USE COMPLETED by 90.** 0x0D/0x0E는 수량 소비가 아닌 toy4/gym3 active loadout snapshot이고, 0x0F energy만 서버 canonical 차감 성공 뒤 S→C0009 `00 0F`로 소비를 확정합니다.

Related: [[content/65_action_stat_deltas_sys_lgc]], [[content/57_content_state_contract_audit]],
[[content/58_quest_money_data_source]] (money 미발견을 이 문서가 해결), INDEX.
