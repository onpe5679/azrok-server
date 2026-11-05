# OX mode-2 서버 구현 (2026-07-18)

> **PARTIALLY SUPERSEDED by 96/97.** cell/current 기반 판정과 C→S C8-only 설명, CD→D2/D4 pair 및 C9 pending-exit 정책은 폐기되었습니다. 현행 구현은 CA side 판정, C9 즉시 cleanup→000D calibration, CD/D2/D4 상호배타 종료를 사용합니다.

관련 계약: 84, 88, 92. 이 문서는 `azrok_server.py`에 반영한 OX mode-2 구현과
검증 결과를 기록합니다. 원본 질문 데이터는 포함하지 않았고, 동적 클라이언트/x32dbg
조작은 이 구현 트랙에서 수행하지 않았습니다.

표기: **VERIFIED**=원본 바이너리 디컴파일 또는 자동 테스트로 직접 확인,
**INFERRED**=원본 서버가 사라져 서버 정책으로 격리한 부분,
**NOT VERIFIED**=실제 클라이언트 mode-2 end-to-end 확인이 남은 부분.

## 1. 추가 정적 확인

- **VERIFIED** `FUN_00606B90`은 C8 `result==0`일 때 `+6/+10`의 x/y를 self에
  적용하고, `+1` marker를 UI에 전달합니다. `+2` DWORD가 0이 아니면 추가 UI
  함수가 호출됩니다. 의미가 복구되지 않은 이 필드는 구현에서 `ready_value=0`으로
  고정했습니다.
- **VERIFIED** C8 실패 result는 즉시 `FUN_00602830` 종료 경로로 갑니다.
- **VERIFIED** CE type은 `FUN_005F6590`에서 1/2/3 전용 prefix, 그 외 default
  prefix를 선택합니다. 구현은 보수적으로 `0..3`만 허용합니다.
- **VERIFIED** CE stars 소비처 `FUN_005F62A0`은 `param_2`만큼 포인터 배열을
  걷고, 초기화 함수 `FUN_005F6300`은 정확히 3개만 초기화합니다. 따라서 `0..3`
  밖은 out-of-bounds 위험으로 전송 거부합니다.

## 2. exact codec / validator

`azrok_server.py`에 다음 pure contract를 추가했습니다.

| 방향/opcode | 계약 | 구현 상태 |
|---|---:|---|
| C→S C8 | exact 0B | `decode_c2s_ox_enter_00c8` |
| S→C C8 | exact 14B `<BBIii` | `build_s2c_ox_enter_00c8` |
| S→C C9 | non-empty N×32B | `build_s2c_ox_remote_00c9` |
| S→C CA/CB/CD | u32 actor-id array(CA는 정확히 1개) | `build_s2c_ox_actor_ids` |
| S→C CC/D2/D4 | exact 0B | `validate_s2c_ox_payload` |
| S→C CE | exact 131B | `build_s2c_ox_question_00ce` |
| S→C D0 | exact 24B | 기존 0068형 builder + mode-2 validator |
| S→C D3 | exact 4B `<HH` | `ox_counter` |

`_packet_semantics`에도 방향별 C8 및 S→C C8..D4 의미/길이 decode를 등록했습니다.
따라서 실제 C8은 더 이상 dashboard의 unknown C2S로 분류되지 않습니다.

## 3. deterministic 라운드 state

자동 timer thread는 사용하지 않습니다. 각 OX room은 lock 아래 다음 상태를
가집니다.

```text
idle/finished -> ready -> question -> closed -> ready(next round)
                                  \-> finished -> ready(new match)
```

- **VERIFIED(테스트)** C8 exact0은 Plaza actor를 기존 state-1 peer에서 0067로 먼저
  제거하고 내부 `LOCAL_OX_ROOM_KIND=-2`에 가입시킵니다.
- **VERIFIED(테스트)** C8 admission만 전송하며 CC와 CE는 별도 control trigger입니다.
  같은 TCP burst의 안전성을 추정하지 않았습니다.
- **VERIFIED(테스트)** 이미 가입한 소켓의 중복 C8은 idempotent no-op이며 C8/C9를
  재전송하거나 round state를 변경하지 않습니다.
- **VERIFIED(테스트)** C9/CA/CB/CD/D0 actor id는 수신자별로 변환합니다. 수신자의
  self는 1, 다른 actor는 server entity id입니다.
- **VERIFIED(테스트)** OX의 0066은 current 좌표만 답으로 기록하고 destination은
  선확정하지 않습니다. 0067은 검증된 arrival을 최신 위치로 승격합니다.
- **VERIFIED(테스트)** OX 이동은 peer에 D0로만 나갑니다. state-1 S→C 0068은 mode-2
  room에 전송하지 않습니다.
- **INFERRED policy** 이벤트는 `received_at < deadline`인 경우만 채택합니다.
  equality는 원본 규칙이 없으므로 fail-closed late입니다. 같은 generation의 마지막
  유효 event만 receive sequence 순으로 남깁니다.
