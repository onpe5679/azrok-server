# 요리(cooking) 레시피 시스템 (2026-07-18)

> **SUPERSEDED in part by 128.** The `mode 6 = cooking` UI attribution is
> false: `FUN_005D27C0` mode 6 follows the `0xD5` selected-item removal path,
> not an oven recipe-output path. Preserve this document's catalogue/stat
> observations, but use `128_PAT_HOUSE_FOODMAKER_CLEAN_REPRO_20260718.md` for
> the corrected UI-branch evidence.

> **PARTIALLY SUPERSEDED by 120.** `0x0007/0x000A`가 inventory를 저장한다는 결론은 폐기합니다. 현재 확인된 요리 후 저장 wire는 inventory가 없는 C→S `0007`뿐이며, S→C `000A`는 75-u16 item registry입니다.

정적 분석(Ghidra, `Azrok_original.exe`) + lgc.tmp/Azrok.dat 파일 대조. 주방(cook.wmb, room4, init 0x68)의
요리 제작 메커니즘. 요리숙련 스탯 인덱스는 lgc.tmp 파일로 재검증, 열거 체인은 디컴파일 스팟검증. 
VERIFIED=디컴파일/파일, INFERRED=추론.

## 1. 요리 = 100% 로컬, 전용 opcode 없음 (VERIFIED)

- 요리 실행부 `FUN_005d27c0`(mode 6)은 `this=*(popup+0x4)=로컬 로직/펫 객체`(스탯배열 logic+0x5f4 소유자)에
  실행, **네트워크 전송 0**.
- 보강: `DomainCode_EmitLocalEffect`(0x0059a6e0)는 bucket 0/1/2/7만 C→S 0x0d/0e/0f 송신, **음식(3)·재료(4)는
  case 자체가 없음**(protocol/75·content/66 일치). 확인된 후속 저장은 C→S `0007`이지만 그 196B에는 inventory가 없습니다.
- **서버는 요리 진행 로직 재구현 불필요** — 클라 로컬. 다만 재료 소비·음식 생성의 영속 wire는 120의 live capture 전까지 NOT VERIFIED입니다.

## 2. 요리숙련 스탯 = lgc.tmp idx 40~54 (VERIFIED, 파일) — content/65 off-by-one 정정

lgc.tmp 직접 파싱: **요리숙련 = stat40(토스트경험)~stat54(김밥경험)**, 55=펫진화·56=펫(요리 아님).
- **기초** idx40~44 max **40**: 토스트40/베이컨41/삶은계42/샌드위43/국수44
- **중급** idx45~49 max **80**: 오믈렛45/크로아46/핫케익47/스파게48/볶음밥49
- **고급** idx50~54 max **120**: 소시지50/스프51/샐러드52/비빔밥53/김밥54
- ★ **content/65 §스탯표의 "41~55"는 off-by-one 오기 → 40~54로 정정 완료** (55=펫진화를 요리로 오분류하고 stat40 누락했던 것).

## 3. 레시피 = 런타임 컨테이너 열거 (하드코딩 테이블 아님, VERIFIED 메커니즘)

정적 레시피 배열(DAT_xxx) 없음. 요리 슬롯은 런타임에 컨테이너에서 채워짐:
- `FUN_005d0aa0`(요리 페이지) → `FUN_0059b200(out,20)` = `FUN_0059c150(out,20,1)` 썽크(스팟검증됨) =
  **컨테이너@logic+0x478 보유 아이템 열거** → `popup+0x72`(15슬롯 요리ID 배열)에 채움.
- 가용 슬롯 상한 = `FUN_0059d5e0(0)` = 가구 저장용량 룩업(DAT_006dfaf8: 냉장고 등급→5/10/15).
- 실행: `FUN_0059b7f0`(0x0059b7f0)이 `컨테이너@logic+0x382`에서 dishID 1개 소비(`FUN_0059be80`) → `logic->vtable[0](dishID)`.
- 그리드 = `FUN_005d1eb0`: **3행(티어)×5열(요리)=15**, slot=tier*5+col.
- 재료부족 실패("요리 재료가 부족합니다") = `FUN_0059be80`(0x0059be80)이 컨테이너 재고 0시 0 반환.

