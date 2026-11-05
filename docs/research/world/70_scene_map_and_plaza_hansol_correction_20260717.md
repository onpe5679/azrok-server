# 전체 씬 지도 + Plaza=hansol 정정 + OX 구조 (2026-07-18)

정적 분석(Ghidra, `Azrok_original.exe`). `GameManager_DispatchRoomCode` @0x0050a0f0 기준 전체 씬 맵.
VERIFIED = 디컴파일 본문, INFERRED = 추론. x32dbg 미사용(Codex 영역).

## ⚠️ 정정 A: 멀티플레이 Plaza = hansol.wmb (ground.wmb 아님) — VERIFIED

일부 문서/라벨이 `ground.wmb`(code 0xa/10)를 Plaza로 표기했으나 **틀림**. 실제 Plaza = **hansol.wmb**:
- INDEX "Plaza scene=110/phase=4": **110 = 0x6E = hansol.wmb 의 init-code, phase 4 = hansol**.
- `Hansol_SceneStageHandler` @0x00614370 (init 0x6e) 의 stage0 가 `SendC2S_0064_LocalBootstrapStatus()`
  호출 = INDEX 자연외출 경로의 "C→S 0064". Plaza 자산 로드: `Data\Plaza\Mount\`(MiniCar/DUCK/LIGHTING/
  RAINBOW/RAIN/SUN 탈것 6종), `Data\Plaza\Model\`(staff/P_TO/P_PZ/P_AO/P_AK NPC, moon, Sandal),
  PLAZA_CHAIR, bee.npc, GM_ICON. 설치경로 문자열 `Program Files\Hansol\Azrok_Plaza`.
- 반면 **ground.wmb**(`FUN_005326c0`, init 0x6d, phase 2)는 3단계 최소 로더, **0x64 부트스트랩 없음**
  → 멀티플레이 Plaza 아님. 역할 미확정(사설 마당/미사용 추정, INFERRED).
- 오늘 확정(0x000D → room 0x6E → hansol.wmb → Plaza)과 **일치**. ground 혼동만 정정.

## 1. 전체 씬 목록 (VERIFIED)

room code → level_load(WMB) → init-code → phase(+0x31792):

| code | WMB | init | phase | 종류 |
|---|---|---|---|---|
| 0 | room.wmb | 0x64 | 2 | 로컬 PatHouse |
| 1 | playroom.wmb | 0x65 | 2 | 로컬 놀이 |
| 2 | gym.wmb | 0x66 | 2 | 로컬 체육 (Codex 동적조사 중) |
| 3 | magic.wmb | 0x67 | 2 | 로컬 마술 |
| 4 | cook.wmb | 0x68 | 2 | 로컬 주방 |
| 5 | shop.wmb | 0x69 | 2 | 로컬 상점 |
| 6 | library_1.wmb | 0x6a | 2 | 로컬 도서관 |
| **8** | **lobby.wmb** | 0x6c | **1** | 서버/캐릭터 선택 로비 |
| **9** | **pet.wmb** | 0x6b | **0** | 펫 뷰/부트 화면 |
| 10 | ground.wmb | 0x6d | 2 | 미확정 (Plaza 아님) |
| **0xb** | **hansol.wmb** | 0x6e | **4** | **멀티플레이 Plaza** (게이트 +0x31c71≠0) |
| 0xc | OXQuiz.wmb | 0x6f | 5 | OX 퀴즈존 |

## 2. 미개척 씬 정체 (VERIFIED)

- **lobby.wmb**(`FUN_00528b60`, phase 1): 5단계 로컬 UI 로더, 네트워크 없음. 서버/캐릭터 선택 로비.
- **pet.wmb**(`FUN_00528780`, phase 0): 5단계 로컬 로더, 네트워크 없음. 펫 뷰/부트 화면.
- **로그인 후 진입 씬 = 서버 지정**: `HandleS2C_0000_SelectLobbyEntryScene` @0x0050d0e0
  (S→C 0x00 — C→S 0x00=login 과 방향 비대칭, content/68 정정 참조): payload[1]==0 → 로비(0x6c),
  !=0 → 펫(0x6b). **로비 vs 펫 진입을 서버가 결정.**

## 3. 씬 진입 프로토콜 C→S 0xC8(200) (VERIFIED payload, 트리거 INFERRED)

`FUN_005ff1e0` → `FUN_005abd50(200, NULL, 0)` = **C→S 0xC8, 빈 페이로드**. self 액터 구성(이름 13B,
외형 4B via FUN_005ab2b0(0..3)) + SetPendingSceneCode(1)로 state-1 진입. → 0xC8 = "self 액터 월드
입장" 무페이로드 announce(서버가 커넥션으로 상관). 씬-상태 함수포인터 테이블(0x6ae908 slot2)로 호출되어
정확한 트리거 씬 집합은 정적 미특정. Plaza 부트스트랩 자체는 별개(C→S 0x64, hansol stage0).

## 4. OX 게임존 (VERIFIED 구조, opcode INFERRED)

> **부분 SUPERSEDED by protocol/75.** ①"셀렉터 0x6F/70/71 후보"=REFUTED(셋 다 범용 UI 프리미티브,
> OX 무관). ②"0x6E가 OX 강제"=약화/반증(0x6E는 ready게이트, FUN_00627560/630은 씬강제 아님). ③"전용 Q&A
> opcode 없음"=CONFIRMED. 전체 S→C 디스패치 18핸들러 표·OX 페이즈 매핑은 protocol/75 참조.

- OX = C++ 클래스 **`CGameOXQuiz : CMultiGame + CGameOXQuizUI`** (RTTI 0x6e45c8). `Data\MultiGame\OXGame\`
  자산 = 멀티플레이 게임. 진입 OXQuiz.wmb(code 0xc, init 0x6f, phase 5). S→C 0x6E가 OX 강제.
- **문제/정답 전용 opcode 없음 (핵심)**: `DispatchState1_S2C` @0x00613740 는 opcode 3/C/0x64~0x71/0x3E8
  만 라우팅 — OX 전용 없음. **OX 진행 = 일반 액터-동기 프로토콜 재사용**:
  - 정답 = 플레이어 위치(O측/X측 이동) → C→S 위치동기 0x16 (INFERRED)
  - 오답 제거 = S→C 0x69 action-state(번개/탈락 애니), lightning.MDL
  - 문제/카운트/결과 = S→C 0x6A(actor text) / 0x3E8(공지) / 셀렉터 0x6F/70/71 후보
  - UI: OXbasePan, TextPan(문제), QNumber, Time/Count, OXok, OXResultPan, abstention(기권)
  - 진행 단계(사운드 0x61f-0x625): Logo→Count→start→Success/Fail→Win→Result
  → 서버 주도 멀티게임이나 dedicated Q&A opcode 없이 액터-동기+위치로 구현. 정확한 문제 opcode 미확정.

## 5. Plaza 하위·건물 진입 = 로컬 vs 서버 (VERIFIED)

- **로컬룸(집, code 0-6) 진입 = 순수 로컬 level_load** (DispatchRoomCode 직접 WMB 로드, 서버 요청 없음).
  펫 홈 허브의 건물/메뉴 버튼이 룸코드를 ButtonQueue push.
- **멀티 씬(hansol Plaza / OX) 진입 = 서버 게이트**: C→S 0x64 부트스트랩 + S→C 0x6E ready-commit 필요.
  OX는 Plaza 하위구역이 아니라 별도 WMB로의 서버 확정 전환.
- 로그인 최초 진입(로비/펫) = 서버 지정(S→C 0x00).
- **요약: 사설 방(집)은 로컬 전환, 공용/멀티 지역은 서버 확정 전환.**

## 확정 못한 것

- ground.wmb 정확한 용도(0x64 없음 → Plaza 아님은 확정, 역할 미확정).
- OX 문제/정답 정확한 wire opcode·페이로드(dedicated 없음; 셀렉터 0x6F/70/71 후보).
- 0xC8 호출하는 정확한 씬 집합(함수포인터 테이블 경유).
- room code 0xa(ground)/0xb(hansol) push 소스(네비게이션).

Related: world/60·62·63·64(Plaza/외출), content/66(C→S opcode 맵), content/68(0x00 정정), INDEX.
**INDEX/문서의 "Plaza(ground.wmb)" 라벨은 hansol.wmb 로 정정 필요.**
