# 117 — 단일 프로토콜 레지스트리·서버·GUI·캡처 분석기 통합 (2026-07-18)

표기: **VERIFIED**=현재 소스·테스트·API·실제 브라우저에서 직접 확인, **INFERRED**=확정 계약으로부터의 설계 판단, **NOT VERIFIED**=추가 원본 클라이언트 실측이 필요한 항목.

## 1. 결론

- **VERIFIED** `azrok_protocol_registry.py`를 부작용 없는 stdlib-only 권위 모듈로 추가했습니다. `PayloadRule`과 `ProtocolSpec`은 `frozen=True, slots=True`이고, direction/mode/opcode 인덱스는 `MappingProxyType`입니다.
- **VERIFIED** registry는 방향별 65개 spec을 갖습니다. 기존 capture inspector 63개, 명시적 미확정 C2S `000B`, 클라이언트 switch case가 없는 금지 tombstone S2C `00D1`의 합입니다.
- **VERIFIED** 현재 canonical spec id는 `sha256:308f3c74811c0f9fbb6f463aebe3d45acd49988447925988710b37f4cb81e8c3`입니다. 정렬된 typed JSON 전체의 SHA-256이므로 순서에는 무관하고 내용 변경에는 민감합니다.
- **VERIFIED** `azrok_server.py`, `azrok_control.py`, `azrok_control_page.py`, `tools/packet_capture_inspector.py`가 모두 이 registry를 소비합니다. 서버·control의 죽은 Python catalog와 GUI의 하드코딩 `const meaning={...}`는 제거했습니다.
- **VERIFIED** 전체 회귀 **150 tests OK**이며, 별도 TCP9211/control9304 무클라이언트 QA에서 typed registry 65행·spec id·교정 길이·D1 tombstone을 실제 브라우저 DOM으로 확인했고 console error는 0건이었습니다. QA 프로세스와 탭은 종료했습니다.

## 2. 정적 재감사로 확정한 교정

| 방향/opcode | 이전 과허용 | 현행 계약 | 판정/근거 |
|---|---|---|---|
| C2S `000D` | inspector exact 8B | exact 4B | **VERIFIED**, item-use 서버 decoder/90·98 |
| C2S `000E` | inspector exact 8B | exact 3B | **VERIFIED**, item-use 서버 decoder/90·98 |
| C2S `0065` | inspector exact 10B | minimum 10B | **VERIFIED**, `decode_c2s_0065` future tail 허용 |
| C2S `0067` | mode1 only | mode1/2 exact15 | **VERIFIED**, Plaza arrival + OX telemetry; OX answer authority는 CA |
| C2S `0068` | minimum 3B split decode | 18..199B + 내부 msglen/NUL 검증 | **VERIFIED**, `decode_c2s_0068_chat` |
| S2C `0067` | N×4 batch | exact4 single actor | **VERIFIED**, client handler에 반복 loop 없음; actor별 한 packet |
| S2C `00C9` | empty 허용 N×32 | non-empty N×32 | **VERIFIED**, OX remote actor record builder |
| S2C `00CA` | N×4 batch | exact4 single actor | **VERIFIED**, builder/validator exact one id |
| S2C `00CB/00CD` | N×4 | empty 허용 N×4 | **VERIFIED**, 빈 loser/final list 유효 |
| S2C `00D1` | registry 부재 | emit forbidden tombstone | **VERIFIED**, client switch case 없음 |

`C2S 0068`의 현행 layout은 `[type:u8][flag:u8][target:13B][NUL][msglen:u8][message CP949 + NUL]`입니다. 전체 길이는 `0x11 + msglen`, `msglen>=1`, target byte `+0x0F==0`, 마지막 byte `0`을 모두 만족해야 합니다. Inspector도 이제 내부 규칙 위반을 malformed로 보존합니다.

## 3. 구현 경계

### 3.1 Registry

- **VERIFIED** `PayloadRule`: exact/one-of, min/max, stride multiple, empty 허용 여부, operator display와 `length_error()`를 한 타입으로 제공합니다.
- **VERIFIED** `ProtocolSpec`: direction, allowed modes, stable name/id, label/category/risk, payload rule, decoder stable name, authority, persistence, relay, status, implementation, policy, evidence를 제공합니다.
- **VERIFIED** `registry_json()`은 `azrok.protocol.registry.v1`, spec id, typed 65 specs를 반환합니다.
- **VERIFIED** `legacy_contracts()`는 기존 GUI/API가 사용하던 6필드 row를 registry에서 투영합니다.
- **VERIFIED** 실제 live mode가 관측되지 않은 캡처에서 mode를 추측하지 않습니다. `find_spec(..., mode=None)`은 directional record를 반환하지만 `modes` 자체는 허용 범위로 유지됩니다.

### 3.2 Server semantics

