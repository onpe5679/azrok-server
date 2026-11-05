# 연결·로그인 핸드셰이크 + 모드별 S→C 디스패치 (2026-07-18)

> **PARTIALLY SUPERSEDED by 86.** 이 빌드의 persistent live 연결에서 즉시 S→C0001[00]은 socket/UI를 종료시켰고, 정상 경로는 첫 heartbeat에 0016+0004[00]+0000입니다. S→C0000 +1은 lobby_mode가 아니라 occupied count이며 slot SoA는 86 참조.

정적 분석(Ghidra, `Azrok_original.exe`) 전 항목 디컴파일. 서버 재구현의 **연결 부트스트랩** 계약.
**모드별 3갈래 디스패처(DispatchInbound_ByClientMode)는 Claude 본인 디컴파일 재검증**(바이트 일치).
VERIFIED=디컴파일 본문, INFERRED=추론. 0x0007 콘텐츠블롭 내부는 Codex 영역(경계로 제외).

## ★ 0. S→C 디스패치는 클라 mode별 3갈래 (VERIFIED, 본인 재검증) — 방향 트랩의 뿌리

`DispatchInbound_ByClientMode`@0x00594310가 **`mode = *(CLogicManager+0x163E4)`** 로 라우팅:
```
mode 0 (로그인/핸드셰이크): DispatchState0Specific_S2C@0x0059dd20  + (게이트 +0x163d8시) DispatchState0Common_S2C@0x0050cbc0  — 둘 다
mode 1 (게임/Plaza)      : FUN_005ab6e0 + DispatchState1_S2C@0x00613740 (protocol/75)
mode 2 (미니게임/OX)      : FUN_005abd90 + vtable[+0x10] 디스패치
```
- 게이트 = `*(CLogicManager+0x163d8)` (INDEX 디스패치 owner: 게이트 +0x163D8 / mode +0x163E4).
- **★ 같은 opcode가 mode에 따라 다른 핸들러로 감** (핸드셰이크 핸들러 = 0x0059xxxx/0x0050xxxx, 게임 = 0x0061xxxx).
  → **프로젝트 전역 "방향/opcode 트랩"의 구조적 근원.** 예: S→C 0x00이 mode0에선 로비부트스트랩, C→S 0x00은 로그인.
- 특례(mode 무관 선처리): opcode 100→mode1 승격, opcode 5→PostLoadState, opcode 1000→FUN_00594240.

## A. 연결 + 로그인 (VERIFIED)

`FUN_00508b30`@0x00508b30 `__thiscall(this, "host:port", user, pass)`:
- 소켓 연결 → `strtok(hostport,":")` host→this+0x31822 / port(atol)→this+0x31842 / user→this+0x3179e / pass→this+0x317be.
- 연결확인(FUN_005941c0) 성공 → **C→S 0x00 로그인** `FUN_00593d90`@0x00593d90 = send(0x00, buf, **0x6a=106B**):
  **[+0]type(1B) [+1]user(13B) [+14]pass(92B).** 연결실패 = UI 패널 0xe.

## B. 서버 부트스트랩 응답 테이블 (mode 0, Specific+Common 병렬) (VERIFIED)

| opcode | Specific @0x0059xx | Common @0x0050xx | 의미 |
|---|---|---|---|
| **0x01** | Primary(FUN_00592a80) | ResetLatchOrRaiseError | **인증결과**: payload[0] 0=성공 / 1=에러패널0x12 / 2=에러패널0x11 |
| **0x00** | LoadLobbySparseCache | SelectLobbyEntryScene | **부트스트랩 0x183 블롭**(§C-1) + 씬선택 |
| **0x02** | TransitionPrimary | (this+0x31946=0) | 전환(C→S ack 방출) |
| **0x03** | — | StoreSpacePath | this+0x31c63=payload[0], payload+1=공간경로 문자열 |
| **0x04** | CalibrationSample | (payload[0]==0xff→Hansol방 해제 this+0x31c71) | **시간동기 캘리브레이션** |
| **0x05** | PostLoadState(스탯캐시→레지스트리 리플레이) | CommonWrapper(방0x6d/0x69) | 로드후 상태 |
| **0x06** | ResetLocalClockAndSeed | FUN_0050d250 | 시드+진화0리셋+PackedDate클록+로컬시드스탯 → **C→S 0x0007 방출** |
| **0x0A** | StatRegistry | — | 75 u16 아이템 레지스트리(INDEX 57b) |
| **0x0B** | XPCurve | — | XP 커브 |
| **0x07** | LoadSetupBlob ⚠콘텐츠경계 | EmitPostSetupStateRequest | 셋업블롭(Codex) + **진입방 결정** |
| **0x0D** | — | payload[0]==0→Plaza전환 / else UI 0x1c | 방 전환 |

## C. 세부 레이아웃 (VERIFIED)

**C-1. 로그인 응답 0x00 = 0x183(387B) 블롭** (`Lobby_CopyBootstrapBlob_0183`@0x0050d1c0 → this+0xbf4):
- +0x00(1B) result_code(0=성공) · +0x01(1B) **lobby_mode → 씬선택(0→로비 방0x6c / ≠0→펫 방0x6b)**
- +0x56(1B) sparse_count · +0x57(u16[]) sparse_keys · +0xBB(u32[]) sparse_values(0값 필터, LobbySparseRecordTable)

