# 질병 시스템 — mode-pair 저장 + 발병/치료 로컬 진행 (2026-07-18)

> **PARTIALLY SUPERSEDED by 86.** §2의 "로컬 발병 writer 없음"과 §5의 "서버 발병 판정"은 반증됐습니다. `FUN_005AA850`이 group5/6/7을 로컬 게임시계로 1→2→3 진행하며 서버는 C→S 0007 결과 저장/복원만 담당합니다.

정적 분석(Ghidra, `Azrok_original.exe`). content/71 §5의 미해결(질병 플래그 위치·발병 트리거·동기 opcode)을 해결.
**setter ModePairWriter_Import는 Claude 본인 디컴파일 재검증**(바이트 일치). 0x0007 블롭 내부 스키마는 Codex 영역
(동기화 지점만 표기). VERIFIED=디컴파일 본문, INFERRED=추론.

## 1. 질병 저장소 = mode-pair 배열 (VERIFIED) — content/71 미해결 해결

- **저장 = `*(logic + 0x6c8 + group*8)`** = {상태@+0(int), 타임스탬프@+4(=+0x6cc, packed date)}. **8그룹(0-7).**
  getter `FUN_005aa770`@0x5aa770, setter `ModePairWriter_Import`@0x5aa6f0.
- **질병 그룹 = 5, 6, 7** (3 카테고리). **57 스탯배열(logic+0x5f4) 밖** = content/71 "질병은 lgc스탯에 없음=별도 런타임필드" 확정.
- **상태값**: 0=초기 · 1=건강/치료됨 · 2=경증 · 3=중증.
- **★아기 중증 면역**(본인 재검증): `ModePairWriter_Import` 첫줄 — 진화단계(`FUN_005465c0`=logic+0x130)==0(아기) AND 들어온 상태>1 이면 **2(경증)로 강등**. 즉 아기는 중증(3) 못 걸림.
- ⚠ **혼동 금지**: `logic+0x70c`(10슬롯 {type,id,expiry}, rand()%100<61% 롤)는 질병 아님 = **음식 갈망/퀘스트 시스템**(content/78). 질병(0x6c8)과 별개 구조.

## 2. 발병/진행 = 로컬 게임시계 (VERIFIED, 86 정정)

- `mode0 per-frame 00594590→0059D2A0→FUN_005AA850`이 `DAT_006E1498`을 평가해 직접 state1→2→3을 씁니다.
- group5: stat4 < stat12-40, group6: stat7>80, group7: stat29>90.
- 조건 활성 시 state1, 게임시간18h 후 state2, 36h 후 state3. clock은 20초마다 1h 전진합니다.
- **동기화 = S→C 0x0007** (`HandleS2C_0007_LoadSetupBlob`@0x0059e330, 임포트 루프만 — 블롭 내부는 Codex):
  ```
  for(i=0;i<8;i++) ModePairWriter_Import(i, blob[0x184+i], blob[0x18c+i*4]);
  ```
  → **블롭 offset 0x184**(8바이트=그룹0-7 상태), **0x18c**(8 dword=타임스탬프). 서버는 저장한 결과를 재접속 때 복원합니다.
- **질병 전용 패킷 없음** — 범용 0x0007 상태블롭에 편승.
- C→S는 mode `+0x9C`, date `+0xA4`; group5/6/7은 mode `+A1/+A2/+A3`, date `+B8/+BC/+C0`입니다.

## 3. 치료 = 로컬 (VERIFIED)

- **약(bucket6, id 4000-4005)은 EmitLocalEffect에 case 없음**(재확인). → 약 = **먹이기(feed) 액션**: `FUN_00596690` action **0xd5(213)**, param_4=약 id:
  ```
  4000/4001 → group5: state==2(경증약4000)/==3(중증약4001)일때만 → state=1(치료)
  4002/4003 → group6: 동일 → state=1, + *(statbase+0x54)=0   (stat7 스트레스 리셋)
  4004/4005 → group7: 동일 → state=1, + *(statbase+0x15c)=0  (stat29 인스턴트 리셋)
  ```
- **★중증도 일치 필수**: 경증약(4000/2/4)은 상태==2일때만, 중증약(4001/3/5)은 상태==3일때만 작동. 불일치 = 무효.
- 치료 후 클라가 mode-pair→1 즉시 세팅, 이후 **C→S 0x0007 저장**(Codex 영역)으로 영속화.
- group6/7 치료는 원인 누적치(스트레스/인스턴트)도 0으로 리셋 = 재발 방지.

## 4. 6질병 ↔ 3그룹×2중증도 (INFERRED, 드라이버 근거)

| group | 중증도 | 약 id | 질병(content/71 이름) | 근거 |
|---|---|---|---|---|
| 5 | 경증/중증 | 4000/4001 | 감기/독감 | 누적리셋 없음(호흡기, 위생/에너지 추정) |
| 6 | 경증/중증 | 4002/4003 | 두통/신경병 | **스트레스(stat7) 리셋** |
| 7 | 경증/중증 | 4004/4005 | 위장/위염 | **인스턴트(stat29) 리셋** = 즉석식품 과다 |

(경증70골드/중증200골드 = content/71/78. group↔정확한 이름은 Azrok.dat 약 effect 문자열로 x32dbg 확정 필요.)

## 5. 표시 자산 (VERIFIED 파일명)

`%s_sick_%d.wis`(sick 오버레이, %d=질병 인덱스), cold_paz/ark/abo/tero.ogg(종별 감기 소리), cold1/cold2 애니(`FUN_0054da10` anim idx3).

## 서버 재구현 계약

- 서버는 로컬 발병/치료 뒤 C→S0007 결과를 저장하고 S→C0007로 복원합니다. 독자 wall-clock 판정과 즉시 echo는 금지합니다.
- 신규 mode/date는 0×8입니다. 0xFF sentinel은 없고 과거 `state2×8/date0×8` 오염은 fresh0으로 migration합니다.
- 8 mode-pair 중 5/6/7=질병, 나머지(0-4)는 다른 용도(미확정).

## 확정 못한 것 (x32dbg)

1. group↔질병명(감기/독감…) = Azrok.dat 약 effect 문자열 대조.
2. mode-pair 0-4의 용도(질병 아닌 나머지 그룹).
3. 약 먹이기 UI 트리거(어느 버튼→action 0xd5).

Related: [[content/71_azrok_dat_item_catalog]](질병6종·약 카탈로그, §5 미해결 해결), [[content/78_quest_evaluation_reward_and_corn_currency]](logic+0x70c 갈망/퀘스트=질병과 별개),
[[content/66_shop_item_economy_and_money_offset]](약 bucket6), protocol/82(0x0007 동기화), INDEX.
