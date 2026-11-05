# 105 — 서버·GUI·프로토콜 운영면 대개편 청사진 (2026-07-18)

> **PARTIALLY SUPERSEDED by 109, 110, 111, 112, 114, 116, 117, 118, 119, 121.** 액세서리·cursor·revision/receipt·journal·단일 protocol registry·OX 자동화·structured capture의 현행 구현은 각 후속 문서를 따릅니다. CAS 관리·capture 검색/내보내기·service 분리 등 나머지 구조와 우선순위는 유효합니다.

표기: **VERIFIED**=현재 코드·테스트·캡처 형식을 직접 확인, **INFERRED**=확정된 계약을 실사용 서버 구조로 수렴시키는 설계 판단, **NOT VERIFIED**=원본 값 또는 실제 클라이언트 검증이 남음.

이 문서는 구현 청사진입니다. 이번 조사에서는 코드·런타임을 변경하지 않았습니다. 기준은 `84_SERVER_IMPLEMENTATION_CONTRACT`, 86~104, 현재 `azrok_server.py`, `azrok_control.py`, `azrok_control_page.py`, `azrok_ctl.py`, `tools/test_server_contract_layers.py`입니다.

## 1. 결론과 우선순위

현재 서버는 84의 얇은 5층과 109의 **6번째 액세서리·탈것 착용상태 층**을 구현했습니다. 110~112에서 P0 관제면과 self/remote 자연 UI 왕복을 검증했고, 114에서 cursor API·증분 GUI·OX 운영 패널·액세서리 unlock authority를, 116에서 canonical revision·exact-file SHA·RAM transaction receipt/GUI를, 117에서 typed 65-spec protocol registry 단일화를 구현했습니다. durable journal·delete archive receipt·CAS 관리 도구 등 나머지 P1/P2 항목은 계속 유효합니다.

| 우선순위 | 대개편 항목 | 판정 | 완료 기준 |
|---|---|---|---|
| **P0** | 선택 캐릭터 권한·lease·canonical revision 가시화 | VERIFIED gap | 잘못된 `Player` fallback과 교차 세션 mutation을 GUI/API에서 즉시 구별 |
| **P0** | canonical 상태를 의미 단위로 읽는 Character/Content/Economy 뷰 | VERIFIED gap | raw 196B hex 없이 통화·인벤토리·스탯·질병·runtime row 확인 |
| **P0** | 액세서리 4슬롯의 저장·복원·로스터 중계 층 | VERIFIED static/test/live | 캐릭터별 4B를 S2C0007 +1D4와 S2C0066 +14에 동일하게 적용 |
| **P0** | 모든 영속 mutation의 공통 transaction audit | VERIFIED gap | commit/reject마다 key·revision·before/after·reason 추적 |
| **P0** | 방향·mode·길이·권한을 포함한 단일 protocol registry | VERIFIED implemented by 117 | Python metadata/length/API/GUI/inspector 단일화; callable codec 분리는 P2 후속 |
| **P1** | `/api/state` 전체 폴링에서 cursor 기반 packet/event API로 분리 | VERIFIED implemented by 114 | 500ms 증분 cursor, 10초 full snapshot, gap/fallback 표시 |
| **P1** | 구조화 JSONL capture + run manifest + 검색/내보내기 | VERIFIED capture by 121 / 검색 미구현 | 텍스트 캡처와 함께 재현 가능한 기계 판독 증거 보존 |
| **P1** | OX 운영 콘솔과 멀티 room/relay 관측 강화 | VERIFIED implemented by 114/119 | 참가자·answer·deadline·generation·복귀 상태를 한 화면에서 관리 |
| **P1** | 안전한 canonical 관리 작업(preview→CAS commit→audit) | INFERRED | raw `proto_state` 편집 없이 격리 프로필을 관리 |
| **P2** | 서버 6층을 service/repository/codec 경계로 점진 분리 | INFERRED | `azrok_server.py` 단일 대형 객체를 계약별 테스트 가능한 단위로 분리 |
| **P2** | 103의 시간·NPC 등 로컬 콘텐츠 수용 슬롯 | VERIFIED local / 일부 NOT VERIFIED | 새 서버 권위를 발명하지 않고 액세서리 외 항목은 로컬/기존 층으로 분류 |

## 2. 현재 구현 현황 — 재작성하지 말고 보존할 것

### 2.1 서버와 API

