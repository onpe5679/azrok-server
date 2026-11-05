# 서버 수렴 2차 — 런타임행·채팅 live·OX 위치 제출 (2026-07-18)

> **OX SECTION PARTIALLY SUPERSEDED by 92.** 0066/0067 위치 제출 결론은 유지되지만, mode-2 S→C `C8..D4`, CE 정답 side와 CB 패자목록이 추가 확정됐습니다. 원본 cutoff/tie-break는 클라이언트가 아니라 소실된 서버 영역입니다.

84/86의 서버 5층 구현을 이어서 정적 분석, 실제 두 클라이언트 실측, 회귀 테스트를 서버 코드로 수렴한 기록입니다.
VERIFIED=디컴파일 또는 wire/UI 실측, INFERRED=근거가 강하지만 원본 판정 시점/값이 미실측,
NOT VERIFIED=추가 동적 확인이 필요한 항목입니다.

## 1. Layer 1/2 슬롯·상태 무결성 (VERIFIED by contract tests)

- 로비 wire 슬롯은 항상 dense `0..count-1`이며 실제 저장 슬롯은 `storage_slot`으로 분리합니다.
- C→S `0004` 생성은 정확한 다음 논리 슬롯만 허용하고, 빈 physical slot에 canonical 문서를 즉시 저장합니다.
- C→S `0005` 선택은 정확히 1B이며 occupied slot만 허용합니다. 선택한 species/stage가 S→C `0007 +1/+2`를 구동합니다.
- 손상 species/stage는 유효 모델로 승격하지 않고 거부/안전값 처리합니다.
- C→S `0006` 삭제는 dense tail만 허용합니다. canonical/196B/legacy name-only 파일을 함께 archive하며 중간 실패 시 역순 rollback 후 failure ACK를 보냅니다.

## 2. kind3 진화 런타임행의 안전한 서버 완료 판정 (VERIFIED static + contract)

`RuntimeRowTable_ImportFrom0007@005A5AB0`은 S→C `0007`의 10행을
`logic+70C`에 import합니다. `QuestEval@005A6910`은 가장 앞의 일치 행 하나만 완료하고
`005A5EC0`이 그 행의 kind만 `FF`로 만듭니다.

- kind3 aux `0 → evolution1`, `1..3 → evolution2`, `4..6 → evolution3`입니다.
- `Kind3Commit@005A7E40`의 실제 호출자는 평가기이며, kind3에는 통화 callback이 없습니다.
- 서버는 각 행에 `generation`과 `issued_evolution`을 저장합니다. 이전 accepted snapshot보다 정확히 목표 단계로
  단조 상승하고, 보이는 임계(EXP/level/progression sum)도 충족할 때만 가장 앞 kind3 행 하나를 retire합니다.
- 완료 키 `generation + row index + kind/aux/target stage`를 canonical JSON에 함께 원자 저장합니다.
  같은 snapshot 재전송, reconnect echo, 회귀값은 재완료되지 않으며 통화 지급은 0입니다.
- aux1..6의 exact branch 조건도 서버에 복제했습니다. aux1/2/3/4/6은 70 stats로 판정하고,
  aux5는 stats와 canonical furniture(쇼파 B/C 중 하나 + 침대 B/C 중 하나)를 함께 검사합니다.
- 클라이언트는 같은 stage의 후보 3개를 자동 선택하지 않고 첫 kind3 행 하나만 봅니다. 원본 서버의 route 선택은
  클라이언트에 없으므로 호환 기본값을 명시적으로 `AZROK_EVOLUTION_AUX_STAGE1=1`,
  `AZROK_EVOLUTION_AUX_STAGE2=4`로 두며 각각 1..3/4..6에서 설정할 수 있습니다(INFERRED compatibility policy).
  완료와 동시에 다음 generation 한 행만 발행하고 evo3에서는 발행하지 않습니다.

kind1은 **NOT SAFE**입니다. 일반 sys.tmp 행동도 같은 skill stat을 올릴 수 있고, 퀘스트 보너스는 max clamp와
봉에너지 gate로 관측되지 않을 수 있습니다. 따라서 C→S `0007` stat delta만으로 kind1 콘을 지급하지 않습니다.
kind0/2/5도 별도 server-visible action witness 전까지 fail-closed입니다.

## 3. Layer5 실제 두 클라이언트 채팅 (VERIFIED live)

