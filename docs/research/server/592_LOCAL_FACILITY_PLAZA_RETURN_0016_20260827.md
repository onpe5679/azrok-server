# 592 — 로컬 시설 퇴장 후 Plaza 복귀 `0016[01] -> 000D[00]`

날짜: 2026-08-27

## 결론

- **VERIFIED:** 마법학원에서 나갈 때 클라이언트는 C2S `0x0016[01]`을 보냈지만 기존 서버는 일반 heartbeat `0x0016[01]`만 반환했다. 이 때문에 장면이 Plaza로 전환되지 않았다.
- **VERIFIED:** 같은 클라이언트 세션에 S2C `0x000D[00]`을 수동 전송하자 C2S `0x0016[01]` 5회가 이어졌고, S2C `0x0004[01]` 5회 뒤 C2S/S2C `0x0064`가 완료되어 `room_kind=27`, `plaza (0064-only)`로 복귀했다.
- **VERIFIED:** 과거 Gym/Cook/Library 실측도 시설 퇴장 뒤 같은 `0x000D[00]`과 5회 calibration, `0x0064` 순서를 사용한다.
- **VERIFIED:** 공통 처리 대상은 로컬 시설 wire kind `0x06`–`0x0C` 전부다. 현재 이름표는 playroom, cook, gym, magic, library, shop, ground이다. PatHouse와 Plaza는 이 분기에서 제외한다.
- **VERIFIED:** 시설의 첫 C2S `0x0016[01]`에 heartbeat ACK와 `0x000D[00]`을 한 번만 보내고 calibration을 무장한다. 다음 kind-1 heartbeat부터 기존 `0x0004[01]` 표본 경로를 재사용한다.
- **VERIFIED:** 재기동된 실제 9200 코어에 magic `0x0065[09...]`와 `0x0016[01]`을 전송한 네트워크 probe가 첫 응답 `0016[00],000D[00]`, 후속 5회 각각 `0016[00],0004[01+u32]`를 반환했다.
- **NOT VERIFIED:** 서버 재시작 뒤 실제 UI에서 7개 시설을 각각 들어갔다 나오는 전수 사용자 수용 시험은 남아 있다.

## 직접 근거

### 현재 마법학원 재현

`captures/packets_20260827_113138.txt`

- C2S `0x0065`, wire room kind `0x09`으로 마법학원 진입.
- packet `#114`: C2S `0x0016[01]`; 기존 서버는 S2C `0x0016[01]`만 반환.
- 수동 S2C `0x000D[00]` 뒤 C2S `0x0016[01]` 5회와 S2C `0x0004[01]` 5회.
- packet `#169`: C2S `0x0064[00]`, 이어 S2C `0x0064` authoritative self.
- control overview: entity 14가 `room_kind=27`, `room_name=plaza (0064-only)`.

### 과거 공통 시설 재현

`captures/packets_20260719_011252.txt`

- facility C2S `0x0065` 뒤 퇴장 heartbeat.
- 수동 S2C `0x000D[00]`.
- C2S `0x0016[01]` 5회와 S2C `0x0004[01]` 5회.
- C2S/S2C `0x0064`로 Plaza 복귀.

## 변경

- `azrok_server.py`
  - `LOCAL_FACILITY_ROOM_KINDS`에 로컬 시설 `0x06`–`0x0C`를 공통 등록.
  - C2S `0x0065`에서 현재 시설 kind와 1회성 복귀 플래그를 기록.
  - 시설의 C2S `0x0016[01]`에서 `0x000D[00]`을 한 번 보내고 기존 Plaza calibration을 무장.
  - C2S `0x0064` 및 PatHouse `0x0005` 선택에서 시설 상태를 초기화.
- `azrok_protocol_registry.py`
  - C2S `0x0016`과 S2C `0x000D`에 확인된 시설 복귀 정책 및 문서 592를 등록.
- `tools/test_server_contract_layers.py`
  - 7개 시설 전부의 정확한 첫 응답과 다음 calibration 응답을 고정.
  - Plaza, PatHouse, room 미지정 상태에서 오발하지 않음을 고정.

## 검증

- `python -m unittest tools.test_server_contract_layers.LoginContractTests -v` — **12/12 PASS**.
- `python -m unittest discover -s tools -p 'test_*.py'` — **288/288 PASS**.
- 현재 실행 중 세션에서 수동 `0x000D[00]` 후 마법학원→Plaza 복귀 — **VERIFIED**.
- 새 자동 분기의 7개 시설 계약 — **VERIFIED**.
- 새 코어 PID 74332에서 9200/9300 listener 및 control overview `running=true` — **VERIFIED**.
- 새 코어의 실제 TCP magic 퇴장 및 5-sample calibration 응답 — **VERIFIED**.