- **VERIFIED** `azrok_server.py`는 로그인/캐릭터 생성·선택, directional `0007`, canonical JSON, 구매 `0013`, item-use `000D/E/F`, Plaza actor relay, 채팅, OX mode-2와 109의 액세서리 6번째 층을 한 프로세스에서 처리합니다.
- **VERIFIED** outbound는 `_emit()` 단일 chokepoint를 지나며 pause/step/drop, origin, capture, semantic packet ring을 제공합니다. 이 경계는 유지해야 합니다.
- **VERIFIED** control API는 localhost `ThreadingHTTPServer`이며 `/api/state`, `/api/send`, `/api/macro`, `/api/pause|step|drop`, `/api/protostate`, `/api/ox/*`를 제공합니다.
- **VERIFIED** OX는 별도 operation lock과 deterministic control API/CLI를 갖습니다. 대개편은 이를 일반 패킷 매크로로 되돌리지 않습니다.
- **VERIFIED** 선택/생성 성공 뒤 `selected_character_key`를 bind하고 구매/item-use/`0007` 저장/canonical overlay/`0017` authority를 fail-closed로 보호합니다(104).

### 2.2 GUI와 CLI

- **VERIFIED** 현재 GUI는 서버 건강, 클라이언트별 room/heartbeat/transition, 멀티 로스터, 최근 성장 수치, 패킷 의미·필터, event timeline, 수동 송신, 매크로, raw watches/proto state를 표시합니다.
- **VERIFIED** 최근 패킷은 `deque(maxlen=400)`, semantic event는 `deque(maxlen=200)`이며 `/api/state`에 매번 전체 배열로 포함됩니다.
- **VERIFIED** 패킷 record에는 `seq,t,dir,opcode,len,origin,hex,entity_id,meaning,category,risk,decoded`가 있습니다. 이 구조는 새 cursor API의 호환 기반으로 재사용할 수 있습니다.
- **VERIFIED** 텍스트 capture는 timestamped `captures/packets_*.txt`와 호환 로그를 남깁니다. 기존 증거 링크를 깨지 않도록 유지해야 합니다.
- **VERIFIED** CLI는 API의 얇은 client이며 state/packets/send/macro/pause/OX를 제공합니다. 새 기능도 GUI 전용으로 만들지 말고 동일 API를 공유해야 합니다.

## 3. 운영자가 현재 볼 수 없는 핵심 상태

### 3.1 권한과 영속성 경계 — P0

**VERIFIED gap**: player card에는 `client_0005_seen`, `selected_character_key`, 선택 key 일치 여부, lease owner, canonical revision이 없습니다. 104의 사고는 패킷상 “선택 거부 뒤 구매 성공”으로만 보였고, GUI에서 “로그인됨 / 캐릭터 권한 없음 / placeholder Player”를 즉시 구별하기 어려웠습니다.

새 API 필드:

```json
{
  "session": {
    "entity_id": 3,
    "auth_state": "logged_in_unbound",
    "selected_character_id": null,
    "identity_consistent": false,
    "lease_state": "selection_rejected",
    "mutation_allowed": false,
    "mutation_denial_reason": "selected character identity required"
  }
}
```

- `auth_state`: `connected | logged_in_unbound | character_bound | in_world | closing`.
- `selected_character_id`: raw account/name hex를 직접 노출하지 않는 서버 발급 opaque id. 내부 `selected_character_key`는 진단 펼침에서만 표시합니다.
- `identity_consistent`: bound key와 현재 account/slot/name key의 일치 결과.
- `lease_state`: `none | owned | held_by_other | selection_rejected`.
- `mutation_allowed`: canonical mutation 공통 gate 결과. 개별 handler가 따로 설명을 만들지 않습니다.

GUI: 각 client card 상단에 `UNBOUND`, `BOUND`, `LEASE CONFLICT`, `MUTATION BLOCKED` badge를 표시하고, unbound `Player`는 일반 캐릭터명처럼 렌더하지 않고 **bootstrap placeholder**로 명시합니다.

검증 방법:

1. 104의 두 session 재현에서 owner는 `bound/owned/allowed`, raw는 `unbound/selection_rejected/blocked`여야 합니다.
2. raw의 `0013`, `000F`, `0007` 뒤 canonical 파일·revision이 변하지 않고 audit reject만 생겨야 합니다.
3. 같은 socket 재로그인 뒤 이전 opaque character id와 lease가 즉시 사라져야 합니다.

84 연결: layer1의 생성/선택 bind와 layer2·4의 mutation 권한을 잇는 공통 경계입니다.

### 3.2 Character/Content/Economy 의미 뷰 — P0

**VERIFIED gap**: `/api/state.proto_state`는 bytes를 통째 hex로 직렬화합니다. GUI는 70 stat 일부와 진화만 해석하며 canonical inventory, currency, active loadout, runtime row generation, completed rows, 질병 mode/date를 직접 보여주지 않습니다.

제안 API:

- `GET /api/characters?scope=online|profile`: 현재 namespace의 roster와 online binding 요약.
- `GET /api/characters/{opaque_id}`: read-only canonical projection.
- `GET /api/characters/{opaque_id}/transactions?after=<id>&limit=<n>`: 해당 캐릭터 mutation audit.