- **VERIFIED** `_packet_semantics`의 meaning/category/risk는 `find_spec()`에서만 옵니다. relay/ox origin이 category를 임의 덮어쓰지 않습니다. 예를 들어 relay된 S2C `000C`도 `accessory`로 유지됩니다.
- **VERIFIED** packet ring에는 `protocol_spec_id`, `contract_length`, `contract_length_error`가 추가됩니다. 잘못된 S2C0067 8B는 `expected 4B`를 남깁니다.
- **VERIFIED** bounded binary decoder 실행은 현재도 서버 로컬 함수 체인입니다. metadata/length 권위는 단일화됐지만 decoder callable dispatch 자체의 완전한 registry 이관은 **NOT VERIFIED / 후속 P2**입니다.

### 3.3 Control API와 GUI

- **VERIFIED** `GET /api/protocol/specs`가 typed registry document를 그대로 반환합니다.
- **VERIFIED** 기존 `GET /api/protocol`은 `contracts`, accessory 정보에 `registry_schema`, `registry_spec_id`를 더해 하위 호환을 유지합니다.
- **VERIFIED** GUI 계약표·검색 의미·unknown 판정은 `/api/protocol/specs`에서 만든 `direction:opcode_hex` map 하나를 공유합니다. 비동기 로드 뒤 이미 렌더된 warning/packet도 다시 계산합니다.
- **VERIFIED** GUI는 registry schema·65 specs·전체 spec id를 표시하고 `persistence`, `room` category filter를 추가했습니다.

### 3.4 Capture inspector

- **VERIFIED** 기존 `CONTRACTS` API는 shared `ProtocolSpec`의 compatibility wrapper일 뿐이며 별도 opcode 표가 아닙니다.
- **VERIFIED** 길이 오류는 shared `PayloadRule.length_error()`를 직접 호출합니다.
- **VERIFIED** 문서화된 직접 실행 `python tools/packet_capture_inspector.py --help`가 root registry import 경로를 포함해 정상 동작합니다.
- **VERIFIED** chat 내부 msglen/NUL, 0067/00CA single actor, 00C9 non-empty batch decode/검증을 보강했습니다.

## 4. 검증 결과

### 4.1 자동 회귀

```text
python -m unittest discover -s tools -p 'test_*.py' -q
Ran 150 tests in 2.197s
OK
```

신규 회귀는 다음을 고정합니다.

- registry key uniqueness/불변성/spec id 결정성·민감성/typed·legacy projection
- C2S000B `NOT VERIFIED / observe only`, S2C D1 `forbidden / fail_closed`
- 000D 4B, 000E 3B, 0065 >=10B, 0068 18..199B
- S2C0067·00CA exact4, 00C9 non-empty N×32, CB/CD empty batch
- server semantics label/category/risk와 registry 동일성, relay category 보존
- typed/legacy control API parity와 GUI 하드코딩 meaning 재도입 방지
- inspector 직접 CLI 실행과 registry object identity

### 4.2 실제 브라우저 QA

별도 `protocol_registry_qa2` 무클라이언트 프로세스에서 확인했습니다.

```text
badge: azrok.protocol.registry.v1 · 65 specs · sha256:308f...e8c3
table rows: 65
0x00D1 visible: true
18..199B visible: true
category filters: persistence, room 포함
browser console errors: 0
```

QA는 새 GUI/API 렌더 검증이며 원본 클라이언트 패킷을 만들지 않았습니다. TCP9211/control9304 프로세스와 브라우저 탭은 검증 직후 종료했습니다.

### 4.3 기존 플레이 세션 보존 감사

- **VERIFIED read-only** 9207/9300은 `pathouse_stable`, 9208/9301은 `plaza_healthy`, 9209/9303은 client 0의 정상 idle이었습니다.
- **VERIFIED read-only** 9207/9208 heartbeat packet은 12초 동안 각각 RX/TX가 증가했고 unknown opcode는 0이었습니다.
- **VERIFIED read-only** main profile 3개 SHA와 mtime은 111/114 기준과 동일했습니다. 파일·클라이언트·패킷 조작은 없었습니다.
- **VERIFIED read-only** C: free는 감사 시점 27.74GiB로 기본 TEMP 회귀 실행에 충분했습니다.

## 5. 남은 범위

- **NOT VERIFIED** decoder callable을 registry에서 직접 dispatch하는 완전한 codec plugin 경계. 현재 stable decoder name은 기록하지만 서버와 inspector의 bounded decode 본문은 각 소비자에 남아 있습니다.
- **NOT VERIFIED** canonical transaction의 durable JSONL journal, character delete archive receipt, preview→CAS admin commit은 116의 후속 P1입니다.
- **NOT VERIFIED** 구조화 JSONL packet capture/run manifest/export는 105의 후속 P1입니다.
- **NOT VERIFIED** C2S000B, S2C0069, S2C006C의 내부 필드. 현행은 observe-only 또는 emit-disabled이며 서버 권위를 발명하지 않습니다.
- **VERIFIED guardrail** S2C00D1은 클라이언트 handler가 없으므로 emit forbidden 상태를 유지합니다.