**C-2. 핸드셰이크 C→S 방출 지점**:
- **C→S 0x00 로그인** = FUN_00593d90 (106B, §A).
- **C→S 0x01/0x02 빈 ack** = `FUN_0059d760(op, 0, 0)` = send(0x01/0x02, NULL, **0B**). ★ content/66 §5 "FUN_0059d760 계열 0x03-0x17"의 실체 = **빈페이로드 전환 ack**.
- **C→S 0x16 시간동기 핑** = HandleS2C_0004가 RTT 5회, 매 샘플 `FUN_0059d760(0x16, &1, 1)`(1B), 완료 payload=0xff. (같은 0x16이 평시 9999ms 하트비트 FUN_005946b0로도 쓰임.)
- **C→S 0x0007 상태저장** = `FUN_005a4770`@0x005a4770 = 196B(0xC4) → netObj->vtable[+0x10]. ⚠콘텐츠경계(Codex, content/76/79).
- **C→S 0xC8(200) 씬진입 확정** = FUN_005ff1e0 → send(0xC8, NULL, **0B**), 이후 mode→2.

**C-3. 핸드셰이크 opcode 핸들러 주소 + payload 세부** (VERIFIED):
- 0x01 `ResetLatchOrRaiseError`@0x0050d360: [+0] 0성공/1→패널0x12/2→패널0x11
- 0x02 `HandleS2C_0002_TransitionPrimary`@0x0059d150: → C→S 0x0007 저장 + C→S 0x02 빈ack
- 0x03 `StoreSpacePath`@0x0050d200: [+0]코드(1B)→this+0x31c63, [+1~]공간경로 문자열
- 0x04 `CalibrationSample`@0x0059de50: [+0]==1 유효샘플·[+1](u32)서버타임스탬프(RTT), [+0]==0xff 완료
- 0x05 `PostLoadState`@0x0059ebd0: [+0]result·[+1]subcode(0x12/0x13)·[+2](u32)값 → 스탯캐시 리플레이
- 0x06 `ResetLocalClockAndSeed`@0x0059e1f0: [+0]==0시 [+1]시드 → 클록/진화0리셋/초기스탯 → C→S 0x0007
- 0x0A `StatRegistry`@0x0059eca0(75 u16) · 0x0B `XPCurve`@0x0059eee0 · 0x00 `LoadLobbySparseCache`@0x0059e070+`SelectLobbyEntryScene`@0x0050d0e0
- FUN_0059d760@0x0059d760 = FUN_00593d10 send 래퍼(여러 이름 FUN_005ab6a0/005abd50/0059d760 전부 동일 소켓 send).

## D. 경계 + mode 전환

- **0x0007 LoadSetupBlob 본문 = Codex 영역**(미접촉). 핸드셰이크는 블롭 수신 + EmitPostSetupStateRequest의
  **진입방 결정**(this+0x31c72≠0→방0x6e / +0x31c73≠0→방0x6f / else 기본)까지.
- **mode 0→1 전환**: *(CLogicManager+0x163E4) 0→1은 0x02 TransitionPrimary + 방 로드가 트리거. 방 진입 자체(C→S 0x0065 등)는 exit/gym 영역(Codex).

## 캐릭터 선택 4슬롯 (INFERRED)

프로토콜에 **명시적 캐릭터목록 opcode 없음.** 로비 스파스캐시(0x00 블롭)가 로비 상태, 씬선택은 lobby_mode 이분법.
4슬롯 = 로비 씬(0x6c) 로컬 UI가 스파스캐시를 표시하는 것으로 추정(Azrok=단일펫). 별도 목록 프로토콜 아님.

## 서버 재구현 계약 (연결 부트스트랩)

1. TCP accept → C→S 0x00 로그인(106B) 수신 → 인증 → **S→C 0x01**(result) → **S→C 0x00**(0x183 블롭: result+lobby_mode+sparse).
2. 캘리브레이션 원하면 S→C 0x04 ↔ C→S 0x16 5회. S→C 0x03(공간경로)/0x06(시드) → C→S 0x0007.
3. S→C 0x0A(아이템 레지스트리)/0x0B(XP커브)/0x07(셋업블롭=콘텐츠) → 진입방 결정 → mode 0→1 → 게임(protocol/75).
4. **mode 필드(CLogicManager+0x163E4)를 서버가 직접 안 봄** — 클라가 자체 관리. 서버는 opcode 순서로 부트스트랩 진행.

## x32dbg 확인 필요

1. mode 전환 정확 시점: BP DispatchInbound_ByClientMode(0x00594310), *(this+0x163e4) 0→1 변화가 어느 S→C 직후인지.
2. 0x183 블롭 실제 바이트(this+0xbf4 덤프) + 캐릭터 4슬롯 데이터 여부.
3. 캘리브레이션 0x04↔0x16 5회 RTT 실측.
4. 서버 push 순서(서버 소실 → 정적 불명, 클라는 순서무관 처리).

Related: [[protocol/75_s2c_state1_dispatch_table_and_ox_protocol]](mode 1 게임 디스패치), [[content/66_shop_item_economy_and_money_offset]](§5 FUN_0059d760 실체 해결),
INDEX(디스패치 owner mode/게이트). 방향 트랩(INDEX)의 구조적 근원 = §0.