- **INFERRED policy** CE open 때 side cell set을 round에 snapshot합니다. 실행 중
  `/configure`가 바뀌어도 현재 판정은 바뀌지 않고 다음 generation부터 적용됩니다.
- **VERIFIED(테스트)** CB는 수신자별 패자 목록입니다. 무응답, generation mismatch,
  side table 밖 cell은 loser입니다.
- **VERIFIED(테스트)** `closed -> ready`는 생존자를 유지합니다. `finished/idle -> ready`
  새 match는 현재 participants 전체를 survivors로 복원하고 generation/answers/losers/
  현재 질문을 초기화합니다. history는 감사 기록으로 보존합니다.

## 4. 입퇴장 lifecycle

- Plaza→OX C8: 기존 Plaza peer에 state-1 0067 targeted remove 후 OX C8/C9.
- OX disconnect 또는 C2S0065 room change: 남은 OX peer에 mode-2 CA 후 participant 제거.
- D2 뒤 자연 C2S0064: mode-2 CA/participant 제거, OX metadata 제거,
  `roster_bootstrapped=False`, visible state1 actor set 초기화 후 Plaza 0064 경계를 처리합니다.
- D4: 송신 즉시 서버가 방을 임의 변경하지 않습니다. 클라이언트 next-tick 종료 뒤 오는
  0064/0065 또는 disconnect가 위 동일 lifecycle 정리를 수행합니다. **NOT VERIFIED**
  실제 클라이언트가 D4 뒤 어느 C2S 순서를 보내는지는 동적 end-to-end가 필요합니다.

## 5. 질문과 설정

기본 질문은 프로젝트가 새로 작성한 짧은 두 문장뿐입니다.

```json
[
  {"text":"1 + 1 = 2","type":0,"correct_side":0,"stars":1},
  {"text":"3 is an even number","type":0,"correct_side":1,"stars":1}
]
```

원본 게임 질문은 포함하지 않습니다. `/api/ox/configure` 또는 CLI
`--questions-json`으로 동일 스키마의 보존용 질문 bank를 교체할 수 있으며, 모든 질문은
CE builder를 통과해야 commit됩니다.

side 기본은 92의 WMB 산술 후보인 code0 `{20,21}`, code1 `{14,15}`입니다.
이는 **INFERRED policy**이며 configure API/CLI로 바꿀 수 있습니다.

## 6. control API / CLI

명시적 HTTP endpoint:

```text
GET  /api/ox/status
POST /api/ox/prepare
POST /api/ox/question   {question_index, duration_ms}
POST /api/ox/tick
POST /api/ox/finish     {exit_mode: "cd"|"d2"|"d4"}
POST /api/ox/counter    {first, second}
POST /api/ox/configure  {side0_cells, side1_cells, questions}
```

호환 action endpoint `POST /api/ox {action,...}`와 CLI도 제공합니다.

```powershell
python azrok_ctl.py ox prepare
python azrok_ctl.py ox open --question-index 0 --duration-ms 16000
python azrok_ctl.py ox tick
python azrok_ctl.py ox finish --exit-mode cd
python azrok_ctl.py ox configure --side0-cells 14,15 --side1-cells 20,21
```

96 이후 side cell 설정은 진단용 geometry이며 실제 판정은 C→S CA의 side를 사용합니다.

## 7. 자동 검증

실행:

```text
python -m py_compile azrok_server.py azrok_control.py azrok_ctl.py tools/test_server_contract_layers.py
python -m unittest tools.test_server_contract_layers -q
```

최신 결과는 96을 따릅니다: OX **16 tests OK**, 전체 **86 tests OK**.

OX 전용 검증에는 exact length/range, C8/CC/CE 분리, 중복 C8, C9 ID,
current-vs-destination, arrival, strict deadline, generation isolation, mode-2 D0,
recipient별 CB self id, CD/D2/D4 상호배타 frame, C9→000D, disconnect CA, Plaza ghost 제거,
D2→0064 cleanup, new-match reset, side snapshot, custom question config와 실제 localhost
HTTP endpoint 왕복이 포함됩니다. 기존 login/state/inventory/shop/chat/social 테스트도 함께
통과하여 state-1 회귀가 없음을 확인했습니다.

## 8. 남은 동적 확인

- **NOT VERIFIED** 실제 클라이언트 C8→C9→CC→CE 표시 및 좌우 이동 후 CB 연출.
- **NOT VERIFIED** C8 marker=0, ready_value=0, spawn `(0,0)`의 실제 UI/충돌 결과.
  `ready_value=0`은 미확정 추가 UI branch를 피하는 정적 안전 기본이고 spawn은
  `AZROK_OX_SPAWN_X/Y`로 설정 가능하지만 live proof는 아직 없습니다.
- **NOT VERIFIED** C9 descriptor/appearance의 현재 보존 기본(`char_type,0,0,0`)과 원본
  서버 값의 일치. exact field 위치는 VERIFIED이나 semantic 값은 실측이 필요합니다.
- **VERIFIED (96/97)** 정상 final은 CD, forced abort는 D2 또는 D4 standalone이며
  모두 C9로 수렴합니다. C9 후속은 000D→kind01 calibration→0064입니다.
