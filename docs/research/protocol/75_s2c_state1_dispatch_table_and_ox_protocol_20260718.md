# S→C state-1 디스패치 전체 표 + OX 프로토콜 확정 (2026-07-18)

> **PARTIALLY SUPERSEDED by 86, 87 and 92.** `FUN_006133B0`은 일반 opcode latch, C→S0069는 Plaza 의자입니다. 답안 위치 송신은 C→S0066/0067을 재사용하지만, 92가 mode-2 전용 S→C `0xC8..0xD4`와 CE 정답 side/CB 패자목록을 확정했습니다. "OX 전용 opcode 0개"는 state-1 표에만 한정됩니다.

정적 분석(Ghidra, `Azrok_original.exe`). `DispatchState1_S2C` @0x00613740 전체 라우팅을 명명 핸들러로
확정하고, OX 퀴즈존 프로토콜 가설을 검증. **디스패치 표는 Claude 본인 디컴파일로 재검증**(에이전트 보고와
바이트 일치), OX 세부는 병렬 에이전트 정적분석. VERIFIED=디컴파일 본문, INFERRED=추론.

## 1. DispatchState1_S2C @0x00613740 — S→C state-1 전체 라우팅 (VERIFIED, 본문 재검증)

`this+0x12A8` 트래픽 카운터 누적 후, opcode<0x3E9 에서 아래 **18개만** 라우팅(본체 0x0061xxxx, 0x004Dxxxx는 thunk):

| opcode | 핸들러 @주소 | 역할 |
|---|---|---|
| 0x0003 | HandleS2C_0003_ForwardStateValue @0x00615610 | payload+1 dword를 전역 state 소비자 2곳에 forward |
| 0x000C | HandleS2C_000C_ApplyActorSlotValue @0x006165b0 | actor 슬롯(index/value), clear시 0xFF |
| 0x0064 | HandleS2C_0064_ApplyAuthoritativeSelf @0x00615650 | 권위적 self 배치(좌표/room_domain/scene 0x2E·0x2F) |
| 0x0065 | HandleS2C_0065_FlushRemoteActors @0x00615b20 | 리모트 액터 flush(전체 클리어) |
| 0x0066 | HandleS2C_0066_BatchRemoteActorSpawn @0x00615b50 | 리모트 액터 배치 스폰 |
| 0x0067 | HandleS2C_0067_RemoveRemoteActor @0x00615d00 | 리모트 액터 제거(이탈) |
| 0x0068 | HandleS2C_0068_BatchActorState @0x00615d50 | 액터 상태 배치(이동/애니 동기) |
| 0x0069 | HandleS2C_0069_ApplyActorActionState @0x00615e70 | actor action-state(self/remote, 탈락/연출 후보) |
| 0x006A | HandleS2C_006A_ApplyActorTextPayload @0x00615ff0 | 텍스트/시스템텍스트(말풍선·질문 후보) |
| 0x006B | HandleS2C_006B_UpdateSelfStateField33A @0x00615340 | self 상태필드 +0x33A |
| 0x006C | HandleS2C_006C_UpdateActorStateFields336_33A @0x00615410 | actor 상태필드 +0x336/+0x33A |
| 0x006D | HandleS2C_006D_AdvanceActorField332Stage @0x006154e0 | actor +0x332 stage 전진 |
| 0x006E | HandleS2C_006E_CommitReadyMode @0x006169d0 | ready/성패 게이트 (+ FUN_00627560/00627630 호출) |
| 0x006F | HandleS2C_006F_SetSelectorPair @0x00616b20 | (index,value) 2슬롯 셀렉터 저장 |
| 0x0070 | HandleS2C_0070_HandleLatchedDualForm @0x00616860 | latch(FUN_006169a0)로 short/full form 분기 |
| 0x0071 | HandleS2C_0071_SynthesizeLocalFE @0x00616510 | payload[0]==0시 적색 로컬 텍스트/이펙트 합성 |
| 0x03E8 | HandleS2C_03E8_ShowState1SystemNotice @0x006167e0 | 고정 시스템공지(msg id 0x11) |

- **0x64=자기(self) 배치, 0x65~0x68=리모트 액터 라이프사이클(flush/spawn/remove/state), 0x69=action-state,
  0x6A=텍스트, 0x6B~0x6D=상태필드, 0x6E=ready게이트, 0x6F~0x71=셀렉터/텍스트 프리미티브, 0x3E8=공지.**
  (0x65~0x68은 multiplayer 51/52/55/67의 로스터·릴레이 동적검증과 일치 — 이 표는 그 정적 대응.)

## 2. OX 퀴즈존 프로토콜 (VERIFIED 구조, 용도라벨 INFERRED)

