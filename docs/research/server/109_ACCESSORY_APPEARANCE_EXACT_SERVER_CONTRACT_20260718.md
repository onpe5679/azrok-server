# 액세서리·탈것 exact 서버 계약과 구현 (2026-07-18)

> **SUPERSEDES 107** 및 content/80의 `0x0018=펫재주/shared`, 105의 `b0 미확정·0066 respawn-only` 결론.

표기: **VERIFIED**=원본 바이너리 디컴파일·구현 테스트·원본 UI 실측 직접 확인, **INFERRED**=원본 서버 recipient 정책에 대한 최소 호환 정책, **NOT VERIFIED**=두 클라이언트 recipient 후속 필요.

## 결론

액세서리·탈것은 캐릭터별 4바이트 착용 상태입니다. 카탈로그와 해금 계산은 클라이언트 하드코딩이며 서버는 별도 소유 inventory를 저장하지 않습니다. 서버 권위는 다음 네 경로로 완결됩니다.

1. C→S `0x0018` exact3 장착/해제 commit
2. S→C `0x000C` exact7 self ACK·동일 방 remote delta
3. S→C `0x0007 +0x1D4` 로그인 복원
4. S→C `0x0066` 26B actor record `+0x14` 초기 appearance

## wire 계약

### C→S `0x0018 [action,slot,value]`

- **VERIFIED** `FUN_005AB900`의 실질 caller는 액세서리 팝업 `FUN_005B2970` 하나뿐입니다. 펫재주 공유 opcode가 아닙니다.
- button `0x1D3` (`mount_*.wis`) → `FUN_005B2970(0)` → `action=0` 장착.
- button `0x1D4` (`remove_*.wis`) → `FUN_005B2970(1)` → `action=1` 해제.
- slot은 0..3, value 범위는 slot0 `0..9`, slot1 `0..6`, slot2 `0..3`, slot3 `0..7`입니다.
- 해제 요청의 value는 현재 장착값입니다. 서버는 stale/forged clear를 막기 위해 canonical current와 일치할 때만 수락합니다.

### S→C `0x000C [actor_id:u32,clear_flag:u8,slot:u8,value:u8]`

- **VERIFIED** handler `HandleS2C_000C_ApplyActorSlotValue@006165B0`, exact 7B입니다.
- clear_flag=0이면 value 적용, nonzero면 value를 무시하고 effective `0xFF`로 해제합니다.
- self와 remote actor 양쪽을 처리합니다. self setter `FUN_005AB0E0`은 `PlayerState+0x1D8+slot*4`를 갱신합니다.

### 복원·초기 스폰

- **VERIFIED** S2C0007 payload `+0x1D4..+0x1D7`을 `DomainSelector_ImportByteVector4@005AB080`이 PlayerState 4 dword로 확장합니다.
- **VERIFIED** S2C0066 actor record stride는 `0x1A`; name `+0x07`, accessory bytes `+0x14..+0x17`, pair `+0x18..+0x19`입니다.

## 카탈로그와 해금

| slot | 의미 | 값 범위 | 빈 값 |
|---:|---|---:|---:|
| 0 | head effect/weather | 0..9 | FF |
| 1 | face/head | 0..6 | FF |
| 2 | back | 0..3 | FF |
| 3 | mount | 0..7 | FF |

`stat1`은 **VERIFIED 레벨**입니다. `CPopupAccessory+0x1CC` 생성자 9행도 직접 확정됐습니다.

| resource | slot/value | group | threshold | 추가 gate |
|---:|---|---:|---:|---|
| 20000 | 1/0 | 4 | 50 | 없음 |
| 20001 | 1/1 | 1 | 200 | 없음 |
| 20002 | 1/2 | 3 | 100 | 없음 |
| 20003 | 1/3 | 2 | 50 | 없음 |
| 20004 | 1/4 | 4 | 200 | evolution≥3 |
| 30000 | 2/0 | 4 | 100 | 없음 |
| 30001 | 2/1 | 5 | 200 | 없음 |
| 30002 | 2/2 | 3 | 150 | 없음 |
| 40000 | 3/0 | 2 | 150 | 없음 |

group 합은 g1=stat31..33, g2=34..36, g3=37..39, g4=stat30, g5=40..66입니다. 기본 tier1 항목은 클라이언트가 직접 허용합니다. 따라서 서버는 파생 해금만 검증하고 소유 목록을 영속하지 않습니다.

## 서버 구현

- canonical `accessory_slots` 기본 `FF FF FF FF`, slot별 값 범위와 JSON roundtrip 검증.
- C2S0018은 선택 캐릭터 binding과 활성 actor가 있어야 하며 canonical 저장 성공 전 emit 0건.
- action0은 범위·해금 검증 후 set, action1은 current!=FF와 submitted value==current일 때 clear.
- **VERIFIED implementation by 114** action0 해금 검증은 선택 캐릭터 canonical `snapshot_hex`의 evolution/stat1/group1..5/direct-stat을 사용합니다. locked forged set은 save/live-meta/self ACK/peer relay 전에 fail-closed합니다.
- 성공 뒤 송신자에게 actor id1 S2C000C ACK, 같은 room에서 sender를 볼 수 있는 peer에게 server entity id로 S2C000C relay.
- S2C0007과 S2C0066은 같은 canonical 4B source를 사용합니다.
- peer canonical read는 recipient identity cache를 오염시키지 않는 read-only 경계입니다.

**INFERRED compatibility policy**: 원본 서버의 exact recipient 집합은 캡처가 없지만 클라이언트가 self/remote를 모두 처리하므로 sender 포함 같은 방 가시 peer 중계가 최소 호환 정책입니다.

## 관제·inspector 반영

- GUI/API는 C2S0018을 accessory set/clear로, S2C000C를 remote appearance delta로 표시합니다.
- S2C0066 baseline 뒤 000C delta를 actor별 현재 4슬롯에 순차 적용합니다.
- level과 9행 해금표를 VERIFIED로 표시하며 shared/ambiguous/PARTIAL 표기를 제거했습니다.
- packet inspector는 exact length/decode/category/persistence를 제공하고 실제 캡처에 없는 0018/000C 행을 꾸며내지 않습니다.

검증: `py_compile` PASS. 111~114의 self/peer/entity projection, unlock authority, OX/cursor 회귀까지 전체 `python -m unittest discover -s tools -p 'test_*.py' -q` **131 tests PASS**.

## live 결과와 남은 관문

- **VERIFIED live by 111** Plaza 자연 UI에서 slot0/value0 장착은 `C2S0018 000000 → S2C000C 01000000000000`, 해제는 `C2S0018 010000 → S2C000C 01000000010000`으로 발생했습니다. canonical은 `[00,FF,FF,FF]` 뒤 FF×4로 원복됐습니다.
- **VERIFIED live by 112** 같은 Plaza의 두 원본 클라이언트에서 set은 peer `000C 02000000000000`, clear는 peer `000C 02000000010000`으로 중계됐고 원격 화면 효과의 생성·소멸까지 확인했습니다.
- **VERIFIED static/live by 112** clear는 catalogue 재선택이 아니라 현재 장착 슬롯 버튼 `0x1CD..0x1D0`을 선택한 뒤 `0x1D4`를 눌러야 합니다. catalogue `0x1C5..0x1CC`는 clear selector를 의도적으로 `-1`로 초기화합니다.
- **NOT VERIFIED live** set 상태 재접속 `0007` 및 이미 set된 actor의 신규 peer `0066` 화면 복원은 builder/contract test만 완료됐습니다.

Related: 80, 84, 103, 105, 111, 112, 114, archive/107, INDEX.