- PID33132/entity2, PID75680/entity3을 각각 request-driven Plaza 전환했습니다.
- 실제 Plaza 입력 UI에서 `L5CHAT84A`를 송신했습니다.
- seq396: entity2 C→S `0068`, 27B
  `000000000000000000000000000000000a4c354348415438344100`
- seq397/398: entity2와 entity3 각각 S→C `006A`, 31B. 양쪽 화면의 채팅 로그 렌더까지 확인했습니다.
- 서버 Plaza room kind는 `0x1B`; `0x6E`는 클라이언트 scene/bootstrap selector입니다.

동적 실측에서 peer 화면 sender가 `Player`로 보이는 결함을 추가 발견했습니다. 슬롯 선택으로 복원된
`char_name_raw=Azrok1`을 per-client relay metadata에 동기화하도록 수정하고 회귀 테스트를 추가했습니다.

증거: `artifacts/dynamic-analysis/LAYER5_TWO_CLIENT_PUBLIC_CHAT_LIVE_20260718.md` 및 그 문서가 가리키는
packet JSON/BMP 3장.

## 4. 006C·0018 소셜 경계 (PARTIALLY SUPERSEDED by 90)

- C→S `006C` exact 4B self id, 길이/비-Plaza/self-id spoof는 검증합니다.
- **90 정정**: S→C `006C`의 state/toggle은 actor state에 실제 write되며 `0/0`도 안전 no-op으로
  증명되지 않았습니다. 원본 source가 live capture되기 전에는 S→C relay를 보내지 않습니다.
- C→S `0018` exact 3B `[slot,kind,localId]`는 검증하지만, S→C `0069`에 필요한
  `arg0/arg1/gate`가 wire에 없으므로 꾸며내지 않고 `pet_trick_deferred` 이벤트로 남깁니다.

## 5. OX 답안 제출 정정 (VERIFIED static / final-cell policy INFERRED)

OX 전용 버튼/답안 opcode는 없습니다.

- `CPopupOXQuestion` ctor `005F5BD0`, event `005F6180`은 버튼 큐 결과를 폐기하며 송신하지 않습니다.
- 일반 world click `00613C60 → 0061B510 → 005AB7B0 → 005AB6A0 → 00593D10`이
  C→S `0066` 22B를 보냅니다.
- `0066` layout:
  `[cell:u8][curX:i32][curY:i32][dstX:i32][dstY:i32][duration:i32][pathFlag:u8]`.
- `cell = ((y+9000)/3000) + ((x+9000)/3000)*6` (`FUN_006136C0`).
- C→S `0067` 15B는 `00619900 → 005AB830`의 arrival/current-position commit입니다.
- C→S `006A` len0은 generic actor field332==2 action branch이며 OX 답안 가설은 REFUTED입니다.

서버는 `0066`을 exact 22B로, `0067`을 exact 15B로 검증하고 current/destination/arrival cell과 각 timestamp를
actor metadata에 따로 유지하도록 수정했습니다. 따라서 OX 문제 마감 때
최종 grid cell로 O/X를 판정하는 구조가 정적 코드에 부합합니다. 원본이 목적지와 도착값 중 어느 timestamp를
판정 기준으로 쓰는지와 O/X side→cell mapping은 동적 A/B 전까지 INFERRED입니다.

동적 보강(88): 실제 Plaza `0066` 114건 모두 byte0가 `cell(curX,curY)`와 일치했고 목적지 셀과는
86건만 일치했습니다. 따라서 목적지 클릭을 즉시 답으로 확정하면 안 됩니다. OX 비활성 화면에서는
`00613C60` 프레임 경계까지만 반복되고 `0061B510/0066/0067`은 0회였으므로, 활성 phase gate와
O/X side→cell mapping만 남았습니다.

## 6. 검증 상태

- `python -m py_compile azrok_server.py tools/test_server_contract_layers.py`: PASS
- `test_server_contract_layers`: 45 PASS
- `test_content_builders`: 13 PASS
- `test_server_room_mapping`: 7 PASS
- 서버 계약 총 65 PASS, minimap 포함 전체 70 PASS

Related: 84, 86, 88, protocol/75, content/78, content/80, artifacts/dynamic-analysis/LAYER5_TWO_CLIENT_PUBLIC_CHAT_LIVE_20260718.md.
