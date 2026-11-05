# 채팅·커뮤니티·펫재주 wire 바이트 레이아웃 (2026-07-18)

정적 분석(Ghidra, `Azrok_original.exe`) 전 항목 디컴파일. content/68의 구조를 **정확한 바이트 오프셋**으로
확정. **C→S 0x68 채팅 빌더(FUN_00594740)는 Claude 본인 디컴파일 재검증**(바이트 일치). VERIFIED=디컴파일 본문,
INFERRED=추론.

## 0. 송신 함수 2개 (수렴점 하나)

- `FUN_00593d10(op, buf, len)` @0x00593d10 = 실제 송신(로그인/채팅/하트비트 직접).
- `FUN_005ab6a0(op, buf, len)` @0x005ab6a0 = 얇은 래퍼(펫/커뮤니티/액터) → 결국 FUN_00593d10 수렴.
  (0x18/0x6c가 FUN_00593d10 직접 호출자에 안 잡혔던 이유 = 이 래퍼 경유.)

## 1. C→S 0x68 채팅 (VERIFIED, 본인 재검증)

빌더 `FUN_00594740(type, name, msg, flag)` @0x00594740. 입력 UI `GameManager_ProcessChatInput` @0x0050dd10
(Enter=VK 0x0D, ESC=0x1B). 전역버퍼 base `DAT_006ea480`:

| off | size | 필드 |
|---|---|---|
| +0x00 | 1B | type: **0=공개, 1=귓속말** |
| +0x01 | 1B | flag: 귓속말→0 / 공개→`FUN_006194f0()` 단어스캔 결과 (의미 INFERRED, 소스 VERIFIED) |
| +0x02 | 13B | 대상이름 `strncpy 0xd`. 공개→빈문자 / 귓속말→타깃명 |
| +0x0F | 1B | 0x00 (이름 널종단) |
| +0x10 | 1B | msglen = `strlen(msg)+1` |
| +0x11 | 가변 | 메시지 CP949 널종단 |

- **총길이 = strlen(msg)+0x12, 상한 <200(0xC8)** → 메시지 ~182B. 초과시 미전송.
- 귓속말 파싱: `/이름 메시지`, **구분자 = 스페이스 0x20**. 자기귓속말 차단, 욕설필터("바른 고운말을 사용하세요.").

## 2. S→C 0x6A ApplyActorTextPayload (VERIFIED)

`HandleS2C_006A_ApplyActorTextPayload` @0x00615ff0 (protocol/75 디스패치 표):

| off | size | 필드 |
|---|---|---|
| +0x00 | 1B | kind(색): 0=흰FFFFFF, 1=적FF0000, 2=하늘(78,FA,C8), 3=금(FA,EF,77) |
| +0x01 | 1B | mode |
| +0x02 | 4B | actor_id (self=mgr+0x2f8 / RemoteActor_FindByActorId) |
| +0x06 | ~15B | primaryText(발신이름; 액터 해석되면 액터명으로 덮어씀) |
| +0x15 | 가변 | secondaryText(메시지, CP949 널종단) |

- 특수: **actor_id==0 && kind==1 → 시스템텍스트**, `":"`(0x3a)로 "이름:메시지" 분할(콜론없으면 fallback색 c9,fa,6b).
- 이중표시: 말풍선(ScreenAnchor) + 채팅로그(TextLog_EmitColoredMessageLines).

## 3. 커뮤니티 0x6C (VERIFIED, ★비대칭)

- **C→S** `FUN_005ab950(actor_id)` @0x005ab950 → send(0x6c, **4B**) = self actor_id(dword) 하나. 트리거
  `FUN_005ce8e0` @0x005ce8e0가 UI플래그 this+0x2bd 토글, **scene==0x6E(Plaza)일 때만 id, 아니면 0** 전송.
- **S→C** `HandleS2C_006C_...336_33A` @0x00615410. payload(≥6B): +0x00(1B)state→actor+0x336, +0x01(1B)toggle→+0x33A
  (값<2면 둘set+FUN_00527760(0x30,0), ≥2면 필드32E/332·336/33A 리셋), +0x02(4B)actor_id(self무시).
- **★ C→S=4B(id만) / S→C=6B(state+toggle+id) 비대칭** — 서버가 state/toggle 바이트 채워 브로드캐스트.
  친구/파티 로스터 아님(리스트 없음, actor 2바이트 상태만). INFERRED: 이모트/상태 토글.