canonical projection 최소 필드:

```json
{
  "character": {
    "id": "chr_...", "name": "Ener103", "storage_slot": 0,
    "species": 0, "evolution": 0, "level": 0,
    "online_entity_id": 2, "lease_state": "owned"
  },
  "persistence": {
    "schema_version": 1, "revision": 7,
    "canonical_sha256": "...", "updated_at": "...",
    "snapshot_present": true, "legacy_mirror_state": "synced"
  },
  "economy": {"currency": 950, "last_purchase": {}, "last_rejection": {}},
  "inventory": {
    "food": [{"local_index":1,"item_id":1001,"name":"...","quantity":1}],
    "toy": [], "gym": [], "energy": []
  },
  "active_loadouts": {"toy":[1,4,7],"gym":[0,3,6]},
  "accessories": {
    "slots":[255,255,255,255],
    "slot_labels":["head_effect","face_head","back","mount"],
    "persistence":"C2S 0x0018 action0=set/action1=clear / S2C 0x0007 +0x1D4",
    "relay":"S2C 0x000C delta / S2C 0x0066 record +0x14 baseline",
    "ownership":"derived_from_stats_not_persisted"
  },
  "stats": [{"index":32,"key":"gym_dumbbell","label":"아령","value":21,"status":"VERIFIED"}],
  "disease": [{"group":5,"mode":0,"packed_date":0,"status":"VERIFIED raw"}],
  "runtime_rows": [{"slot":0,"kind":3,"aux":1,"value":0,"generation":1,
    "policy":"exact_stage_edge_only","completion":"pending"}]
}
```

규칙:

- **VERIFIED** item id/name/price는 현재 서버 catalogue와 71의 decode를 사용합니다. unknown id는 삭제하지 않고 raw id로 표시합니다.
- **VERIFIED** stat index 31~36 등 이름이 확정된 항목만 semantic label을 붙입니다. 미확정 stat은 `stat_XX`와 `NOT VERIFIED`로 표시합니다.
- **VERIFIED** 질병은 mode/date raw 저장·복원만 서버 권위입니다. GUI가 발병 원인이나 남은 시간을 서버 확정값처럼 계산하지 않습니다(83/86).
- **VERIFIED** kind0/1/2/5는 `fail_closed_no_wire_witness`, kind3만 `exact_stage_edge_only`를 표시합니다(101). GUI의 “완료” 버튼을 만들지 않습니다.
- **VERIFIED** toy/gym `000D/E`는 future-compatible/dormant producer, energy `000F`만 natural UI path임을 inventory action 설명에 표시합니다(98/99).
- **VERIFIED** 액세서리는 inventory가 아니라 캐릭터별 착용 4바이트입니다. 슬롯은 `0=head effect 0..9`, `1=face/head 0..6`, `2=back 0..3`, `3=mount 0..7`, `0xFF=empty`로 표시합니다(109).
- **VERIFIED** 액세서리 소유 목록은 영속하지 않습니다. 해금은 이미 저장되는 stat의 순수 함수이므로 projection은 `equipped_slots`와 `derived_unlock_status`를 분리하고, 소유 inventory 배열을 만들지 않습니다(109).
- **VERIFIED by 109** `stat1=level`, `PlayerState+0x1CC` 9행의 resource/group/threshold와 group stat 범위가 확정됐습니다. GUI/API는 exact unlock evidence를 표시합니다.

검증 방법: 89/91의 playable fixture, 102의 빈/삭제 roster, 104의 Ener103/Player 사고 fixture를 golden projection으로 고정합니다. 472B S2C decode와 canonical projection의 currency/inventory/stage/runtime row가 일치해야 합니다.

84 연결: layer2 상태 저장/복원과 layer4 통화의 운영자 가시성입니다.

### 3.3 액세서리·탈것 4바이트 층 — P0

109가 103의 가장 큰 서버 갭을 exact wire까지 확정했고 111이 자연 UI wire를 실측했습니다.

- **VERIFIED** 서버 권위 영속값은 캐릭터당 액세서리 슬롯 4바이트뿐입니다. 카탈로그·모델명은 클라이언트 하드코딩입니다.
- **VERIFIED** self 복원은 S2C `0007 +0x1D4..+0x1D7`, remote spawn/roster 중계는 26B S2C `0066` record `+0x14..+0x17`입니다.
- **VERIFIED by 109** 클라이언트 commit은 액세서리 전용 C2S `0018 [action,slot,value]` exact 3B입니다. action0=set, action1=clear이며 clear value는 현재 장착값입니다.
- **VERIFIED** C2S `0007` 196B에는 액세서리가 없습니다. 따라서 서버는 검증된 C2S0018 분기에서 별도 canonical 4B를 갱신해야 합니다.
- **VERIFIED** 해금/소유는 별도 inventory가 아니라 stat-derived입니다. 기존 0007 stat 저장으로 재계산되며, 서버가 소유 목록을 새로 저장하지 않습니다.

