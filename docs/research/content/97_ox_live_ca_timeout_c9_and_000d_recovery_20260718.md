# OX live CA timeout·C9 자연 종료·000D 복귀 A/B (2026-07-18)

관련 문서: 92, 93, 94, 95, 96. 최신 `profile_playable_v2` 서버와 실제 클라이언트 한 개로 OX mode-2 입장, CA 제출, CB/C9 자연 종료, Plaza 복귀 handshake를 검증했습니다. 원본 서비스나 외부 서버에는 접속하지 않았습니다.

표기: **VERIFIED**=실제 패킷·API·메모리·화면 직접 관찰, **INFERRED**=확정된 현상에 대한 최소 구현 판단, **NOT VERIFIED**=후속 clean runtime 실측 필요.

> **SUPERSEDES 96 finish policy:** C9 sender에게 서버가 `CD→D2/D4` pair를 보내야 한다는 96의 pending-exit finish 정책은 원본 디컴파일 재검토와 본 live A/B에 의해 폐기합니다. self loser의 클라이언트는 CB 뒤 자체 teardown으로 C9를 보내고 mode0/Plaza scene을 enqueue하며, 서버에 필요한 후속은 기존 Plaza calibration을 시작하는 S→C `000D[00]`입니다.

## 1. 저장 상태와 Plaza 기준선

- **VERIFIED** PID `104624`, entity 2 `Azrok1`, capture `captures/packets_20260718_105345.txt`였습니다.
- **VERIFIED** canonical state는 `server_state/profile_playable_v2/a706c61796572_s0_c417a726f6b31_state_v1.json`, SHA-256 `D190456272D19D182FB9AA69F405373C31C13393F24A706FF190E71B35B0E31F`, 3279B였습니다.
- **VERIFIED** 시작 상태는 `room_kind=27`, scene 110, phase 4, mode 1, self actor 1, heartbeat 정상, engine error 없음이었습니다.

## 2. targeted 006E와 OX C8 입장

| seq | 시각 | 방향/opcode | payload |
|---:|---|---|---|
| 79 | 10:57:58.818 | S→C `006E` | `0000` |
| 80 | 10:57:59.138 | C→S `00C8` | exact 0B |
| 81 | 10:57:59.138 | S→C `00C8` | exact 14B all-zero |

- **VERIFIED** targeted `006E[0000]`은 한 번만 보냈습니다.
- **VERIFIED** 320ms 뒤 자연 C8 요청과 서버 C8 응답이 연속으로 발생했고 `scene=111`, phase 5, mode 2, self 1, heartbeat 정상, engine error 없음이 됐습니다.
- **VERIFIED** OX 화면에서 왼쪽 초록 O와 오른쪽 보라 X를 다시 캡처했습니다. 최신 서버 side table은 `side0={14,15}`, `side1={20,21}`로 96과 일치했습니다.

## 3. 좌측 클릭 시도는 active-click 증거가 아님

S→C CC seq 88 뒤 CE seq 89가 `10:58:26.721`에 도착했고, 질문은 `1 + 1 = 2`, correct side 0이었습니다. 좌측 O 중심을 화면 `(273,665)`, client ratio `(0.2606,0.828)`로 식별해 클릭은 한 번만 실행했습니다.

- **VERIFIED** C→S CA seq 94는 CE 후 15.005초에 발생했습니다.
- raw: `01000000000000000000000000000000002e7bf27201`
- decode: side 1, current/destination `(0,0)`, timing `1928493870`, `timeoutFlag=1`입니다.
- **VERIFIED** CE 이후 C→S 0066/0067은 한 건도 없었고, 서버 answer도 `side=1, timeout=true`였습니다.
- **VERIFIED** 클릭 실행이 클라이언트의 고정 15초 timeout과 겹쳐 active movement보다 timeout CA가 먼저 확정됐습니다.
- **NOT VERIFIED (첫 표본, §9에서 해소)** 따라서 이 첫 표본 자체는 좌측 O의 active-click `side0/pathFlag0` 증거가 아닙니다. 자동 lifecycle 반영 뒤의 성공 표본은 §9에 기록합니다.
- **INFERRED 운영 규칙** control API의 120초 deadline은 서버 tick만 늦출 뿐 클라이언트의 약 15초 CA 제출 시한을 연장하지 않습니다.

