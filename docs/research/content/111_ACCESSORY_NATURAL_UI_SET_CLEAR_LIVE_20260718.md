# 액세서리 자연 UI 장착·해제 live 종결 (2026-07-18)

표기: **VERIFIED**=원본 클라이언트 화면·wire·canonical 파일 또는 디컴파일/테스트로 직접 확인, **INFERRED**=후속 호환 정책, **NOT VERIFIED**=추가 recipient 대조 필요.

## 결론

109의 액세서리 계약을 원본 클라이언트 자연 UI로 종결했습니다. Plaza의 메뉴에서 `액세서리`를 열어 기본 해금 head-effect slot0/value0을 장착하고 다시 해제했으며, 클라이언트·서버·canonical이 정확히 왕복했습니다.

| 단계 | C→S | S→C | canonical |
|---|---|---|---|
| 장착 | seq99 `0018 000000` | seq100 `000C 01000000000000` | `[00,FF,FF,FF]` |
| 해제 | seq131 `0018 010000` | seq132 `000C 01000000010000` | `[FF,FF,FF,FF]` |

- **VERIFIED live** C2S0018은 exact3 `[action,slot,value]`입니다.
- **VERIFIED live** S2C000C은 exact7 `[actor_id:u32,clear_flag,slot,value]`이며 self actor id는 1입니다.
- **VERIFIED live** 해제 요청은 이전 장착값 value0을 그대로 보냅니다.
- **VERIFIED live** 장착 때 canonical SHA는 `4FFCFCF9...22360E6`로 바뀌었고 해제 뒤 slot 4바이트는 다시 FF×4입니다.

## 자연 UI 경로와 표시 게이트

정적 에이전트와 실제 화면이 수렴했습니다.

- **VERIFIED static** MainMenu queue consumer는 `FUN_005CC5C0`, `ButtonQueue_Pop` return은 `0x005CC5F1`입니다.
- **VERIFIED static** 액세서리 entry button id는 `0xBE`입니다. 기존 `0xC0` 추정은 다음 Setting 버튼의 역순 인자였습니다.
- **VERIFIED static/live** `CPopupMainMenu+0x76==2`에서 세 번째 행이 `액세서리`, mode0/1 PatHouse에서는 같은 자리에 `청소`가 표시됩니다.
- **VERIFIED static** mode2는 Hansol stage6에서 설정됩니다. 창 열기 자체에 레벨·진화 gate는 없습니다.
- **VERIFIED live** Plaza healthy(scene110/phase4/mode1/self1)에서 하단 메뉴를 열자 실제 세 번째 행에 `액세서리`가 나타났고 자연 클릭으로 `CPopupAccessory`가 열렸습니다.

PatHouse에서 hidden entry `0xBE`를 정확한 consumer에 강제 주입한 격리 PID24512는 주입 직후 종료됐습니다. 따라서 가시성 mode를 건너뛰어 창을 여는 방법은 안전하지 않으며, 원본의 Plaza mode2 경로를 따라야 합니다. 메인 PID104264와 `profile_playable_v2`는 이 음성 대조 실험에서 변경되지 않았습니다.

## 자연 장착·해제 조작

Plaza 액세서리 창의 1/5 페이지에서 첫 head-effect를 선택하고 `장착`을 눌렀습니다. 오른쪽 slot0 미리보기와 설명이 갱신된 뒤 seq99/100이 발생했습니다.

> **SUPERSEDED by 112.** 아래 당시의 “같은 catalogue 아이템 재선택” 해석은 잘못됐습니다. 정확한 clear selector는 ACK 뒤 현재 장착 슬롯 버튼 `0x1CD..0x1D0`입니다.

해제는 현재 장착 슬롯 선택 없이 `해제`만 누르면 `액세서리를 먼저 선택하세요` 로컬 안내가 나오며 wire는 0건입니다. 112의 정적·동적 재검증에서 slot0 장착 버튼 `0x1CD`를 선택한 뒤 `0x1D4`를 눌러야 clear가 발생함을 확정했습니다.

## 격리 런처·관제 개선

- 대체 인스턴스 런처 요청에 allowlist된 `content_profile`과 정규식 제한 `state_namespace`를 전달하도록 확장했습니다.
- 주 `profile_playable_v2`를 `profile_accessory_live`로 복제해 main과 쓰기를 분리하고, 통합 런처가 서버와 원본 클라이언트를 함께 소유해 메모리 readiness를 관측하게 했습니다.
- 검증된 PatHouse vtable/child fingerprint 뒤 허용된 문 opcode 등가 `S→C000D[00]` 1회로 요청 주도 calibration 5회→C2S/S2C0064→Plaza healthy를 확인했습니다.
- 관제의 self `current_self`가 0007 baseline에 머물던 버그를 수정했습니다. 이제 actor_id1의 000C delta를 순차 적용하고 baseline seq/source, runtime delta seq/source, canonical을 분리해 표시합니다.
- 전체 `python -m unittest discover -s tools -p 'test_*.py' -q` **120 tests PASS**입니다.

## 저장 불변과 증거

주 profile SHA는 작업 전후 모두 다음과 같습니다.

| 파일 | SHA-256 |
|---|---|
| `417a726f6b31_c2s0007.bin` | `875390B17961AB74EE4A64525F66B0D71EA80FD259224883E874830012BC817E` |
| `506c61796572_c2s0007.bin` | `821D08B97ADE675797AA2436094C275E4D02FD46E1BE144F32D1039B72762940` |
| `a706c...Azrok1_state_v1.json` | `D190456272D19D182FB9AA69F405373C31C13393F24A706FF190E71B35B0E31F` |

증거:

- `captures/packets_20260718_142936.txt`
- `artifacts/dynamic-analysis/accessory_live_clear_confirmed_20260718.bmp`
- `artifacts/dynamic-analysis/accessory_packets_inspector_20260718.json`
- `tools/artifacts/packet_capture_accessory_live_20260718.html`
- `artifacts/dynamic-analysis/accessory_live_evidence_20260718.json`

## 후속 상태

- **VERIFIED live by 112** 같은 Plaza room의 두 번째 원본 클라이언트가 sender set/clear에 대응하는 server entity id 2의 `000C`를 수신했고, 원격 머리효과가 생성·소멸했습니다.
- **VERIFIED static/live by 112** 해제는 catalogue 항목 재선택이 아니라 ACK 뒤 현재 장착 슬롯 `0x1CD..0x1D0`을 선택해야 합니다. 선택 없는 `0x1D4`의 로컬 안내와 wire 0건도 정상 전제조건입니다.
- 재접속 0007 +1D4와 이미 set된 actor의 신규 peer 0066 +14 화면 복원만 후속 실측으로 남습니다.

Related: 84, 105, 109, 110, 112, INDEX.