서버/API 계약:

```json
{
  "accessories": {
    "equipped":[255,0,255,7],
    "wire":{"restore_offset":468,"relay_record_offset":20,"commit_opcode":"0x0018"},
    "commit":{"action0":"set","action1":"clear","status":"VERIFIED"},
    "ownership":{"model":"stat_derived","persisted_fields":0},
    "relay_status":"S2C 000C exact7 delta + S2C 0066 baseline"
  }
}
```

구현 fail-closed 경계:

1. C2S0018 action은 `0=set`, `1=clear`만 허용합니다. clear는 submitted value와 canonical current가 일치해야 합니다.
2. `slot 0..3`과 slot별 값 범위를 검증하며 canonical 저장 성공 전에는 emit하지 않습니다.
3. 109의 exact +0x1CC/stat1 해금표로 derived ownership을 검증하고 별도 inventory는 만들지 않습니다.
4. 로그인/재접속 S2C0007과 모든 S2C0066 actor record는 같은 canonical 4B source를 사용합니다.
5. mid-session 갱신은 S2C000C exact7로 self와 같은 방 가시 peer에게 보내고, 0066은 초기 baseline에만 사용합니다.

GUI: Character/Content 탭에 4개 slot과 exact derived unlock evidence를 표시합니다. packet inspector는 C2S0018 set/clear와 S2C000C effective value를 해독합니다. Multiplayer 탭은 S2C0066 baseline 뒤 000C delta를 actor별 현재 appearance에 순차 반영합니다.

109에서 기존 x32dbg 관문 3개는 모두 정적으로 직접 해소됐습니다. 남은 것은 원본 UI의 장착·해제 `0018→000C` live recipient 대조입니다.

검증 방법: disposable character에서 slot별 equip/unequip를 한 번씩 캡처해 C2S0018 action과 S2C000C recipient를 확인하고, 재접속 S2C0007 +1D4와 두 client S2C0066 +14가 같은 4B인지 비교합니다. +1CC/stat1 exact 값은 109의 정적 회귀로 고정합니다.

84 연결: 기존 layer2의 canonical 저장/복원과 layer3의 appearance relay를 묶지만, C2S0018 공유 opcode와 별도 4B 영속값 때문에 운영·테스트 관점에서는 **layer6 AccessoryAppearance**로 분리합니다.

### 3.4 공통 mutation transaction audit — P0

**VERIFIED gap**: 현재 `last_purchase`, `last_item_use`, `last_runtime_row_completion`과 event가 있지만, 모든 canonical 저장에 공통 revision/transaction id/before-after digest가 없습니다. `0007` 저장, legacy fold, 생성, 구매, energy consume, 삭제 archive를 한 timeline에서 비교하기 어렵습니다.

모든 영속 write는 다음 envelope를 남겨야 합니다.

```json
{
  "transaction_id":"tx_...", "kind":"purchase|snapshot_save|item_use|create|delete|migration",
  "entity_id":2, "character_id":"chr_...", "selected_key_valid":true,
  "request":{"opcode":"0x0013","packet_seq":116},
  "result":"committed|rejected|rolled_back", "reason":"...",
  "revision_before":6, "revision_after":7,
  "sha256_before":"...", "sha256_after":"...",
  "changed_fields":["currency","inventory.energy[0]"], "timestamp":"..."
}
```

- 성공·실패 모두 기록하되 비밀번호, 전체 account raw, 전체 snapshot hex는 제외합니다.
- revision은 canonical document 또는 sidecar manifest의 단조 증가 정수입니다.
- canonical 저장과 audit durable ordering은 명시해야 합니다. 최소 계약은 “canonical atomic replace 성공 후 committed audit”; audit 실패는 별도 high severity event입니다.
- 삭제는 archive target과 rollback 결과까지 기록합니다(102).

GUI: “최근 상태 변경” timeline에서 packet seq→transaction→파일 revision을 연결하고, reject는 이유와 함께 표시합니다.

검증 방법: save fault injection, delete 두 번째 replace 실패, 104 unbound purchase, energy ACK 전 durable commit을 각각 audit golden test로 추가합니다.

84 연결: layer2·4의 server authority를 운영 증거로 고정합니다.

## 4. Protocol registry 단일화 — P0

> **VERIFIED implemented by 117.** 아래는 당시 gap/설계 기록입니다. 현행 65-spec typed registry와 교정 계약은 117을 따릅니다.

