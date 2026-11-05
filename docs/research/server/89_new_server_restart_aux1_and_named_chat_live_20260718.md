# 새 서버 clean restart: legacy snapshot fold + aux1 + 이름 채팅 실증 (2026-07-18)

## 상태

- **VERIFIED (동적 실측)**: 수정된 `azrok_server.py`로 TCP `9207`/control `9300`을 clean restart한 뒤, playable canonical `Azrok1`을 슬롯 0에서 선택해 PatHouse에 정상 진입했습니다.
- **VERIFIED (wire/API/파일)**: S2C `0x0007`은 `stage=1`, `currency=950`, `food[1001]=1`, 런타임 첫 행 `kind=3, aux=1, value=0`을 보냈습니다.
- **VERIFIED (두 실제 클라이언트)**: 두 클라이언트 모두 canonical 이름 `Azrok1`으로 Plaza에 진입했고, 실제 UI에서 보낸 `NEWSRV2`가 C2S `0x0068` 한 건과 양쪽 S2C `0x006A`로 relay되었습니다. peer 화면에도 `Azrok1 : NEWSRV2`가 렌더되었습니다.

## 발견한 재접속 결함과 수정

구 canonical JSON이 `snapshot_hex: null`, `runtime_rows[0]=kind3/aux0`인 채 이름 전용 legacy `417a726f6b31_c2s0007.bin`과 공존하면, canonical loader가 legacy 196바이트 snapshot보다 먼저 실행되어 stage 1을 보지 못했습니다. 모델과 통화는 복원되지만 런타임 행만 stage-0 route `aux0`으로 남는 순서 결함이었습니다.

`_load_character_state_snapshot()`의 이름 전용 legacy import 성공 지점에서 다음을 원자적 canonical 문서로 fold하도록 수정했습니다.

- legacy 196바이트 snapshot을 `snapshot_hex`에 저장
- stage 1이면 활성 kind3 행을 `aux1`, generation 2, issued_evolution 1로 승격
- 기존 통화와 서버 소유 inventory는 그대로 보존
- stage 2/3에도 기존 canonical migration과 같은 route/remove 규칙 적용

회귀 테스트 `test_name_only_legacy_snapshot_is_folded_into_existing_canonical_state`를 추가했습니다. 당시 전체 테스트는 `32 + 13 + 7 = 52`개 통과했습니다. 이후 저장 무결성·item-use 계약까지 포함한 현행 수는 90의 서버 65/전체 70 PASS입니다.

## 직접 증거

### 재접속 S2C 0x0007 파싱

`packets_log.txt`의 최신 S2C `0x0007` 472바이트 payload:

- `+0x02 = 1` (진화 stage)
- `+0x07 u32 = 950` (통화)
- `+0xEB = 1` (food 1001 수량)
- `+0x134 u16 = 3` (runtime kind)
- `+0x148 u16 = 1` (runtime aux)
- `+0x15C u32 = 0` (runtime value)

control API도 entity 2를 `name=Azrok1`, `room=PatHouse (local)`, `saved_state_loaded=true`, `persisted_evolution=1`, `server_currency=950`으로 보고했습니다.

### 새 코드의 두 클라이언트 실제 채팅

- C2S seq216 entity2 `0x0068`: `...084e45575352563200` (`NEWSRV2`)
- S2C seq217 entity2 `0x006A`: sender name 13바이트가 `417a726f6b31...` (`Azrok1`)
- S2C seq218 entity3 `0x006A`: sender name 13바이트가 동일하게 `Azrok1`

## 증거 파일

- `artifacts/dynamic-analysis/new_server_reconnect_aux1_state_20260718.json`
- `artifacts/dynamic-analysis/new_server_reconnect_aux1_ui_20260718.txt`
- `artifacts/dynamic-analysis/new_server_two_clients_plaza_state_20260718.json`
- `artifacts/dynamic-analysis/new_server_chat_packet_proof_20260718.json`
- `artifacts/dynamic-analysis/new_server_chat_peer_received_20260718.bmp`

## 실행 종료 상태

- **VERIFIED**: PID `86028`/entity2와 PID `83804`/entity3 모두 Plaza `room_kind=27`, `name=Azrok1`, peer_count 1, heartbeat 정상 상태로 유지했습니다.
