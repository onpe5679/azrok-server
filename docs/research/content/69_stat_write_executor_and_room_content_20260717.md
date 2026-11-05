# 스탯 WRITE executor + 방 콘텐츠 매핑 (2026-07-17)

정적 분석(Ghidra, `Azrok_original.exe`). content/65 가 남긴 gap("sys.tmp 델타를 실제 스탯에
APPLY 하는 함수 미발견")을 해결. VERIFIED = 디컴파일 본문, INFERRED = 추론.

## 1. 스탯 WRITE executor (gap 해결, VERIFIED)

**액션 실행자 = `FUN_00596690`** @0x00596690 (thunk 0x004e0524). `__thiscall(logic, char* name, int actionId, uint param)`:
1. actionId → `FUN_00595eb0` (또는 name → `FUN_00595e10`) 로 sys.tmp 행 해석
2. **`FUN_005960e0(mgr, actionId, out[71])`** = sys.tmp 행 로더: 테이블 ptr=`*(mgr+0x865)`, 행
   stride 0x142(322B), 행수=`*(mgr+0x861)`, actionId 로 행 매칭, **델타 71개(int)를 행+0x26 에서 out 복사**
3. `FUN_005975b0` 보정
4. 루프 `for i in 0..0x47: FUN_005a4ba0(i, deltas[i])` ← 실제 기록

**실제 WRITE = `FUN_005a4ba0(logic, statIdx, delta)`** @0x005a4ba0 (VERIFIED):
```c
*(*(logic+0x5f4) + statIdx*0xc) += delta;   // 현재값에 델타 가산
// 그 후 min = 레코드+4, max = FUN_005a4a50(레코드+8) 로 클램프
```
- **스탯 배열 = `*(logic+0x5f4)`, stride 0xc, 레코드 12B = [+0 현재값][+4 최소/바닥][+8 최대/캡]**
  (content/65·INDEX 의 "logic+0x5f4, stride 0xc" 를 write 본문으로 확정)
- statIdx 유효 0..0x46(71개). **게이트(2026-07-18 정정, 본문 재검증)**: write 조건 =
  `(stat9[+0x6c]!=0) OR (idx!=2 AND idx∉[0x1f,0x27])`. 즉 **봉에너지(stat9)==0 이면 경험치(stat2)와
  스킬(31~39) 적립 차단**, 나머지는 정상. (구 서술 "또는 statIdx==2 또는 [0x1f,0x27]"는 의미 반대 → 정정.
  게임 메시지 "봉에너지 0이면 경험치 안 오름"의 구현. 상세 content/76.)
- 보조: `FUN_005a49b0`=스탯 READ, `FUN_005a4a50`=max getter(스탯9는 진화단계별 500/600/700).

**정정**: `DomainCode_EmitLocalEffect`@0x0059a6e0 는 이 경로가 **아니다**. 그건 소지품(음식/장난감/
체육/에너지 소비 아이템) 사용 경로이며 스탯은 도메인 서브객체 소비 + 네트워크(C→S 0x0D/0E/0F, content/66)로
처리. **케어/방 액션 스탯 적용은 FUN_00596690 → FUN_005a4ba0 로 별개** (content/66 §4 의 "이게 stat 델타
적용인가?" 물음의 답 = 아니오).

## 2. 디스패처 (FUN_00596690 호출자)

방 매니저 상태머신 `FUN_00561050` @0x00561050 (state `*(base+0x12905)`: 0셋업/1/2/3활동적용/4). case3 = FUN_0055e610.
- **`FUN_0055e610`** = 방 활동 루프. 디스크립터 테이블 `*(base+0x127cb)`, stride 0x13e(318B). 스텝: 타입@+0x98,
  **액션id@+0x9c**, 지속@+0x14, 애니@+0x18, 진행델타@+0x139. 타이머 만료 시 액션id를 FUN_00596690 적용.
- `FUN_0055ee30`(다음 스텝), `FUN_0055e580`(즉시), `FUN_00560d20`(action 0xc8/0xcc, 0xc9-0xe2→애니),
  `FUN_005d27c0`(요리 팝업 버튼 0x189-0x197→슬롯, state6→요리 action 0xd5), `FUN_005306d0`(프레임당 스탯 감쇠, action=-1).

## 3. 게이트

- 액션 가용성 `FUN_005a14d0(actionId)`: 진화단계(FUN_005465c0)≠0 필요; 아이템(0xd4/0xd1)→FUN_00598520, 그 외→FUN_00597de0.
- **`FUN_00597de0`** = 액션별 **스탯 임계 게이트 + 반응/음성 선택**. 예: 급식 0xcb/0xcf → stat idx12 vs 0x27.
  > **SUPERSEDED by 79.** `0xdc-0xe2`를 Gym 자연 운동으로 분류한 기존 결론은 틀렸다.
  > Gym은 `0xf6-0xfd`이며 `FUN_005a1b90(domain 2)` 경로를 사용한다.
- `FUN_00598520`(아이템 0xd1/0xd4/0xdb): stat idx3 임계.
- 방 진입 게이트: 대부분 **없음**(직접 level_load). 유일 = **Hansol방(code 0xb): `*(base+0x31c71)≠0` 필요**.

## 4. 방 카탈로그 (VERIFIED)

`GameManager_DispatchRoomCode`: room code → WMB → init:
| code | WMB | 방 | init |
|---|---|---|---|
| 0 | room.wmb | PatHouse | 100 |
| 1 | playroom.wmb | 놀이(MuryPlay) | 0x65 |
| 2 | gym.wmb | 체육(TeroGym) | 0x66 |
| 3 | magic.wmb | 마술 | 0x67 |
| **4** | **cook.wmb** | **주방(ArimCook)** | **0x68** |
| 5 | shop.wmb | 상점 | 0x69 |
| **6** | **library_1.wmb** | **도서관** | **0x6a** |
| 10 | ground.wmb | Plaza | |
| 0xb | hansol.wmb | (게이트) | |
| 0xc | OXQuiz.wmb | OX | |

`GameManager_ExecuteRoomInit`: 주방=FUN_00531fb0, 도서관=FUN_00532470, 체육=FUN_00531b10, 마술=FUN_00531d60, 놀이=FUN_005318c0 (5단계 로딩; step0 룸빌더 주방=FUN_00530b90 / 도서관=FUN_00530d70).

- **주방(요리)**: action 0xd5 = **레시피/모드 전이**(ModePairWriter_Import, 재료 id 4001-4005), 스탯 직접 증가 아님 —
  요리 결과물(음식)을 먹을 때 스탯 적용. UI HighCook_10..42, Exp_Cook.wis, 레시피 팝업 FUN_005d27c0(슬롯 15).
- **도서관**: 펫 read/study 애니(FUN_0054da10, 진화단계별 anim 0xc/0x19). Book%d.wis, PaziStudy.mp3.
- **체육(TeroGym)**: `0xf6/0xf7` 팔굽, `0xf8/0xf9/0xfa` 아령, `0xfb/0xfc/0xfd` 줄넘기.
  자연 미니게임 리워드는 `FUN_005a1b90(domain 2)`에서 적용되고 C→S `0x0007`을 즉시 저장한다(79).

## 5. 액션 id 부분 카탈로그

0xc9/0xcd 급식(+4exp) · 0xcb/0xcf 급식(+2exp) · 0xd1 아이템 · 0xd4/0xdb 아이템변형 · **0xd5 요리(레시피모드)** ·
0xd2/0xd3/0xd9/0xda 스탯게이트 · 0xdc-0xe2(비-Gym 그룹) · 0xe4-0xec 놀이 · 0xed-0xf5 마술 · **0xf6-0xfd Gym** · 0xc8(200)/0xcc.
(각 action id → 실제 델타는 sys.tmp 행(content/65)에서 조회 — executor 가 그 행을 그대로 적용함이 확정.)

## 확정 못한 것

1. ~~도서관 "책읽기" action id + sys.tmp 행~~ **→ 해결(2026-07-18, content/76 §4).** ★**독서는 두 종류로 분리**:
   ① **도서관 공부** = action **500(0x1f4)** → `FUN_0055e380` → 리워드엔진 `FUN_005a1b90(domain 0)` → **지식경험(stat30)+5**,
   봉에너지-5, 재미-5. **sys.tmp 아님**(리워드엔진 직접). ② **하우스 책장 독서** = sys.tmp "도서" 행
   (`도서,-5,-5,-5,15,0,10,10,-5`) → FUN_00596690 → **경험치(stat2)+10·재미+15·용변+10**, stat30 안 건드림.
   (즉 "재미+15/경험+10"은 하우스 독서, 도서관 지식경험과 별개.)
2. 방별 디스크립터 테이블(`*(base+0x127cb)`, stride 0x13e) 원본 출처(파일 vs 하드코딩) — step0 빌더 미해부.
3. sys.tmp 매니저 객체 정체(logic 자신 vs 별도 전역) — 테이블 [mgr+0x865]/카운트 [mgr+0x861] 확정, 소유 미확정.
4. 요리 결과물 → 음식 아이템 → 스탯 상세.

Related: [[content/65_action_stat_deltas_sys_lgc]] (sys.tmp 델타 — 이 문서가 적용 executor 완성),
[[content/66_shop_item_economy_and_money_offset]] (DomainCode 소지품 경로 구분), INDEX 로컬룸.