**VERIFIED gap**: 의미 표가 `azrok_server.py::_packet_semantics`, `azrok_control_page.py` JavaScript `meaning/glossary`, 구 embedded page에 중복되어 있습니다. 같은 opcode가 방향과 client mode에 따라 다른데 registry key는 현재 주로 `(direction, opcode)`입니다. 현재 C2S `0068=채팅` 정정도 Python과 GUI 표에 각각 따로 반영되어 있어, 한쪽만 고치면 즉시 의미가 어긋나는 구조입니다.

registry record 제안:

```python
ProtocolSpec(
    direction='C2S', mode=1, opcode=0x0068,
    name='plaza_chat_send', category='community',
    payload_rule='variable<200', decoder='decode_c2s_0068_chat',
    authority='client_input', relay='same_room', risk='normal',
    implementation='implemented', evidence=['80','87','89'],
)
```

필수 필드:

- `direction`, `mode(0/1/2/common)`, `opcode`, `name`, `category`.
- `exact/min/max/multiple` payload constraint와 decoder/builder.
- `authority(client/server/local-only)`, `persistence effect`, `relay scope`.
- `risk`, `implementation status(implemented/fail_closed/dormant/not_verified)`.
- 권위 문서 번호와 최신 superseding 문서.

registry에서 자동 생성할 것:

1. 서버 packet validation/semantic decode.
2. `/api/protocol/specs` JSON.
3. GUI glossary와 unknown 판정.
4. CLI `protocol 0x0068 --direction C2S --mode 1`.
5. 문서용 opcode table 또는 CI drift report.

중요 정책:

- **VERIFIED** `0003/0007/0065~006C`처럼 방향별 의미가 다른 opcode를 절대 합치지 않습니다(75/82).
- **VERIFIED** mode-2 C8~D4는 state-1 표와 별도 namespace를 유지합니다(92~97).
- **VERIFIED** 006C는 서버 응답 필드가 부족해 `fail_closed`입니다. 0018은 액세서리 전용 set/clear commit, 000C는 appearance delta로 registry에 확정합니다. 000D/E는 `dormant sender`, kind0/1/2/5는 protocol completion 자체가 없음을 표현합니다(98/100/101/109).
- **NOT VERIFIED** 원본 서버 값은 빈 decoder 필드를 임의 0으로 채우지 않습니다.

검증 방법: 모든 기존 golden packet을 registry validator에 통과시키고 malformed exact-length tests를 자동 생성합니다. Python API 의미와 브라우저 표시가 같은 spec id를 반환해야 합니다.

84/109 연결: 6층 전체의 wire 계약을 단일 source of truth로 만듭니다. C2S0018 set/clear와 S2C000C delta를 별도 exact registry entry로 표현합니다.

## 5. Capture·검색·재현성 개편 — P1

### 5.1 cursor API

> **SUPERSEDED by 114.** 아래는 구현 전 gap 설명입니다. 현재 GUI는 500ms cursor 증분과 10초 full snapshot을 병행하며 gap/overflow/fallback을 명시합니다.

GUI는 과거 500ms마다 `/api/state` 전체를 받아 packet 400건과 event 200건을 다시 렌더했습니다. 114에서 `/api/overview`, `/api/packets`, `/api/events`와 bounded merge를 구현했습니다.

추가 API:

- `GET /api/overview`: server/clients/alerts/active profile의 작은 snapshot.
- `GET /api/packets?after_seq=123&limit=200&entity_id=2&direction=C2S&opcode=0x0007&category=content`.
- `GET /api/events?after_seq=44&limit=200&kind=purchase`.
- `GET /api/captures`: run manifest 목록.
- `GET /api/captures/{run_id}/download?format=text|jsonl`.

응답은 `items,next_seq,dropped_before_seq,run_id`를 포함합니다. GUI가 cursor gap을 만나면 “ring 이전 N건은 capture에서 검색”을 표시해야 합니다.

### 5.2 JSONL sidecar와 run manifest

기존 text capture는 유지하고 다음 구조화 sidecar를 병행합니다.

- `captures/<run_id>/packets.txt` — 사람/기존 도구 호환.
- `captures/<run_id>/packets.jsonl` — packet record + monotonic ns + wall time + entity/session + room/mode + registry spec id + decoded + raw hex + origin + transaction id.
- `captures/<run_id>/events.jsonl` — semantic event/audit.
- `captures/<run_id>/manifest.json` — server version, profile/namespace, config, started/stopped, clean shutdown, tests/build id, registry schema version.

민감정보: login `0000` payload의 password bytes는 JSONL decoded/raw export에서 기본 redaction합니다. 보존용 raw text가 필요하면 명시적 local diagnostic 설정과 경고가 있어야 합니다.

검증 방법: 한 packet이 text/JSONL/ring에서 같은 seq·opcode·payload digest를 갖는지, restart 두 번의 run id가 충돌하지 않는지, 비정상 종료 manifest가 `unclean`인지 검사합니다.