## 4. CB 뒤 C9는 자연 발생하지만 Plaza handshake가 자동 시작되지 않음

- **VERIFIED** 서버 tick은 timeout side1을 오답으로 판정해 S→C CB seq 119 payload `01000000`를 보냈습니다.
- **VERIFIED** CB 6.514초 뒤 클라이언트는 자연 C→S C9 seq 122 payload `00`을 보냈습니다.
- **VERIFIED** 서버에서 종료 프레임 `CD/D2/D4`는 하나도 보내지 않았습니다.
- **VERIFIED** C9 직후 클라이언트는 mode 0, scene 110, phase 5가 됐고 `C→S 0016[01]` 한 건을 보냈지만, 추가 calibration이 이어지지 않았습니다.
- **VERIFIED** 이후 60초 이상 C→S 0064/0065가 없었고 서버 room은 여전히 OX, `pending_exits=[2]`였습니다. heartbeat와 engine 상태만 정상인 stuck입니다.

## 5. S→C 000D[00] 단일 주입으로 Plaza 복귀 완주

stuck 상태에서 entity 2에 S→C `000D[00]`을 한 번만 보냈습니다.

| 단계 | seq | 결과 |
|---|---|---|
| S→C `000D[00]` | 149 | Plaza calibration arm |
| C→S `0016[01]` | 150,153,156,159,162 | 정확히 5회 |
| S→C `0004[01 + tick]` | 152,155,158,161,164 | 정확히 5회 |
| C→S `0064[00]` | 165 | 자연 Plaza 완료 보고 |
| S→C `0064` | 166 | 27B self/Plaza 응답 |

- **VERIFIED** 전체 handshake는 423ms 안에 완료됐습니다.
- **VERIFIED** 최종 상태는 `room_kind=27`, `room_name=plaza (0064-only)`, `ox_room_id=null`, scene 110, phase 4, mode 1, self 1, heartbeat 정상, engine error 없음, pending exits empty입니다.
- **VERIFIED** 실제 화면도 Plaza의 `OX지존` 표지판 앞 캐릭터로 복귀했습니다.
- **INFERRED 서버 수정** 유효 C9를 받은 서버는 sender에게 CD/D2/D4를 보내지 말고, mode0/scene enqueue가 반영될 짧은 경계 뒤 기존 S→C `000D[00]` calibration 경로를 정확히 한 번 시작해야 합니다. 중복 C9/중복 000D와 disconnected socket은 fail-closed여야 합니다.

## 6. 후속 검증

1. 자동 C9→000D 코드 반영 후 clean restart에서 같은 loser 경로가 수동 주입 없이 Plaza healthy까지 완주하는지 확인합니다.
2. 그 runtime에서 CE 직후 2~3초 안에 좌측 O를 클릭해 CA `side0, timeoutFlag0` 및 좌표 필드를 확보합니다.
3. correct side0 tick에서 CB exact 0B/self 비패배를 확인합니다.
4. 별도 generation에서 오른쪽 X active click CA `side1, timeoutFlag0` → CB self → C9 → 자동 000D 복귀 A/B를 확인합니다.
5. D4는 원본 호출 조건이 추가로 확정되기 전에는 보내지 않습니다.

## 7. 증거

- `artifacts/dynamic-analysis/ox2_ca_c9_000d_recovery_evidence_20260718.json`
- `artifacts/dynamic-analysis/ox2_admitted_before_question_20260718.bmp`
- `artifacts/dynamic-analysis/ox2_question0_before_left_click_20260718.bmp`
- `artifacts/dynamic-analysis/ox2_question0_timeout_after_click_20260718.bmp`
- `artifacts/dynamic-analysis/ox2_after_natural_c9_stuck_20260718.bmp`
- `artifacts/dynamic-analysis/ox2_recovered_via_000d_plaza_20260718.bmp`
- wire 원문: `captures/packets_20260718_105345.txt`