## 4. 액세서리 commit 0x18 (SUPERSEDED by 109)

> **SUPERSEDED by 109.** 아래의 펫재주/shared/0x69 해석은 `FUN_005AB900`의 실질 caller 전수와 액세서리 UI asset·dispatcher 재검증으로 폐기되었습니다. C→S `0x0018`은 액세서리 전용이며 `[action=0 set/1 clear, slot, value]`; 실시간 응답은 S→C `0x000C` exact7입니다.

- **C→S** `FUN_005ab900(slot, kind, localId)` @0x005ab900 → send(0x18, **3B**):
  +0x00(1B) slot 0/1 · +0x01(1B) kind 0-3 · +0x02(1B) localId = `fullActionId − 10000×(kind+1)` (kind0=1만번대…3=4만번대)
- 빌더 `FUN_005b2970(this, slot)` @0x005b2970 (슬롯0=this+0x764/+0x768, 슬롯1=this+0x7a8/+0x7ac).
- **스탯 잠금해제 게이트** `FUN_005b2cb0(this, actionId)` @0x005b2cb0 = 1(해제)/0(잠김). 스탯리더 `FUN_005a49b0`(base this+0x5f4, stride 0xc). 임계 예:
  10004→마법스탯 0x25/26/27 각≥100 · 10009→stat0x1E≥200 · 20004→데이터테이블+**진화단계(vtable+4)≥3** · 40001→stat1(레벨)≥10 · 기본ID 10000-10003·10007·10008·30003·40005-40007 → 무조건 해제. 데이터테이블 @this+0x1cc(9엔트리 stride0xc: actionId/statId/threshold).
- 재주 정의데이터 = 별개 CJSCommand 시스템, CSV 로더 `FUN_00595780`(0x142B 레코드), **네트워크 아님**.
- **정정**: S→C `0x000C` `HandleS2C_000C_ApplyActorSlotValue@006165B0`가 exact7 `[actor_id:u32,clear:u8,slot:u8,value:u8]`로 self/remote appearance를 갱신합니다. `0x0069`는 이 계약과 무관합니다(109).

## ⚠ content/68 정정 (직접 검증)

- **0x1a/0x1b는 네트워크 opcode 아님** — `FUN_005bf2c0` @0x005bf2c0 = UI 패널 스위처 코드(this+0xf2 패널인덱스).
  slot 비면 액션메뉴패널 0x1a, 게이트 실패면 패널 0x1b. FUN_005b2970의 실제 네트워크 송신은 **0x18 하나뿐**.
  (content/68 §"slot 비면 opcode 0x1a 전송"은 오기 → 정정.) `FUN_005afdd0`은 getter(송신 아님).

## 방향 트랩 (재확인)

- **C→S 0x68=채팅** / **S→C 0x68=BatchActorState**(이동 릴레이, 0x18B/record) — 완전 다름.
- **C→S 0x00=로그인**(채팅 아님): FUN_00593d90→send(0x00, 106B) = [+0]type(1B)+[+1]13B user+[+14]92B pass.

## 서버 재구현 계약

- 채팅: 서버는 C→S 0x68 파싱(type/name/msg) → 대상(공개=방 전체 / 귓속말=name 매칭) 에게 S→C 0x6A(kind+actor_id+이름+메시지) 브로드캐스트.
- 커뮤니티: C→S 0x6C(4B id) 수신 → state/toggle 결정해 S→C 0x6C(6B) 브로드캐스트.
- 액세서리: C→S 0x18(3B) 검증·영속 → S→C 0x000C self ACK와 같은 방 peer appearance delta(109).

## x32dbg 확인 필요 (Codex 동적영역)

1. BP @0x00593d10 ([ESP+4]=op/[ESP+8]=buf/[ESP+0xC]=len). 공개채팅·귓속말·커뮤니티·재주 각 실행 라이브 캡처.
2. 0x68 공개 +0x01 flag(FUN_006194f0 결과) 실제 값·의미.
3. S→C 0x6C state/toggle 이모트별 바이트값.
4. 원본 UI 장착/해제 각 1회의 0x18 action/value와 S→C 0x000C recipient 실측(109의 남은 live 관문).

Related: [[content/68_chat_community_pet_social_protocol]](구조 원본, 0x1a/1b 정정), [[protocol/75_s2c_state1_dispatch_table_and_ox_protocol]](0x6A/6C/69 핸들러),
[[content/76_minigame_reward_engine_and_bong_energy_gate]](스탯 게이트), INDEX.
