# 꾸미기/액세서리/탈것 — 서버 계약 (2026-07-18)

> **SUPERSEDED by 109.** `0x0018` shared/b0 미확정 및 `0x0066`만으로 중계한다는 결론은 원본 바이너리 직접 재검증으로 폐기되었습니다. 역사적 조사 기록으로 보존합니다.

**목적**: content/103이 발견한 "놓친 액세서리 시스템"을 **서버 구현 가능한 계약**으로 확정. 정적 디컴파일.
**저장 오프셋(PlayerState+0x1D8)은 Claude가 getter 직접 디컴파일로 재검증**(바이트 일치). VERIFIED=디컴파일,
INFERRED=추론, NOT VERIFIED=Codex 동적확인.

## ★ 결론: 캐릭터당 4바이트만 저장하면 됨

액세서리·탈것 = **단일 4슬롯 시스템**. 카탈로그·모델명은 **전부 클라 하드코딩**(서버 불필요). 서버는
**4바이트(슬롯0..3)를 저장/복원/중계**만 하면 됨.

## 1. 4슬롯 카탈로그 (클라 하드코딩, VERIFIED) — 로더 FUN_00521ff0 / 인덱서 FUN_00521e90

| 슬롯 | 종류 | 값 범위 | 아이템(값 순서) | 모델 |
|---|---|---|---|---|
| **0** | 머리위/후광 효과 | 0-9 | SUN·RAIN·RAINBOW·LIGHTING·ANGELRING·HEART·ANGEL·snowcloud·Moon&Star·MortarBoard | 종족무관 고정 |
| **1** | 얼굴/머리 착용 | 0-6 | GLASSES·SUNGLASSES2·SUNGLASSES·MASK·SUJANG(단계3게이트)·SANTA_HEADGEAR·RUDOLPH_HEADGEAR | 종족+단계별 |
| **2** | 등 착용 | 0-3 | BAG·TURTLESHELL·WING·SANTA_BAG | 종족+단계별 |
| **3** | 탈것(ride) | 0-7 | DUCK·PIG·Penguin·Dog·Cat·Kite·BookCart·MiniCar | 종족무관 고정 |