## 8. 원본 정적 재검토와 서버 반영

Ghidra MCP에서 원본 `Azrok_analyzed.exe`의 종료 함수들을 다시 디컴파일했습니다.

- **VERIFIED** `FUN_006071B0`: CB self loser를 result state2로 만들고 timer를 시작합니다.
- **VERIFIED** `FUN_00607530`: CD final을 result state3으로 만들고 같은 timer를 시작합니다.
- **VERIFIED** `FUN_005FF5B0`: 6499ms 뒤 state2와 state3 모두
  `FUN_00602830`을 호출합니다.
- **VERIFIED** D2 handler는 `FUN_00602830`을 직접 호출합니다.
- **VERIFIED** `FUN_006076F0`은 D4 flag `+0x9D`를 세우고,
  매 tick의 `FUN_00603620`이 이를 보고 `FUN_00602830`을 호출합니다.
- **VERIFIED** `FUN_00602830`은 `FUN_006028E0` teardown/C9 송신 뒤 Hansol flag,
  mode0, calibration reset, local room `0x6E` enqueue를 수행합니다.

따라서 정상 final `CD`, forced abort `D2`, deferred abort `D4`는 상호배타적인 종료
원인입니다. 어떤 경우도 `CD→D2` 또는 `CD→D4` pair로 보내면 안 됩니다.

`azrok_server.py`, `azrok_control.py`, `azrok_ctl.py`에는 다음을 반영했습니다.

- C9 즉시 OX membership 제거 및 peer CA actor-remove
- sender를 `Plaza transition pending`으로 전환
- sender proto에 Hansol kind01 calibration/count0 arm
- sender에게 S→C `000D[00]` exact 1회 전송
- `ox_finish` 기본 `cd`; CD only / D2 only / D4 only
- API 기본 `cd`, CLI choices `cd/d2/d4` 및 기본 `cd`

자동 검증은 C9 source의 exact `000D[00]`, membership 즉시 제거, calibration count
reset, 다음 C→S `0016[01]`에 대한 S→C `0004[01]`, 중복 C9 idempotence와
CD/D2/D4 상호배타를 고정합니다. OX **16 tests OK**, 전체 **86 tests OK**입니다.

## 9. 후속 clean runtime: active side0와 CD-only 자동 복귀 완주

자동 C9→000D가 반영된 clean PID `65612`, capture
`captures/packets_20260718_110829.txt`에서 미해결 항목을 최종 검증했습니다.
시작 전 canonical state는 SHA-256
`D190456272D19D182FB9AA69F405373C31C13393F24A706FF190E71B35B0E31F`, 3279B였고,
slot0 `Azrok1/species2/level26/evolution1`, currency 950이었습니다.

### 9.1 active side0 CA와 0067 arrival (VERIFIED)

- targeted S→C `006E[0000]` seq 57을 한 번만 보냈고 C→S C8 seq 58,
  S→C C8 seq 59 뒤 OX mode2가 정상 렌더됐습니다.
- 좌측 O 중심은 screen `(273,665)`, ratio `(0.2606,0.828)`였습니다.
- CE seq 71 `11:11:37.799` 직후 같은 제어 흐름에서 좌측 O를 한 번 클릭했습니다.
- CE **2.426초** 뒤 C→S CA seq 72 exact22가 발생했습니다.

```text
raw         000000000000000000cafeffff98fdffff800d000000
side        0
current     (0,0)
destination (-310,-616)
timing      3456
timeoutFlag 0
```

