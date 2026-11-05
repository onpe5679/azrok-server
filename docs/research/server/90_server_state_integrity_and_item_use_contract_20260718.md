# 서버 상태 무결성·아이템 사용 계약 (2026-07-18)

> **PARTIALLY SUPERSEDED by 98 and 104.** `000D/000E` sender body와 서버 수신 계약은 유효하지만, shipped `내 인벤토리` toy/gym UI에는 producer가 없습니다. `S2C0007 +0x125`도 toy/gym 복원 필드가 아니라 11×u8 furniture effect command입니다. 104는 lease reject 뒤에도 unselected `Player` canonical mutation이 가능했던 경계를 selected key 기반으로 추가 봉쇄했습니다.

## 상태

- **VERIFIED (static/Ghidra)**: `DomainCode_EmitLocalEffect@0059A6E0`, `FUN_0059C790`, `FUN_0059BFC0`, `DispatchState0Specific_S2C@0059DD20`을 기존 분석 DB에서 재디컴파일했습니다.
- **VERIFIED (server contract tests)**: `0x000D/0x000E/0x000F`, canonical-first 저장, 진화 edge, 동일 캐릭터 lease 회귀 테스트가 통과했습니다.
- **VERIFIED static/live negative (98)**: toy/gym UI producer 부재와 실제 UI 무패킷이 수렴했습니다. energy UI는 natural producer가 있으나 현재 보유량 0이라 pending/ACK 양성 실측은 남았습니다.

## 1. 아이템 사용 3종 exact wire

### C→S `0x000D` toy active loadout — VERIFIED static

- exact payload: **4바이트** local index 배열. 다만 `FUN_0059C790` 반환 count를 송신자가 무시하므로 기본 활성 3개뿐일 때 4번째 바이트는 미초기화 residue입니다.
- `model+0x3D4`의 vfunc가 활성 flag를 설정합니다.
- `FUN_0059C790(buf,100)`은 flag==1인 항목을 순서대로 순회하여 `itemId-base` 1바이트를 씁니다.
- 따라서 수량 소비가 아니라 **현재 활성 toy 4칸 전체 snapshot**입니다.
- 서버는 보장된 앞 3개와, 유효한 정렬·소유 조건을 만족할 때만 4번째를 loadout으로 인정합니다. ownership은 감소시키지 않습니다.

### C→S `0x000E` gym active loadout — VERIFIED static

- exact payload: **3바이트** local index 배열.
- toy와 동일한 active flag/serializer 구조이며 index 범위는 `0..7`입니다.
- 기본 활성 예시는 catalog `2500/2503/2506`, 즉 local `00 03 06`입니다.
- 서버는 `active_loadouts.gym`만 저장하고 ownership은 감소시키지 않습니다.

`FUN_0059ACD0`은 S→C0007 load setup마다 toy `2001/2004/2007`(local 1/4/7)과 gym `2500/2503/2506`(local 0/3/6)을 직접 1개 부여하고 활성화합니다. canonical fresh/legacy loader도 이 client-granted unique ownership을 최소 1로 seed하여 정상 기본 000D/000E가 unowned로 거부되지 않게 했습니다.

### C→S `0x000F` energy pending consume — VERIFIED static

- exact payload: **1바이트** local index `0..2`.
- 클라이언트는 `FUN_0059BFC0(0,itemId)`로 pending만 설정하며 이 시점에는 로컬 수량을 줄이지 않습니다.
- 성공 ACK는 S→C `0x0009` exact payload **`00 0F`**입니다.
- state-0 handler는 이 ACK에서 `FUN_0059BFC0(1,-1)`을 호출해 pending energy를 실제 로컬 감소시키고 UI를 갱신합니다.
- 서버는 canonical `energy[index]>0` 검증 → copy-on-write 1 감소 → atomic JSON 저장 성공 뒤에만 `S→C 0009[00 0F]`를 보냅니다.
- 실패 status 의미는 live 미확정이므로 forged/stale 요청에는 ACK를 꾸며내지 않고 fail-closed합니다.

## 2. canonical 저장 원자성 — VERIFIED tests

`C→S 0x0007` 저장은 canonical JSON을 먼저 임시파일+`os.replace`로 확정합니다. 그 뒤에만 메모리 cache와 legacy raw mirror를 갱신합니다.

- canonical 실패: raw/cache/proto metadata 모두 이전 세대를 유지합니다.
- raw mirror 실패: canonical은 이미 권위 저장이므로 성공 상태를 유지하고 warning event를 남깁니다.
- 이 순서로 raw 신세대/canonical 구세대 split-brain을 차단했습니다.

## 3. 진화 snapshot 단조성·kind3 exact edge — VERIFIED tests

- 서버 발행 `runtime_row_meta.issued_evolution` 또는 직전 canonical snapshot을 기준선으로 사용합니다.
- 같은 stage 저장은 허용합니다.
- `+1` 상승은 해당 kind3 aux가 요구하는 정확한 목표 stage, 발행 기준선 일치, stat/inventory 임계 충족 때만 허용합니다.
- stage 회귀, 2단계 점프, 임계 미달 상승, 첫 snapshot의 stage3 점프를 모두 거부합니다.
- legacy raw import에만 one-time route migration을 적용하며 일반 load/cached snapshot에는 route reconcile을 실행하지 않습니다.
- legacy/malformed canonical에 kind3 행이 둘 이상이면 가장 앞 한 행만 유지하고 나머지는 `FF`/generation0으로 sanitize하여 stale route 재노출을 막습니다.

## 4. 동일 캐릭터 exclusive lease — VERIFIED tests

동일 `(account_raw, storage_slot, char_name)`을 두 소켓이 동시에 선택하면 revision 없는 whole-snapshot `0007`이 서로 덮어쓸 수 있습니다.

- C→S `0005` 선택과 C→S `0004` 생성은 identity mutation/zone bundle 전에 다른 live session의 selected key를 검사합니다.
- 이미 활성인 key는 newcomer에서 fail-closed합니다.
- 연결 종료 시 `client_meta` 제거와 함께 lease가 자연 해제됩니다.
- invalid logical slot은 `character_slot`이나 relay identity를 바꾸지 않습니다.

104 보강: lease 거부 자체만으로는 후속 0013/000F/0007을 막지 못했습니다. 생성/선택 성공 시 immutable `selected_character_key`를 bind하고 canonical mutation·loader·overlay 전에 현재 identity와 일치하는지 검사합니다. 따라서 lease가 거부된 newcomer의 bootstrap `Player`는 어떤 다른 canonical에도 저장 권한이 없습니다.

## 5. 006C 안전성 정정 — VERIFIED static / semantics NOT VERIFIED

S→C `006C[ state, toggle, actorId ]`의 첫 두 바이트는 actor 필드에 실제 write되고 refresh를 호출합니다. `0/0`은 no-op으로 증명되지 않았습니다.

따라서 서버는 C→S `006C` exact 4B/self-id/Plaza 조건까지만 검증하고, state/toggle의 원본 서버 source가 live capture되기 전에는 S→C `006C`를 relay하지 않습니다. C→S `0018`→S→C `0069`와 같은 defer 정책입니다.

## 6. 검증

- `python -m py_compile azrok_server.py`: PASS
- `test_server_contract_layers`: **45 PASS**
- `test_content_builders`: **13 PASS**
- `test_server_room_mapping`: **7 PASS**
- 서버 계약 합계: **65 PASS**
- minimap 5개 포함 전체 discover: **70 PASS**

Related: 84, 86, 87, 89, content/66, content/80, protocol/82.