84 연결: 모든 layer의 직접 증거 보존입니다.

## 6. GUI 정보구조 대개편 — P1

한 화면에 raw 정보를 계속 추가하지 말고 다음 탭으로 나눕니다.

1. **Overview**: listen/profile/namespace/run id, clients, alerts, persistence health, latest commits/rejects.
2. **Players**: session auth/binding/lease, room/position/heartbeat/mode, visible peers.
3. **Character**: 선택 캐릭터 identity, canonical revision/SHA, semantic stats, evolution.
4. **Content**: inventory/loadout, disease raw mode/date, runtime rows와 fail-closed 정책.
5. **Economy**: currency, purchase request/commit/reject, item quantities, transaction timeline.
6. **Multiplayer**: room별 roster, 각 recipient가 보는 actor id/visible count, relay/drop/cap.
7. **OX**: rooms, phase, generation, deadline countdown, participants, answer side/timing/timeout, loser/survivor, C9/000D recovery.
8. **Protocol**: cursor log, registry inspector, decode detail, capture search.
9. **Diagnostics**: watches, pause/step/drop, manual send, raw proto state. 기본 접힘+위험 모드입니다.

실사용 원칙:

- raw hex보다 **원인→결과**를 우선 표시합니다. 예: `C2S0013 seq116 → tx42 rejected(unbound) → revision unchanged`.
- primary client만 memory watch가 있다는 사실을 카드마다 표시합니다. secondary에 primary scene/self를 섞지 않습니다(67).
- 상태 badge는 `confirmed/working/warning/error/not_verified`를 구분하며 “프로세스 응답”을 “게임 정상”으로 쓰지 않습니다(63/64/94/97).
- profile/namespace와 canonical path는 항상 헤더에 표시해 main/격리 프로필 혼동을 방지합니다(102).
- 페이지 reload 뒤 브라우저 메모리 기반 timeline이 사라지지 않도록 server event cursor를 사용합니다.

검증 방법: no-client, unbound client, PatHouse, Plaza healthy, two-client Plaza, OX active, OX C9 recovery, engine error, profile_minimal 빈 roster의 fixture snapshot으로 DOM smoke test를 만듭니다.

## 7. 안전한 운영 작업 — P1

현재 `/api/protostate`와 arbitrary `/api/send`는 분석에는 유용하지만 실사용 서버 관리 기능으로는 너무 낮은 수준입니다.

### 7.1 normal mode

- read-only overview/character/content/economy/protocol.
- 검증된 OX prepare/open/tick/finish.
- client disconnect 또는 lease release는 별도 명시 API와 확인 절차가 확정되기 전 제공하지 않습니다.
- raw proto edit/manual packet send는 숨깁니다.

### 7.2 diagnostic mode

- localhost only, 세션별 unlock phrase, 명확한 target entity, payload decode preview, risk spec 표시.
- `0065`, `006E`, `000D` 등 transition packet은 현재 scene/mode readiness preflight와 이중 확인.
- 모든 manual/macro mutation은 audit에 operator action으로 남깁니다.

### 7.3 canonical admin transaction

**INFERRED** 보존 운영에는 격리 프로필의 통화·아이템·row 복구가 필요할 수 있습니다. 이를 raw JSON 편집으로 하지 말고 다음 순서를 강제합니다.

`GET projection → POST preview patch(expected_revision) → diff/validation → confirm token → atomic CAS commit → audit → optional reconnect notice`

허용 후보: currency set, catalog item quantity set, active loadout normalize, runtime row clear/issue(kind3 verified routes only), archived character restore. 기본은 offline character 또는 lease owner가 없는 경우만 허용합니다.

금지: 미확정 006C/0069 필드 생성, kind0/1/2/5 강제 완료/콘 지급, 질병 서버 판정, toy/gym natural use가 있었다고 위조, 원본 자산 업로드.

검증 방법: stale revision 충돌, invalid item id, quantity overflow, online lease conflict, atomic write failure, audit failure를 모두 fail-closed 테스트합니다.

84 연결: layer2·4를 운영할 수 있게 하되 클라이언트 로컬 권위와 미확정 원본 값을 침범하지 않습니다.

## 8. OX·멀티플레이 운영 콘솔 — P1

### OX

- **SUPERSEDED by 114** OX phase/deadline/participant/answer와 prepare/open/tick/finish(CD/D2/D4) 전용 panel을 구현하고 브라우저 렌더·confirm을 검증했습니다.
- 표시 필드: room id, phase, generation, question index/text/type/correct side/stars, opened/deadline/remaining ms, participants(entity/wire self id), answers(side/current/dest/timing/timeout/generation), survivors/losers, finish cause(CD/D2/D4), C9 received, 000D recovery armed/completed.
- 동작: prepare/open/tick/finish/counter/configure를 form validation과 현재 phase 기반 enable/disable로 제공합니다.
- **SUPERSEDED by 119:** auto scheduler는 기본 활성화지만 자연 C→S C8 이후에만 작동하고 unsolicited 006E는 금지합니다. 기존 explicit deterministic controller도 유지되며 GUI/API에서 on/off할 수 있습니다. 시간값은 INFERRED/configurable입니다.

