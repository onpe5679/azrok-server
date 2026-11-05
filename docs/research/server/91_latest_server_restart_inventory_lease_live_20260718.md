# 최신 서버 clean restart·기본 소유권·exclusive lease 동적 실증 (2026-07-18)

> **ITEM-UI INTERPRETATION SUPERSEDED by 98.** 아래 toy 탭 무패킷은 미완료 조작이 아니라 shipped UI에 `000D/000E` producer가 없다는 정적 callgraph와 수렴한 음성 증거입니다.

## 상태

- **VERIFIED (live/UI/wire/API)**: 최신 `azrok_server.py`로 playable 서버와 주 클라이언트를 clean restart하고, 실제 캐릭터 선택 UI에서 `Azrok1` 슬롯 0을 선택해 PatHouse에 진입한 뒤 Plaza state-1까지 정상 전환했습니다.
- **VERIFIED (S2C 0x0007 direct decode)**: stage 1, currency 950, food1001 수량 1, toy 기본 local `1/4/7` 수량 1, gym 기본 local `0/3/6` 수량 1을 같은 472바이트 payload에서 확인했습니다.
- **VERIFIED (live exclusive lease)**: 같은 계정·같은 캐릭터를 두 번째 클라이언트가 C2S `0x0005[00]`으로 선택하자 서버가 zone bundle을 한 바이트도 보내지 않고 fail-closed했습니다. 두 번째 화면은 캐릭터 선택 화면에 남았고 `saved_state_loaded=false`였습니다.
- **NOT VERIFIED (live item-use)**: 실제 인벤토리 UI까지 열어 장난감 탭의 기본 소유 슬롯을 클릭하고 닫았지만 C2S `0x000D/000E/000F`는 발생하지 않았습니다. 명확한 equip/consume 동작을 더 추정해 누르지 않았으며 90의 live item-use gap은 유지합니다.

## 1. 실행 정리와 clean restart

기존 세션의 보조 PID `83804`만 `REQUEST_CLOSE_AZROK_INSTANCE.json`의 PID+UTC 시작시각 고정 요청으로 닫았습니다. 주 PID `86028`과 서버가 보존된 것을 확인한 다음, 요청 마커가 없는 상태에서 `Azrok-Plaza-Stop`으로 전체 종료하고 one-shot `playable` 프로필로 재기동했습니다.

새 주 클라이언트는 PID `58280`, server entity 2입니다. 로비의 실제 슬롯 선택과 접속 버튼을 클릭했고 API는 다음을 보고했습니다.

- `name=Azrok1`
- `room=PatHouse (local)`
- `saved_state_loaded=true`
- `persisted_evolution=1`

## 2. S2C 0x0007 복원 direct decode

최신 `packets_log.txt`의 S2C `0x0007` payload는 정확히 472바이트였습니다.

| 필드 | wire 값 | 판정 |
|---|---:|---|
| `+0x02` evolution | `1` | VERIFIED |
| `+0x07 u32` currency | `950` | VERIFIED |
| `+0xEB` food local1 / item1001 | `1` | VERIFIED |
| `+0x113..0x11C` toy | `[0,1,0,0,1,0,0,1,0,0]` | VERIFIED |
| `+0x11D..0x124` gym | `[1,0,0,1,0,0,1,0]` | VERIFIED |
| `+0x134/+0x148/+0x15C` runtime row0 | `kind3/aux1/value0` | VERIFIED |

이는 90에서 정적으로 확인한 S2C load setup의 client-granted 기본 ownership과 일치합니다.

## 3. Plaza 실제 전환

서버가 지원하는 S2C `0x000D[00]` 전환 prelude를 entity 2에 한 번 보냈습니다. 그 뒤 클라이언트가 실제로 calibration 요청과 C2S `0x0064[01]`을 생성했고 서버는 S2C `0x0064`로 응답했습니다.

최종 건강 상태:

- `scene=110`, `phase=4`
- `dispatch_mode=1`, `self_actor_id=1`
- `state1_ready=true`, `heartbeat_recent=true`
- `transition=plaza_healthy`

## 4. 동일 캐릭터 exclusive lease live

reuse-server 보조 PID `99396`/entity 3을 띄우고 같은 로비 슬롯 0을 실제 UI로 선택했습니다.

- seq70: entity 3 C2S `0x0005`, payload `00`
- 그 뒤 entity 3에는 heartbeat `0x0016`만 왕복
- S2C `0x0003/0007/0005/000A/000B` zone bundle은 0건
- entity 3 `saved_state_loaded=false`, `client_0005_seen` 미설정
- 화면은 캐릭터 선택 화면에 그대로 유지

보조 PID `99396`도 PID+UTC 시작시각 고정 narrow-close로 종료했습니다. 주 PID `58280`과 서버는 영향 없이 유지되었습니다.

참고: control UI metadata는 C2S0005 관측만으로 `PatHouse (local)`을 표시하지만, 이는 zone bundle 전송 증거가 아닙니다. wire와 per-client proto가 권위이며 두 값은 fail-closed를 직접 입증합니다.

## 5. 실제 아이템 UI 확인 범위

Plaza에서 `메뉴 → 내가방 → 장난감` 탭을 실제 UI로 열었습니다. 기본 아이템 UI가 표시되었고, 기본 소유로 예상되는 슬롯 하나를 클릭한 뒤 인벤토리를 닫았습니다. 이 안전 범위에서는 C2S `0x000D/000E/000F`가 한 건도 발생하지 않았습니다.

따라서 다음은 추정하지 않습니다.

- 단순 탭/슬롯 선택이 equip commit이라는 주장
- 장난감 클릭만으로 0x000D가 발생한다는 주장
- 에너지 수량 0 상태에서 0x000F 소비를 강제하는 동작

원본 UI의 명확한 equip/consume commit 동작을 식별하거나 energy를 정당한 구매/보상 경로로 보유한 뒤 별도 live 검증이 필요합니다.

## 증거

- `artifacts/dynamic-analysis/latest_narrow_close_secondary_20260718.txt`
- `artifacts/dynamic-analysis/latest_primary_s2c0007_decode_20260718.json`
- `artifacts/dynamic-analysis/latest_primary_pathouse_state_20260718.json`
- `artifacts/dynamic-analysis/latest_primary_plaza_state_20260718.json`
- `artifacts/dynamic-analysis/latest_primary_plaza_20260718.bmp`
- `artifacts/dynamic-analysis/latest_exclusive_lease_packet_slice_20260718.json`
- `artifacts/dynamic-analysis/latest_exclusive_lease_rejected_state_20260718.json`
- `artifacts/dynamic-analysis/latest_exclusive_lease_rejected_20260718.bmp`
- `artifacts/dynamic-analysis/latest_exclusive_lease_secondary_closed_20260718.txt`
- `artifacts/dynamic-analysis/latest_item_ui_myroom_20260718.bmp`
- `artifacts/dynamic-analysis/latest_item_ui_toy_tab_20260718.bmp`
- `artifacts/dynamic-analysis/latest_restart_lease_item_packet_slice_20260718.json`
- `artifacts/dynamic-analysis/latest_final_live_state_summary_20260718.json`

## 최종 실행 상태

- 서버 TCP `9207` / control `9300`: running
- 주 PID `58280` / entity 2: `Azrok1`, Plaza healthy, heartbeat 정상
- 연결 클라이언트: 1
- 보조 클라이언트: narrow-close 완료

Related: 84, 89, 90, protocol/82, content/66.