- **값 `0xFF` = 해당 슬롯 비움**(언마운트 FUN_00522ae0). ★관측된 안경 = 슬롯1 값0/1/2(GLASSES류).
- 경로: `Data\Plaza\Mount\` + 종족접두(0 P_AK/1 P_AO/2 P_PZ/3 P_TO) + 단계접미(0·1 _R/2 _S/3 _G/4 _M) + 액세서리명. 슬롯1·2만 종족+단계 메시.
- **★탈것 = 별도 아니라 액세서리 슬롯3** (동일 시스템).

## 2. 착용상태 저장 = 4슬롯, 다중착용 (VERIFIED, 본인 재검증)

- **런타임: `PlayerState + 0x1D8` [4 dwords]** (슬롯0..3). getter `FUN_005ab2b0(slot)=*(this+0x1D8+slot*4)` (Claude 재검증).
- 렌더용 액터 필드: `Actor + 0x314..0x317` [4 bytes].
- **동시 착용 최대 4개**(머리효과+얼굴+등+탈것, 슬롯당 1개).

## 3. 서버 동기 3채널 (전부 VERIFIED)

**(a) 착용 송신 C→S `0x18` [3 bytes]** ← ★새 발견, 패킷 있음
- 커밋 FUN_005b2970 → FUN_005ab900(b0,slot,value) → send(0x18, buf, 3). 레이아웃 **[b0=kind/context(0/1) · b1=slot(0-3) · b2=value(0xFF=해제)]**.
- ⚠ **content/80 정정**: 0x18을 "펫재주 전용"으로 봤으나 **액세서리 착용도 0x18 공유**(b0로 구분 추정, b0 의미는 x32dbg).

**(b) self 복원 S→C `0x0007` blob `+0x1D4` [4 bytes]** — `DomainSelector_ImportByteVector4`@0x005AB080 → state+0x1D8.
- ⚠ **정정(구 doc49/21)**: 0x0007 `+0x1D4`를 "domain selector vector"로 라벨했으나 **실제=착용 액세서리 4슬롯**.

**(c) 타유저 중계 S→C `0x0066` 레코드 `+0x14..0x17` [4 bytes]** — RemoteActor_InitFrom0066Record@0x005243E0.
- ⚠ **0x0066 레코드 구조 완성(구 doc21 불완전)**: stride **0x1A** = `[kind1 | actor_id4 | 종족변형1@+5 | 외형1@+6 | name13@+7 | acc_slot0..3 4@+0x14 | pairL1@+0x18 | pairR1@+0x19]`. (기존 표는 name·accessory 누락)

## 4. 중요 제약 (VERIFIED)

- **C→S 0x0007 표준 저장(196B, PlayerState+0x5F8, FUN_005a4770)은 액세서리(+0x1D8) 미포함.** → 서버는 **C→S 0x18로 받은 값을
  프로필에 직접 반영**하고(로컬-only 저장 추정은 반증), 그걸 다음 S→C 0x0007 `+0x1D4` / 0x0066 `+0x14`에 실어야 함.
- **S→C 0x69(action-state)는 액세서리 슬롯 미갱신** → mid-session 착용변경을 기존 뷰어에 보이려면 재스폰(0067제거+0066추가) 필요 추정(NOT VERIFIED, Codex).
- C→S 0x0064(부트스트랩)은 1바이트 상태만, 외형은 0064로 안 나감(로컬 self 적용만).

## ★ 서버가 해야 할 것 (계약 = 계약서 84의 신규 6번째 층)

1. 캐릭터당 **액세서리 4바이트 저장**(0xFF=빈; 범위 slot0:0-9/1:0-6/2:0-3/3:0-7). 범위밖·미보유 거부(fail-closed).
2. 로그인: **S→C 0x0007 `+0x1D4`에 4바이트** 복원.
3. 스폰/로스터: 각 액터 **S→C 0x0066 `+0x14..0x17`에 4바이트** 중계.
4. **C→S 0x18 [b0,slot,value]** 수신 → 슬롯 갱신+영속. (0x18은 펫재주 공유 → b0 분기 파서 필요.)
5. 카탈로그·모델명 = 클라, 서버 불필요.

## 확정 못한 것 (x32dbg — Codex)

1. C→S 0x18 b0(0/1) 의미 + 액세서리 vs 펫재주 판별 바이트.
2. ~~보유/획득 소스~~ **→ 해결(2026-07-18, 본인 재검증).** ★**소유목록은 저장 안 됨 — 스탯 마일스톤 라이브 계산.**
   게이트 `FUN_005b2cb0(resIdx)`@0x005b2cb0 = 1(해금)/0(잠금)(펫재주와 공유):
   - **tier1 기본해금**(신규캐릭 즉시): 슬롯0 기본날씨효과·슬롯1 산타/루돌프·슬롯2 SANTA_BAG·슬롯3 Kite/BookCart/MiniCar.
   - **tier2 직접 스탯임계**: PIG stat1≥10·HEART stat1≥7·ANGEL stat1≥5·Penguin stat1≥3·Dog/Cat stat1≥4·MortarBoard 지식(stat30)≥200·ANGELRING 마술(stat37-39)각≥100.
   - **tier3 스킬그룹합**(+0x1cc 테이블 9엔트리 {resIdx,groupIdx,threshold}, `FUN_005a5280` 그룹합≥threshold): GLASSES/SUNGLASSES/MASK/SUJANG(+진화≥3)/BAG/TURTLESHELL/WING/DUCK.
   - **획득 = 순수 게임플레이 스탯 성장**(레벨/지식/스킬누적). 별도 "지급" 순간 없음. Azrok.dat 밖 맞음(파생값).
   - **★서버 함의: 소유목록 저장/추적 불필요** — 스탯(0x0007로 이미 영속)의 순수 함수. content/107 착용 4바이트 계약 그대로 충분, 소유필드 0개. (원하면 서버가 동일 임계 재계산해 미해금 equip fail-closed 거부 가능.)
   - 미확정(x32dbg): +0x1cc 9엔트리 정확 {groupIdx,threshold}, stat1 정체(레벨/성장).
3. mid-session 착용변경 재스폰 relay 여부.

## doc 정정 3건

1. content/80: C→S 0x18 = 펫재주 **+ 액세서리 착용**(공유 opcode).
2. 0x0066 레코드(구 doc21): name(13B@+7)·accessory(4B@+0x14) 추가.
3. 0x0007 `+0x1D4`(구 doc49): "domain selector vector" → 착용 액세서리 4슬롯.

핵심함수: 로더 FUN_00521ff0/인덱서 FUN_00521e90/언마운트 FUN_00522ae0/getter FUN_005ab2b0/importer DomainSelector_ImportByteVector4@0x005AB080/커밋 FUN_005b2970/송신 FUN_005ab900/self적용 FUN_00524280/remote적용 RemoteActor_InitFrom0066Record@0x005243E0.

Related: content/103(놓친컨텐츠 — 액세서리 여기서 계약화), content/84(서버계약 — 6번째 층 추가), content/80(0x18 정정), multiplayer/55(0x0066 로스터), INDEX.