**★ state-1 표 안의 OX 전용 opcode는 0개 (CONFIRMED).** 위 18개는 범용 world/actor/text 핸들러입니다.
다만 OX 진입 뒤 mode 2에는 별도 vtable 디스패처와 S→C `0xC8..0xD4`가 존재합니다(92).

- **진입 `FUN_00613a10`** (VERIFIED): room code 0xc(OX방) 로드 → `FUN_006136c0(0xf7b,0xc3)` 로 월드좌표를
  **6열 그리드 셀**로 변환(`(y+9000)/3000 + ((x+9000)/3000)*6`) → **OX = 타일/좌표 기반 공간게임 확증** →
  `FUN_00594100(2)` = dispatch **mode=2** (this+0x163E4) → phase 인자 3. 보조 flag: `GameManager_SetOXQuizFlag`
  @0x005284c0 = this+0x31c73 바이트.
- **OX 와이어 페이즈 매핑** (메커니즘 VERIFIED / 용도 INFERRED):
  - 진입·배치 = **0x0064** (entry_kind 0x0A→scene0x2E, 0x0B→scene0x2F = OX '플레이중' 씬)
  - 질문/공지 = **0x006A** (actor_id==0 && kind==1 = 시스템텍스트, **콜론 구분자**로 2분할; kind→RGB
    0=흰/1=적/2=(0x78,0xFA,0xC8)/3=(0xFA,0xEF,0x77)) — 질문용도 INFERRED
  - 카운트/전역 = **0x0003**(state value 2곳) + **0x03E8**(시스템공지) — 매핑 INFERRED
  - 탈락/판정 = **0x0069** (mode 0x2E/0x2F면 좌표 직접동기화, 아니면 SetPendingSceneCode(1)=씬전환/사망연출)
    — '탈락' 의미 INFERRED(강함)
  - 개별상태(생존/점수?) = **0x000C** (슬롯 index/value, 0xFF clear) — 용도 INFERRED
  - ready/성패 = **0x006E** (ready_gate=payload[1]; ==0 성공[버튼0xC6 push,+0x129B ready=1], !=0 실패 FUN_005bf2c0(0x18))
- **C→S 프레이밍**: 다음 송신 opcode = `state+0x3084a` (FUN_006133b0), 플래그 +0x3179a. C→S/S→C 번호공간 공유
  — `SendC2S_0064_LocalBootstrapStatus` @0x006130b0 는 입장상태 빌드 후 outbound 0x6E(ready) arm. 즉 0x64=입장,0x6E=ready.
- **답안 = O/X 타일 이동**: 전용 popup 송신은 없으며 일반 world click의 C→S0066 22B와 arrival C→S0067
  15B를 재사용합니다(VERIFIED). 0066은 cell/current/destination/duration/pathFlag이고 cell은
  `((y+9000)/3000)+((x+9000)/3000)*6`. 원본 최종 판정 timestamp와 O/X side→cell mapping은 NOT VERIFIED.

## 3. world/70 정정 (이 문서가 상위)

- **0x6F/0x70/0x71 = OX 전용 셀렉터** 가설 → **REFUTED.** 셋 다 범용 UI 셀렉터/텍스트 프리미티브(§1),
  OX 진행과 무관. world/70 §4의 "셀렉터 0x6F/70/71 후보"는 폐기.
- **"S→C 0x6E가 OX 강제진입"** → **약화(사실상 반증).** 디스패처의 0x6E case가 부르는 `FUN_00627560`/`FUN_00627630`
  은 씬강제가 아니라 정적초기화 가드/배열원소 write(인자 (0,0)). 0x6E는 ready/성패 게이트일 뿐. world/70 §4 정정.
- **"OX 전용 Q&A opcode 없음, 액터-동기 재사용"** → **CONFIRMED** (world/70 가설 유지·강화).

## 4. x32dbg 실측 필요 (Codex 동적 영역 — 정적 한계)

1. OX phase A/B에서 원본 판정이 0066 destination과 0067 arrival 중 어느 값을 마감 시 사용하며 어느 cell이 O/X인지 확정.
2. 질문 텍스트 실제 opcode: OX 진행중 0x006A actor0/kind1 페이로드에 질문+콜론포맷 오는지 캡처.
3. 탈락 트리거: 0x0069 수신시 SetPendingSceneCode(1) 사망연출=실제 탈락인지, 서버 O/X 판정 그리드셀 기준.
4. 카운트다운: 0x0003 forward value vs 0x03E8 notice 중 라운드타이머 구동원.

Related: [[world/70_scene_map_and_plaza_hansol_correction]] (정정), multiplayer/51·52·55·67(0x65-0x68 동적),
protocol/48·49(로컬룸·0x0007 스키마), INDEX.
