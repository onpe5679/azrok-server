# 완성도 감사 — 놓쳤던 컨텐츠 시스템 (2026-07-18)

**목적**: "전 기능 플레이 가능?" 최종점검. 병렬 정적 스윕(RTTI 클래스명 + 에셋경로 문자열)으로 **지금까지 문서화
안 된 컨텐츠 시스템**을 발굴. 액세서리 시스템은 **Claude가 search_strings로 직접 재검증**(문자열 실재 확인).
VERIFIED=문자열/RTTI 직접 리드, INFERRED=아키텍처 추론, NOT VERIFIED=Codex 동적확인 필요.
바이너리 Ver. PLAZA 1.3.1 @006ad4c0.

## ★ P1. 꾸미기/액세서리/탈것 시스템 (완전 미문서화, 대형) — VERIFIED

`CPopupAccessory`@006e16ec, `CMountItem`@006d9ccc, 메뉴 accessories 버튼 @006a9500.
- **패널 `Data\Interface\Accessory\`** (search_strings 82개 확인): 탭 **toy%d(장난감)/back%d(등)/weather%d(날씨효과)**,
  버튼 상태 mount(착용)/click/down/over/normal, **`Not*` 접두 = 미보유 잠금슬롯**.
- **3D 착용모델 `Data\Plaza\Mount\` (`%s_`=종족코드)**:
  - 얼굴/머리: **`%s_GLASSES.mdl`·`%s_SUNGLASSES.mdl`(★관측된 안경 착용의 정체 확정)**, MASK, SANTA_HEADGEAR, RUDOLPH_HEADGEAR, MortarBoard(졸업모자), SUJANG
  - 등: WING, BAG, SANTA_BAG, TURTLESHELL, ANGEL, ANGELRING
  - weather(머리위 장식이펙트): snowcloud, RAIN, RAINBOW, SUN, LIGHTING, Moon&Star, HEART (★Plaza 무지개/눈 장식의 정체)
  - **탈것(Mount)**: MiniCar, BookCart, Kite, Cat, Dog, Penguin, PIG, DUCK — Plaza에서 펫이 탐
- **서버 함의(INFERRED 강함)**: 착용상태는 인벤토리 아이템 + 멀티 액터릴레이로 타유저에 전파. → **계약서 84에 없던 새 서버 책임**(착용 slot 영속 + Plaza 렌더 relay). Codex로 착용 시 패킷 실측 필요.

## P2. 달력/낮밤·시간대 + 눈 연출 (미문서화) — VERIFIED

`CPopupCalendar`@006e172c. `Data\Interface\Calendar`(확인): DayTime%d(시간대), SunMoon_%d(해/달=낮밤), 날짜.
- 눈 = 파티클 `eff_FallingSnow`@006d0e34 + Snow_1.tga → "눈 쌓인 광장"의 정체. 동적 날씨엔진 아니라 개별 파티클 연출.
- `CJSScheduler`@006dfa28 = 서버 스케줄/이벤트 시각 로직 추정. 산타/루돌프 아이템군 = 시즌이벤트 가능성(INFERRED).
- **★ 해결(2026-07-18, 본인 재검증): 시간/달력 = 100% 로컬 코스메틱, 서버 시간/계절 층 불필요.**
  - 시각 = `FUN_005b61f0`이 로컬 게임값(`FUN_00653b50`)+GetTickCount로 계산(**GetLocalTime도 서버recv도 아님**, hour=arg/60*24). 낮밤플래그(obj+0xd4) 6~19시=낮, 달력UI 내부에만—스탯/이벤트 전파 없음(게임플레이 무영향). Plaza시계는 2.5초 순환 장식 애니메이션. GetLocalTime은 스크린샷 파일명 전용.
  - **★"눈"=계절 아니라 액세서리**: snowcloud.MDL=Mount 아이템 0x2717(슬롯0 value7), FUN_00521ff0가 펫에 부착. 전역 날씨엔진·계절토글·시즌이벤트 **없음**. 산타/루돌프도 코스메틱 액세서리. → **content/107 액세서리 층에 흡수**(별도 계절 층 0).
  - CJSScheduler = 계절/스케줄 데이터파일 전무 → 로컬 인메모리 타이머 추정(INFERRED).

## P3. NPC 상호작용 (미문서화) — VERIFIED

`CPopupOutMapNPC`@006e42b4, `CPopupOutMapBingBing`@006e41ec(상점NPC 빙빙테리우스, bingbing.mdl), `CPopupOXNPC`@006e4470.
- **`.npc` 데이터파일 포맷**: `Data\Plaza\bee.npc`@006a6a7c(클라측 NPC 정의). 모델 HoneyBee/Kingk.mdl, 말풍선 TalkingBubble.
- Plaza 스태프/GM: staff.MDL, GM_ICON. NPC 대사 출처(.npc 로컬 vs 서버) = NOT VERIFIED.

## P4. 진화 트리 (VERIFIED, ⚠ 이름 매핑 미해결)

`Data\Temp_Character\`: **내부 종족 4계열 = TERO / PAZ / ABO / ARK**. 각 **알→1→2→3→4단계** 모델(Tero1..Tero4 등),
HeadPet 변종 HP_%s_%d(단계별 머리펫). 진화이펙트 eff_EvolUp1~9@006d0dc8.
- **⚠ 표시명↔내부코드 불일치**: 관측명(새지/아링/테로/블루론/레드론) ↔ 내부(TERO/PAZ/ABO/ARK) 1:1 안 맞음.
  - 표시명 힌트: UserInfo 초상 = **Tero/Sagi/Aring/Mury**, 액세서리 프리뷰 = Tero/Paz/Aring/Muze.
  - 추정(INFERRED): 테로=TERO, 아링=ABO, 새지≈Sagi=PAZ, ?=ARK(Mury). **"블루론/레드론"은 정적 문자열 미확인**
    = 색상변종 명칭이 데이터파일(init.csv/lgc.tmp) 또는 CP949 한글문자열에 있을 가능성. → 데이터파일 확인 필요.

## P5. 그 외 발견 (VERIFIED RTTI/에셋)

- **캐릭터 생성/이름짓기**: `CPopupSelectEgg`@006e439c(CreatePet_ch0~3=4종족 선택, EggProfile, **NameBoard=이름짓기**), `CPopupSelectPet`@006e43c0(SelectPet_ch0~3=최대 4슬롯, **PetDel_Pan**, EnterPlaza). → 서버 계정에 종족·이름·슬롯 영속.
- **Plaza 소셜/유저정보**: `CPopupUserInfo`@006e456c(타유저 클릭→ BtnWhisper/BtnInfo/gage + 종족초상). 서버의존.
- **구역명** CPopupSpaceName@006e4548, **미니맵/줌** CPopupMiniMap@006e444c.
- **펫 속성 시스템**: `CViewProperty`@006dd2c0 + `CJSProperty`@006dfa08(m_jsProperty[%d].nMax 다중속성배열, 서버 JS구동).
- **Magic방 재주**: AirHook/FunnyShild(방어막)/MagicClon(분신)@006aaf08.
- **Know방 지식학습**: PaziKnow\Study, **Exp_Know(지식경험)가 Exp_Cook(요리경험)과 별개 트랙 = 이중경험치** (content/76 stat30 지식 ↔ stat40-54 요리와 일치).
- **RingCommand**: CPopupRingCommand@006e4374(펫 행동 방사메뉴 추정, RTTI만).
- **공지/옵션**: CPopupNotice@006e418c, CPopupOption. `CStory`@006dd288, `CJSMarumong`@006dfa48("마루몽"=펫개체 총칭 가능성 INFERRED).

## 없음 확인 (부재 = VERIFIED 범위 내)

- **친구/버디 목록 없음** — Friend/Buddy 문자열·클래스 전무. 소셜 = Plaza 클릭→귓속말+정보뿐.
- **업적/도감/수집앨범 전용시스템 미발견** — Album/Card/Collection/Gallery 문자열 없음(완전부재 단정은 NOT VERIFIED).
- **동적 날씨엔진 없음** — weather = 액세서리 장식 파티클.

## 계약서 84 갱신 함의 (서버 새 책임)

기존 5층 + OX에 더해 **놓쳤던 서버 관여 컨텐츠**:
- **액세서리/탈것 착용상태**: 인벤토리 + 착용 slot 영속(0x0007 계열?) + Plaza 멀티 relay. (가장 큰 신규 항목)
- **캐릭터 생성 계약**: 종족(4계열)·이름·슬롯(최대4) 영속 — Codex가 이미 일부 구현(생성/삭제).
- **유저정보/귓속말**: Plaza 타유저 클릭 → 서버 조회.
- **달력/시간**: 서버시각 권위 여부 확인 필요.

## Codex(동적) 확인 항목

1. 액세서리 착용 → 서버 패킷 유무·레이아웃 (가장 중요)
2. SunMoon/DayTime = 로컬시계 vs 서버시각
3. NPC 대사 출처(.npc 로컬 vs 서버)
4. 종족 표시명(블루론/레드론)↔내부코드(TERO/PAZ/ABO/ARK) 매핑 (데이터파일/런타임 문자열)
5. CJSScheduler가 계절/눈을 서버플래그로 토글하는지

Related: content/84(서버계약 — 액세서리 층 추가 필요), content/76(이중경험 stat30/40-54), world/70(씬맵), 튜토리얼은 별도(tutorial-probe 진행중), INDEX.
