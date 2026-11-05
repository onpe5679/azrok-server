# OX mode-2 최종 동시성·수명주기 검토 (2026-07-18)

> **PARTIALLY SUPERSEDED by 97.** D2/D4 finish pair 가정과 C9 pending-exit lifecycle은 폐기되었습니다. control 직렬화와 spectator/stale-round hardening은 계속 유효합니다.

관련 계약: 92, 93. 이 문서는 `azrok_server.py`, `azrok_control.py`,
`azrok_ctl.py`, `tools/test_server_contract_layers.py`를 독립 재검토하고 발견한
서버 구현 결함과 자동 검증 결과를 기록합니다. 이 검토에서는 실제 게임 클라이언트를
조작하지 않았습니다.

> **RUNTIME NOTE:** 아래 수정은 디스크 코드와 자동 테스트 기준으로 VERIFIED입니다.
> 문서 작성 시점의 실행 중 서버 프로세스는 수정 전 코드일 수 있으므로 실제 OX E2E 전에
> 서버를 clean restart해야 합니다.

표기: **VERIFIED**=코드와 자동 테스트로 직접 확인, **INFERRED**=보존 서버 정책,
**NOT VERIFIED**=실제 mode-2 클라이언트 동적 확인이 남은 부분.

## 1. wire 계약 재검토

- **VERIFIED** C2S C8은 exact 0B, S2C C8은 exact 14B `<BBIii>`입니다.
- **VERIFIED** C9는 actor마다 exact 32B이며 actor id, appearance, CP949 이름,
  x/y의 필드 위치를 바이트 단위 테스트로 고정했습니다.
- **VERIFIED** D0는 state-1 0068과 같은 exact 24B 이동 레코드를 재사용하되 OX
  peer에게만 송신합니다.
- **VERIFIED** C9/CA/CB/CD/D0의 actor id는 수신자별로 변환합니다. 수신자 자신은
  wire id 1, 타인은 서버 entity id입니다. CB뿐 아니라 CD도 직접 테스트했습니다.
- **VERIFIED** 이미 입장한 연결의 중복 C8은 payload를 먼저 exact 검증한 뒤
  idempotent no-op으로 처리합니다.

## 2. 발견하고 수정한 수명주기 결함

- **VERIFIED** 질문이 열린 뒤 C8로 들어온 참가자가 현재 CE를 받지 않았는데도
  survivor에 들어가 자동 탈락하던 결함을 수정했습니다. 중도 입장자는 현재 match의
  spectator이고 다음 fresh match부터 survivor입니다.
- **VERIFIED** OX에서 직접 C2S0065로 나갈 때 participant만 제거되고
  `ox_room_id`, `ox_round_generation`, state-1 visibility metadata가 남던 결함을
  수정했습니다. Plaza/OX ghost 재발 방지 테스트를 추가했습니다.
- **VERIFIED** 마지막 참가자가 질문 중 disconnect하면 phase/deadline/question이
  남아 다음 입장자가 spectator로 고착되던 결함을 수정했습니다. 마지막 이탈 시
  room은 idle로 돌아가며 다음 입장자는 prepare/open이 가능합니다.
- **VERIFIED** D2/D4 finish에서 per-client round generation과 room의
  answers/correct-cells/deadline이 남던 결함을 정리했습니다. fresh prepare는
  `finish_exit_mode`도 초기화합니다.
- **VERIFIED** closed->ready는 생존자에게만 CC를 보내며, finished/idle->ready는
  현재 참가자로 fresh match를 구성합니다.

## 3. 동시성 및 control API

- **VERIFIED** OX control transition 전체를 별도 re-entrant operation lock으로
  직렬화했습니다. concurrent prepare/open에서도 CC emit이 끝나기 전에 CE가 앞서지
  않습니다.
- **VERIFIED** lock 순서는 operation lock이 바깥이고 내부에서 control/room lock을
  취합니다. participant 제거의 재진입 경로는 `RLock`이며 테스트에서 deadlock 없이
  완료됐습니다.
- **VERIFIED** 질문 index 음수, CP949로 표현할 수 없는 질문, 비문자열 질문,
  겹치는 side cell, side list가 아닌 입력을 fail-closed로 거절합니다.
- **VERIFIED** HTTP JSON root가 object가 아니거나 Content-Length가 부정확·음수·1MiB
  초과인 경우 400으로 거절합니다. `room_id`도 비문자열·빈 문자열·제어문자·64자 초과를
  거절합니다.
- **VERIFIED** CE question builder는 strict CP949, 최대 127B, NUL-safe 계약을 유지합니다.
  서버 API가 임의 객체를 `str()`로 정규화해 우회시키지 않습니다.

## 4. 자동 검증

실행:

```text
python -m py_compile azrok_server.py azrok_control.py azrok_ctl.py tools/test_server_contract_layers.py
python -m unittest tools.test_server_contract_layers.OxMode2ContractTests -v
python -m unittest discover -s tools -p "test_*.py"
```

결과:

- **VERIFIED** py_compile PASS.
- **VERIFIED** OX mode-2 표적 **15 tests OK**.
- **VERIFIED** 전체 서버 계약 **85 tests OK**.
- **VERIFIED** state-0 로그인/bootstrap 및 state-1 저장·인벤토리·상점·채팅 회귀도
  같은 전체 suite에서 통과했습니다.

## 5. 남은 동적 확인

- **NOT VERIFIED** 실제 클라이언트에서 C8/C9/CC/CE 표시, O/X 이동, CB 탈락,
  CD 결과, D2/D4 종료까지의 end-to-end 흐름.
- **NOT VERIFIED** D4 수신 뒤 실제 클라이언트가 보내는 다음 C2S opcode 순서.
- **NOT VERIFIED** C8 marker/ready-value/spawn 기본값과 C9 appearance 의미값이 원본
  서버와 완전히 같은지 여부. exact wire 위치와 길이는 VERIFIED입니다.
- **INFERRED policy** strict `<deadline`, side-cell 표, 동률/무응답 처리와 종료 모드는
  원본 판정 증거가 나오기 전까지 설정 가능한 서버 정책으로 유지합니다.