### Multiplayer

- room별 source→recipient relay matrix, recipient-local actor id 변환, visible remote id set, 100-slot cap/drop 이유를 표시합니다.
- room move/leave event는 packet seq와 함께 표시합니다.
- 006C deferred event는 `원본 서버 필드 부재로 릴레이 안 함`, 0018/000C는 `액세서리 canonical commit/appearance delta`로 서로 다르게 설명합니다.

검증 방법: two-client named chat(89), targeted leave(67), OX active side0+timeout+C9+000D recovery(97)의 capture를 replay-free fixture로 사용합니다.

84 연결: layer3 actor relay, layer5 chat, OX mode-2 운영면입니다.

## 9. 서버 내부 구조의 점진 분리 — P2

대개편은 big-bang rewrite가 아니라 다음 seam을 순서대로 추출합니다.

```text
Transport/Connection
  └─ ProtocolRegistry + Codec
       └─ SessionService (layer 1)
       └─ CharacterStateRepository + StateService (layer 2)
       └─ MultiplayerRelay + OXService (layer 3)
       └─ EconomyService (layer 4)
       └─ CommunityService (layer 5)
       └─ AccessoryAppearanceService (layer 6)
            └─ ControlProjection/Audit (read model)
```

- `CharacterStateRepository`: key/path/cache/atomic save/revision/archive만 담당.
- `SessionService`: login/create/select/relogin/binding/lease만 담당.
- `StateService`: 196B↔472B directional mapping, sanitize, runtime row policy.
- `EconomyService`: catalogue/purchase/item-use와 transaction result.
- `MultiplayerRelay`: room membership, recipient-local actor ids, relay cap.
- `OXService`: 이미 존재하는 lock/state machine을 독립 interface로 감쌉니다.
- `AccessoryAppearanceService`: selected character의 4B 착용상태, 검증된 C2S0018 분기, S2C0007 +1D4 복원, S2C0066 +14 appearance projection을 담당합니다. stat-derived 해금은 inventory repository에 넣지 않습니다.
- `ControlProjection`: live mutable dict를 그대로 반환하지 않고 immutable DTO를 만듭니다.

첫 추출은 ProtocolRegistry와 ControlProjection이어야 합니다. wire 처리 코드를 옮기기 전에 관측/테스트의 single source를 확보해야 회귀를 잡을 수 있습니다.

검증 방법: 기존 96 tests를 그대로 통과시킨 뒤 layer별 golden/contract tests를 이동합니다. 기능 변경과 파일 분리를 한 commit에 섞지 않습니다.

## 10. 103/109 신규 콘텐츠의 수용 경계 — layer6 VERIFIED static/test/live

103이 발견한 액세서리·탈것은 109에서 서버의 6번째 층으로 계약화됐고 111에서 자연 UI set/clear가 실측됐습니다. 달력/낮밤·NPC 등 나머지는 로컬 또는 기존 상태층에 흡수되며 새 영속 서버 필드가 확인되지 않았습니다.

- **VERIFIED** canonical 신규 필드는 `accessories: [u8;4]` 하나입니다. mount는 별도 시스템이 아니라 slot3이므로 별도 mount inventory/state를 만들지 않습니다.
- **VERIFIED** restore/relay 위치는 각각 S2C0007 `+0x1D4`, S2C0066 record `+0x14`입니다. 기존 toy/loadout 필드로 재해석하지 않습니다.
- **VERIFIED** 소유 목록은 stat-derived이므로 canonical inventory migration이 없습니다.
- **VERIFIED by 109** C2S0018 action0/1 persistence는 exact validation·binding·atomic save 뒤에만 허용합니다.
- **VERIFIED by 109** +0x1CC 9행, group threshold, stat1=level이 확정되어 서버의 해금 검증에 반영됐습니다.
- **VERIFIED by 111/112** mid-session appearance는 자연 `0018 exact3 → 000C exact7`로 self와 같은 방 peer 모두 set/clear되며, recipient-local actor id와 원격 화면 효과 생성·소멸까지 실측됐습니다.
- GUI의 `Time / NPC`는 서버 상태인 것처럼 만들지 않고 local-content inventory 문서 링크 또는 `no server authority`로 표시합니다.

검증 방법: 109의 slot/value 범위 golden test, S2C0007/S2C0066 동일 4B projection test, invalid/unbound C2S0018 무변경 test와 disposable two-client live를 요구합니다.