## 4. 샌드위치+삶은달걀 매핑 (INFERRED — 강함, lgc/Azrok.dat 이름 3중대조)

| 요리 | 요리숙련 stat | 음식 domain3 ID | 티어/재료 |
|---|---|---|---|
| **삶은달걀** | **stat42** (max40) | **1008** | 기초 / 재료 domain4 1500 |
| **샌드위치** | **stat43** (max40) | **1009** | 기초 / 재료 domain4 1500 |

기초 5종 = 토스트1006(stat40)/베이컨1007(41)/삶은달걀1008(42)/샌드위치1009(43)/국수1010(44), 초급재료1500 소비.
중급(45-49) 오믈렛1015~볶음밥1019/재료1501. 고급(50-54) 소시지1024~김밥1028/재료1502.
→ 현재 퀘스트 "샌드위치+삶은달걀 마스터" = stat42·stat43을 max40까지 올리는 것(3단계 성장 조건).

## 5. 서버 재구현 계약

- 요리 진행·제작에 서버 왕복 불필요. 레시피는 "보유 재료/음식 컨테이너 열거" 규칙(로컬).
- 서버는 C→S/S→C `0007`로 요리숙련 stat40-54(max40/80/120)를 왕복합니다. 음식/재료 inventory 왕복 wire는 **NOT VERIFIED**이며 현재 canonical 구현에 누락돼 있습니다(120).

## 확정 못한 것 (x32dbg — Codex 동적영역, 저비용 BP로 마감 가능)

1. **컨테이너 baseId**: 열거 logic+0x478 vs 소비 logic+0x382 각 baseId(음식1000 vs 재료1500) — CLogic 생성자
   미도달로 정적 미확정. → `FUN_0059be80`@0x0059be80 BP, `[this+0x15]`(baseId)·arg2(dishID) 덤프.
2. ~~요리숙련 증가 지점~~ **→ 해결(2026-07-18, content/76).** ★**요리숙련(stat40-54) 증가 = domain1 리워드엔진.**
   주방 조리 미니게임 완료 → `FUN_0055e380` case 0x68 → `FUN_005a1b90(domain1, foodId)` → 리매퍼 `FUN_005a8aa0`
   (@0x5a8aa0, 테이블 &DAT_006e0e70 33엔트리, 본인 재검증)가 **조리 음식id → 대상 숙련스탯** 매핑: **1006→40(토스트)
   … 1020→54(김밥)** = lgc.tmp 요리숙련 15개 정확일치. (1001-1005→stat29 인스턴트, 1000→-1 스킬없음.) 베이스 +5.
   sys.tmp 아님. 즉 "요리 만들기"가 곧 요리숙련 훈련이며, 봉에너지 게이트 대상 아님(stat40-54).
3. **숙련0→실패 게이트**: stat40-54 read 지점(mode3/5 또는 슬롯채움).

주요 주소: FUN_005d27c0(실행)·FUN_005d0aa0(페이지)·FUN_0059b200→FUN_0059c150(열거)·FUN_0059b7f0(소비실행)·
FUN_0059be80(재고체크)·FUN_0059d5e0(용량)·FUN_005d1eb0(그리드). 데이터: DAT_006dfaf8(가구용량).

Related: [[content/71_azrok_dat_item_catalog]](음식/재료 카탈로그), [[content/65_action_stat_deltas_sys_lgc]](허기델타·off-by-one 정정),
[[content/76_minigame_reward_engine_and_bong_energy_gate]](스탯 write), [[content/66_shop_item_economy_and_money_offset]](EmitLocalEffect), INDEX.
