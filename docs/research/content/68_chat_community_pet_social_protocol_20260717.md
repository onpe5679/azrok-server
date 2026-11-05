# 채팅 · 커뮤니티 · 펫 소셜 프로토콜 (2026-07-17)

정적 분석(Ghidra, `Azrok_original.exe`)으로 채팅/소셜 축 복원. VERIFIED = 디컴파일 본문,
INFERRED = 추론(서버 소실이라 S→C 응답은 핸들러 형태에서 역산).

## ⚠️ 정정: C→S 0x00 = 채팅 아님, LOGIN/인증 (VERIFIED)

이전에 "0x00/0x68 = 채팅"으로 오인됐으나, **0x00은 인증 채널**이다.
- 송신 `FUN_00593d90` → `FUN_00593d10(0x00, buf, 0x6a)`. 고정 106B: [+0]type(1B) + [+1]13B + [+14]92B.
- 호출 체인 `FUN_00508b30`(로그인)이 결정적: `host:port` strtok → 소켓 오픈(DAT_006b1748),
  param3→gm+0x3179e, param4→gm+0x317be → `FUN_00594130` → `FUN_00593d90(user, pass, 0)`.
- 즉 **13B = username, 92B = password, type 바이트 = 0(로그인)**. FUN_005942c0/FUN_0050b020 경로는
  같은 필드로 type=1(재접속/재인증 추정). 미연결 시 "서버와 접속이 끊겼습니다." 표시.
- **실제 사용자 채팅은 0x68 하나뿐.** (INDEX identity 문서 56 의 0x0000 login NAME/AUTH 와 일치.)

## 1. 채팅 송신 = C→S 0x68 (VERIFIED)

빌더 `FUN_00594740`, 입력 UI `GameManager_ProcessChatInput` @0x0050dd10 (Enter=0xD, ESC=0x1B).
페이로드(가변, 총 <200B): [+0]type(1B) [+1]flag [+2]이름 13B(strncpy 0xd) [+0xf]0 [+0x10]msglen+1(1B)
[+0x11]메시지(가변, CP949). len = strlen+0x12.
- **slash 없음 → type=0 = 공개 채팅** (이름=빈문자, 메시지만)
- **`/이름 메시지` → type=1 = 귓속말**(directed). '/' 뒤 첫 토큰을 13B 타겟명(gm+0x345be)으로,
  나머지를 메시지로. `FUN_00520780` 검증 통과 시 전송.
- "로컬 vs 전체" 별도 구분 없음 — 채널은 공개(0)/귓속말(1) 둘. 이름 13B 고정, 메시지 ~182B 상한, CP949.

## 2. 채팅 수신 = S→C 0x6A (VERIFIED) — ApplyActorTextPayload

`HandleS2C_006A_ApplyActorTextPayload` @0x00615ff0. 페이로드: [+0]kind [+1]mode [+2]actor_id(4B)
[+6]primaryText(이름) [+0x15]secondaryText(메시지).
- actor_id → self(*(mgr+0x2f8))/remote(RemoteActor_FindByActorId) 해석.
- 이중 표시: 아바타 말풍선(Actor_SetSecondaryText + ActorText_UpdateScreenAnchor) + 채팅 로그
  (TextLog_EmitColoredMessageLines).
- **kind → 색상**: 0=흰(FFFFFF) · 1=빨강(FF0000) · 2=하늘(78FAC8) · 3=금색(FAEF77).
- 특수: actor_id==0 && kind==1 = 시스템 메시지, "name:message"를 콜론으로 분리 포맷.
- 다른 플레이어 채팅·자기 에코·시스템 공지 전부 0x6A.
- **⚠ 방향 비대칭**: S→C 0x68 은 `HandleS2C_0068_BatchActorState`(이동/상태 릴레이), 채팅 아님.

## 3. 커뮤니티 C→S 0x6C (VERIFIED 메커니즘, 명칭 INFERRED)

송신 `FUN_005ce8e0` → `FUN_005ab6a0(0x6c, buf, 4)`. 4B = 자기 actor id, **단 scene==0x6E(Plaza)일
때만 id, 아니면 0**. 트리거 = 버튼 0xb7(펫 액션 메뉴 FUN_005cc5c0), +0x2bd 플래그로 UI 패널 토글.
수신 `HandleS2C_006C` @0x00615410: payload[0]→remote actor field+0x336, payload[1]→+0x33A
(값<2면 set + FUN_00527760(0x30,0)), dword@+2=대상 actor id(self 무시).
- **친구/파티 로스터는 아님** (리스트 페이로드 없음, actor 상태 2바이트만 브로드캐스트).
- 구조상 아바타에 붙는 **상태/이모트 토글**(예: "대화중"/감정 표시)에 가까움. 정확한 UI 명칭은
  본문만으로 확정 불가 — **INFERRED: 이모트/상태 플래그**.

## 4. 펫 상호작용 C→S 0x18 (송신 VERIFIED, 표시 INFERRED)

송신 `FUN_005ab900` → `FUN_005ab6a0(0x18, buf, 3)`. 3B = [slot(0/1), kind(0-3), localId].
빌더 `FUN_005b2970`, 트리거 버튼 0x1d3(slot0)/0x1d4(slot1). localId = fullId − 10000*(kind+1)
(kind0=10000번대, 1=20000, 2=30000, 3=40000). slot 비면 **UI 패널코드 0x1a**(메뉴 전환) — ⚠ **네트워크 opcode 아님**(FUN_005bf2c0 패널 스위처, content/80 정정). 실제 재주 송신은 C→S 0x18(3B)뿐.
- 게이트 `FUN_005b2cb0`: 이 action id 들은 **펫 스탯으로 잠금해제되는 학습 능력/트릭**.
  예: id 10004 = 마법스탯 0x25-0x27 각 ≥100(매직클론/퍼니쉴드/에어훅, content/65), 10009 = stat0x1E≥200,
  20004 = 진화단계≥3, 40001-40007 = stat1(레벨) 임계.
- 즉 0x18 = 펫이 학습한 재주/트릭을 수행(소셜 과시)하는 요청.
- 표시: S→C 0x18 핸들러 없음 → 서버가 `HandleS2C_0069_ApplyActorActionState` @0x00615e70 로
  재브로드캐스트(액터에 action 레코드/애니메이션). 서버 소실이라 이 경로는 구조적 INFERRED.

## 확정 못한 것

- 0x6C 의 정확한 UI 명칭(친구/파티/이모션) — 상태 2바이트 메커니즘만 가시.
- 0x18 각 action id(10000-40000번대) 개별 의미·애니메이션 매핑 — 스탯 게이트만, id→애니 테이블 미추적.
- 서버 응답 실제 바이트(서버 소실) — S→C 핸들러 형태 역산 INFERRED.

Related: [[content/66_shop_item_economy_and_money_offset]] (C→S opcode 맵), [[content/56_...]] (0x0000 login),
INDEX. **0x00=login 정정은 content/66 §5 의 "0x00 chat" 표기를 대체.**