84 연결: 기존 5층을 깨지 않고 layer2 영속과 layer3 appearance relay 사이에 액세서리 전용 6번째 층을 추가합니다.

## 11. 단계별 구현 순서와 release gate

### Phase A — 관측 정확성(P0)

1. protocol registry 생성, 기존 Python semantic decoder 이관.
2. session binding/lease projection과 character opaque id.
3. read-only canonical projection.
4. 액세서리 4B canonical/restore/relay projection과 C2S0018 unresolved gate.
5. 공통 transaction audit/revision.
6. GUI/CLI를 새 projection/spec에 연결.

Release gate: 104 동시 session 회귀에서 unbound mutation 0건, playable/minimal profile 혼동 0건, registry/GUI meaning drift 0건.

### Phase B — 실사용 GUI·capture(P1)

1. ~~overview/packets/events cursor API~~ — **VERIFIED implemented by 114**.
2. ~~mutation receipt JSONL journal~~ — **VERIFIED implemented by 118**.
3. ~~structured packet JSONL/run manifest/free-space health~~ — **VERIFIED implemented by 121**. disk 검색/내보내기 API는 별도 미구현.
4. 탭형 GUI, Character/Content/Economy/OX view.
5. diagnostic mode 분리와 위험 preflight.
6. 선택적으로 canonical preview/CAS admin transaction.

Release gate: 장시간 packet ring overflow에서도 cursor gap이 명시되고 disk capture로 연결, two-client/OX/energy live에서 packet→transaction→revision 추적 가능.

### Phase C — 내부 모듈화·신규 콘텐츠(P2)

1. repository/service seam 점진 추출.
2. fault/concurrency tests 확대.
3. 109 액세서리 layer6을 service seam으로 분리하고, 남은 103 항목은 새 wire가 확정된 경우만 schema/relay에 추가.

Release gate: 기존 원본 클라이언트 end-to-end 방/미니게임/상점/멀티/OX 회귀가 모두 통과하고 main profile SHA가 의도 없는 변경 없이 유지.

## 12. 전체 검증 매트릭스

| 84 layer | 자동 검증 | live 검증 | GUI 증거 |
|---|---|---|---|
| 1 로그인/부트스트랩 | malformed login, create/select/delete/relogin, lease | 원본 로비→선택→PatHouse | auth/binding/lease state와 roster |
| 2 상태 저장/복원 | 196B/472B golden, sanitize, atomic fault, revision | gym/playroom stat 저장→재접속 | semantic stats, disease raw, runtime rows, SHA/revision |
| 3 actor/OX | relay id/cap, OX codec/lifecycle/concurrency | 두 client 이동/퇴장, OX CA/C9/복귀 | room matrix, answer/deadline/recovery |
| 4 통화/구매 | forged total, insufficient, unique/overflow, unbound | 구매/재접속, energy `000F→0009` | balance/inventory transaction diff |
| 5 chat/social | 0068 decode/relay, 006C/0018 defer | 두 client named chat | message delivery와 deferred reason |
| 6 accessory appearance | 4B range, unbound/stale-clear fail-closed, 0018/000C/0007/0066 projection 일치 | slot별 equip/unequip→재접속→두 client appearance | equipped/unlock evidence/action/relay bytes |

최종 사용자 플레이 release gate는 “API 성공”이 아니라 원본 클라이언트 화면·wire·canonical 파일이 함께 일치하는 것입니다. 각 기능은 `VERIFIED static/test/live` 세 칸을 독립적으로 표시하고, 하나가 빠지면 GUI에서도 미완료로 남겨야 합니다.

## 13. 즉시 구현할 최소 묶음

대개편의 첫 실제 변경 묶음은 다음 다섯 개로 제한하는 것이 안전합니다.

1. `ProtocolSpec` registry + `/api/protocol/specs`.
2. `/api/overview`의 session `auth_state/binding/lease/mutation_allowed`.
3. `/api/characters/{id}` read-only canonical projection.
4. canonical `revision` + 공통 transaction event envelope.
5. 액세서리 4B projection, C2S0018 set/clear, S2C000C delta, S2C0007/0066 builder 연결.
6. GUI의 Players/Character/Content/Economy 세 탭과 unbound mutation 경고.

이 묶음은 110~114에서 구현·실측됐습니다. 104 유형의 오류와 84 layer2/4, 109 layer6의 실제 플레이 저장·appearance를 raw hex 없이 검증할 수 있고, cursor 증분 관제와 OX 운영 panel까지 동작합니다. transaction audit·CAS·모듈 분리는 그 위에서 진행합니다.

Related: 66, 67, 71, 75, 80, 82, 83, 84, 86~104, archive/107, 109, 110, 111, `docs/superpowers/specs/2026-07-17-server-control-panel-design.md`.