- **VERIFIED** 이는 active-click `side0/timeoutFlag0`의 첫 live 증거입니다.
- **VERIFIED** active CA 이전 C→S 0066은 없었습니다. 이동 완료 때 C→S 0067 seq 73이
  `cell14,(-310,-616)`를 보고했습니다. CA가 답안 권위이고 0067은 arrival telemetry라는
  구분이 실제 wire 순서로 확정됐습니다.
- **VERIFIED** 화면에서 캐릭터가 실제 좌측 O 안에 도착했습니다.
- **VERIFIED** CE 15.052초 뒤 추가 timeout CA seq 76도 왔습니다. side0,
  current=destination `(-310,-616)`, timeoutFlag1이었습니다. active CA 뒤에도 local countdown
  종료 시 두 번째 CA가 올 수 있으며 서버는 같은 generation의 마지막 유효 side를 보존했습니다.

### 9.2 CB empty와 self 생존 (VERIFIED)

- tick은 `losers=[]`, `survivors=[2]`로 마감했습니다.
- S→C CB seq 81은 **exact 0B**였고 self는 패배하지 않았습니다.
- 최종 answer side0과 arrival cell14 `(-310,-616)`가 API와 wire에서 일치했습니다.

### 9.3 CD 단독 finish와 자동 Plaza 복귀 (VERIFIED)

`/api/ox/finish {exit_mode:"cd"}`는 S→C CD seq 86 payload `01000000`만 보냈습니다.
이는 survivor self wire actor id 1입니다. **S→C D2/D4는 0건**입니다.

| 단계 | 시각/seq | 실측 |
|---|---|---|
| S→C CD | 11:12:31.014 / 86 | survivor `[1]` |
| 자연 C→S C9 | 11:12:37.522 / 89 | CD +6.508초, payload `00` |
| 자동 S→C 000D | 11:12:37.522 / 90 | C9와 같은 시각, payload `00` |
| C→S 0016[01] | 91,94,97,100,103,106 | 요청 6회 |
| S→C 0004[01] | 93,96,99,102,105 | calibration sample 5회 |
| C→S/S→C 0064 | 108/109 | C9 +523ms, Plaza 완료 |

- **VERIFIED** kind1 요청은 6회였고 서버 calibration sample은 5회였습니다. 다섯 번째 sample
  뒤 여섯 번째 요청에서 클라이언트가 C→S 0064를 commit했습니다.
- **VERIFIED** 최종 상태는 room27, scene110, phase4, mode1, self1, heartbeat 정상,
  engine error 없음, unknown C2S 0, OX idle/participants empty입니다.
- **VERIFIED** 최종 화면도 Plaza `OX지존` 표지판 앞 캐릭터를 표시했습니다.
- **VERIFIED** state SHA-256/길이, slot0 identity, currency950은 시작 전후 불변입니다.

### 9.4 최종 계약

1. 답안 권위는 C→S CA exact22의 side입니다. active click은 flag0, local countdown은 flag1입니다.
2. active CA 뒤 같은 generation의 timeout CA가 추가될 수 있으므로 둘 다 exact validation하고
   deadline 안 마지막 유효 side를 사용합니다.
3. C→S 0067은 arrival telemetry이며 CA 답안을 대체하지 않습니다.
4. 승자 finish는 S→C CD 단독입니다. D2/D4를 붙이지 않습니다.
5. 자연 C9를 받으면 S→C 000D를 한 번 보내 기존 Plaza calibration을 시작합니다.
6. 성공 판정은 OX cleanup과 Plaza `scene110/phase4/mode1/self1/heartbeat`까지 포함합니다.

추가 증거:

- `artifacts/dynamic-analysis/ox3_active_side0_cd_auto_recovery_evidence_20260718.json`
- `artifacts/dynamic-analysis/ox3_admitted_pre_question_20260718.bmp`
- `artifacts/dynamic-analysis/ox3_active_side0_after_ca_20260718.bmp`
- `artifacts/dynamic-analysis/ox3_cd_auto_recovered_plaza_20260718.bmp`
- wire 원문: `captures/packets_20260718_110829.txt`
