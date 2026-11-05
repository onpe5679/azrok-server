# 선택 캐릭터 영속성 경계·동시 세션 fail-closed (2026-07-18)

VERIFIED=live wire/파일, 코드 직접 검토 또는 회귀 테스트로 확인. NOT VERIFIED=패치 후 원본 클라이언트 재검증 필요.

## 1. 사고 재현과 원인

- **VERIFIED (dynamic, seq116/117)**: 원본 `Ener103` 세션과 raw entity3가 동시에 연결된 상태에서 raw의 C→S `0005[00]` 선택은 exclusive lease로 거부됐습니다. 그런데 이어진 C→S `0013` item5000/total0은 S→C `0005` success를 받았고, `Ener103`이 아니라 bootstrap placeholder인 `Player` canonical에 `energy[0]=1`이 저장됐습니다.
- **VERIFIED (code review)**: `_client_protocol_context()`는 `proto_lock`을 context의 전체 yield 동안 보유하므로 두 socket thread의 `self.proto_state` swap/응답/저장은 직렬화됩니다. 이번 현상은 global context race가 아닙니다.
- **VERIFIED (root cause)**: `_process_purchase_0013()`가 선택 성공 여부를 검사하지 않고 `_load_canonical_character_state()`를 먼저 호출했습니다. `_character_state_key()`의 호환 fallback `Player/slot0`이 저장 권한처럼 사용된 fail-open입니다. 같은 선행 검증 부재가 item-use, C2S0007 저장, legacy raw loader/canonical overlay에도 있었습니다.

## 2. 구현된 영속성 경계

`azrok_server.py`에 다음 계약을 구현했습니다.

1. C→S `0004` 생성 또는 `0005` 선택이 lease 검사까지 성공한 뒤에만 `client_0005_seen=True`와 immutable `selected_character_key`를 함께 기록합니다.
2. 구매 `0013`, item-use `000D/000E/000F`, C→S `0007` 저장은 canonical load 전에 `client_0005_seen`과 `selected_character_key == 현재 account/slot/name key`를 모두 요구합니다.
3. mutation transaction은 검증된 key를 canonical load/save에 명시적으로 전달합니다. 선택되지 않은 구매는 status1/subtype13/balance0 ACK로 client lock만 해제하며 canonical/cache를 읽거나 만들지 않습니다.
4. `_load_character_state_snapshot()`과 `_apply_canonical_server_state()`도 선택 key가 없으면 즉시 false를 반환합니다. 따라서 bootstrap `Player`가 name-only legacy raw를 import하거나 Player canonical을 overlay하는 경로가 없습니다.
5. C→S `0017` stat55/56 authority는 선택 key가 있을 때만 수락하고 `c2s_0017_authority_key`를 함께 저장합니다. C2S0007 merge 시 동일 key만 인정하며 create/select/re-login 때 기존 authority를 지웁니다.
6. 같은 socket의 재로그인은 기존 dict를 유지한 채 내용만 `proto_template` fresh copy로 reset한 다음 새 account를 기록합니다. account A의 name/lobby slot을 account B가 첫 heartbeat 전에 선택하는 교차계정 바인딩을 차단합니다.
7. lease 비교는 다른 session의 bound `selected_character_key`를 권위값으로 사용합니다. mutable relay/bootstrap identity로 두 번째 캐릭터를 추론하지 않습니다.
8. 검증된 C2S0004 transaction을 거치지 않는 heartbeat auto-create는 `SERVER_AUTO_CREATE_ENABLED=False`로 비활성화했습니다. 비영속 world identity를 만들지 않습니다.

## 3. 회귀 테스트

**VERIFIED (tests)**:

- seq116/117 형태를 두 thread/두 protocol context로 재현: owner 구매는 owner canonical에만 commit, lease가 거부된 raw `Player` 구매는 failure ACK, Player canonical 미생성.
- unselected purchase/item-use/C2S0007 save는 canonical load 전 fail-closed.
- unselected zone overlay는 기존 `Player` legacy 196B raw를 import하지 않고 canonical도 만들지 않음.
- unselected C2S0017 stat55=999 뒤 정상 `Ener103` 선택/0007 저장에서 999가 bleed하지 않음.
- socket re-login accountA→accountB 뒤 stale EnerA slot 선택/구매가 거부되고 `accountB/EnerA` canonical이 생성되지 않음.

검증 결과:

- `python -m py_compile azrok_server.py tools/test_server_contract_layers.py tools/test_content_builders.py`: PASS
- `test_server_contract_layers`: **71 PASS**
- `test_content_builders`: **13 PASS**
- `test_server_room_mapping`: **7 PASS**
- `test_wmb6_minimap`: **5 PASS**
- 전체 discover: **96 PASS**

## 4. 남은 live 확인

- **NOT VERIFIED**: clean server restart 후 원본 `Ener103` 선택 세션과 raw 보조 세션을 동시에 연결하고, 보조 `0005` lease reject 뒤 `0013`을 보내 status1 ACK와 canonical SHA 불변을 재확인해야 합니다.
- live cleanup은 별도 동적 트랙 담당입니다. 이 수정에서는 실행 중 클라이언트나 원본/격리 canonical 파일을 조작하지 않았습니다.

Related: 84, 86, 90, 91, 98, protocol/82.
