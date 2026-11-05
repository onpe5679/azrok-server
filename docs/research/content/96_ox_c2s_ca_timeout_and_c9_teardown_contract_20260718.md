# OX C→S CA 타임아웃 제출 및 C9 종료 계약 (2026-07-18)

> **SUPERSEDED by 97 for finish lifecycle.** CA/C9 wire 계약과 side/timeout 정적 결론은 유효하지만, C9 sender에게 서버가 `CD→D2/D4`를 보내야 한다는 pending-exit finish 정책은 폐기됐습니다. 실제 복귀에 필요한 후속은 기존 S→C `000D[00]` calibration 시작입니다.

관련 문서: 92, 93, 94, 95. 이 문서는 94의 동적 실측을 원본 바이너리의 송신
생성자까지 역추적해, 92의 `0066/0067` 답안 가설과 side 방향을 정정하고 서버에
반영한 기록입니다.

표기: **VERIFIED**=디컴파일 본문 또는 패킷 실측으로 직접 확인,
**INFERRED**=확정된 클라이언트 계약 위에 둔 서버 정책,
**NOT VERIFIED**=추가 동적 확인이 필요한 부분입니다.

## 1. 결론

- **VERIFIED** OX 전용 C→S는 최소 `C8`, `C9`, `CA`입니다.
- **VERIFIED** 답안 권위 값은 C→S `CA` 22B의 첫 바이트 `side`입니다.
  일반 C→S `0066/0067`의 cell은 이동 텔레메트리일 뿐 OX 답안이 아닙니다.
- **VERIFIED** `side=0`은 음의 X/왼쪽, `side=1`은 양의 X/오른쪽입니다.
- **VERIFIED** CE 이후 입력이 없으면 클라이언트가 약 15초 뒤 `CA`를 스스로
  제출합니다. 구역 밖이면 CE 정답과 반대 side를 넣어 의도적으로 오답 처리합니다.
- **VERIFIED** C→S `C9` exact 1B는 OX 로컬 teardown/leave 통지입니다.
  CB로 탈락한 self도 약 6.5초 뒤 이를 보냅니다.
- **VERIFIED by 97** C9는 클라이언트가 이미 자연 exit를 시작한 통지입니다.
  서버는 membership을 즉시 정리하고 S→C `000D[00]`로 기존 Plaza calibration을
  시작해야 합니다. C9 뒤 CD/D2/D4를 추가로 보내면 안 됩니다.

## 2. C→S exact wire 계약

| opcode | payload | 생성자/호출 근거 | 의미 |
|---|---:|---|---|
| `0x00C8` | exact 0B | `FUN_005FF1E0` | OX scene 준비/입장 요청 |
| `0x00C9` | exact 1B | `FUN_005ABE50` | teardown/leave; byte0은 `CGameOXQuiz+0x84` marker |
| `0x00CA` | exact 22B | `FUN_005ABDC0` | side 선택 및 OX 이동/타임아웃 제출 |

`CA`의 정확한 레이아웃은 다음과 같습니다.

```text
[side:u8]
[currentX:i32][currentY:i32]
[destinationX:i32][destinationY:i32]
[timing:i32]
[timeoutFlag:u8]
```

- **VERIFIED** `timeoutFlag=0`: active click 경로. `timing`은 이동 시간입니다.
- **VERIFIED** `timeoutFlag=1`: 타임아웃 경로. current와 destination이 같고,
  `timing`에는 동기화된 절대 tick이 들어갑니다.
- **VERIFIED** OX 클래스 범위에 CB/CC/CD/CE를 C→S로 보내는 별도 wrapper는 없습니다.
- **VERIFIED** C→S `0066` wrapper의 직접 xref는 `0061B510`, `0061BCF0`,
  `0061A420`이며 OX 클래스의 답안 송신자가 아닙니다. C→S `0067`은 공유 arrival
  송신 경로가 있으나 OX 답안 권위 값은 아닙니다.

## 3. active click와 15초 무입력 경로

### active click

`FUN_006018A0`은 `FUN_005ABDC0`을 호출해 다음을 전송합니다.

- `side = CGameOXQuiz+0x73`
- current/destination 좌표
- 계산된 movement duration
- `timeoutFlag=0`

그 뒤 동일 actor state를 로컬에도 적용합니다. 즉 서버 판정은 도착 cell을 재구성할
필요 없이 CA 첫 바이트를 사용해야 합니다.

### 무입력 타임아웃

CE handler `FUN_006069A0`은 `FUN_005F8E30(1, 4000, 10)`을 호출합니다.
`FUN_005F8ED0`은 최초 4초를 기다린 뒤 10부터 0까지 1초마다 감소시키고, 0에서
`FUN_00602D10`을 호출합니다. 결과적으로 wire 제출은 CE 수신 약 15초 뒤입니다.

`FUN_00602D10`의 구역 판정:

| side | 중심 | 반경 | 의미 |
|---:|---:|---:|---|
| `0` | `(-357,-419)` | `310` | 음의 X/왼쪽 |
| `1` | `(+344,-419)` | `310` | 양의 X/오른쪽 |

두 원 밖이면 CE의 정답 side(`this+0x7C`)와 반대 값을 제출합니다. 따라서 92에서
결과 effect 좌표만으로 유추한 `0=오른쪽, 1=왼쪽`은 반대로 해석된 것입니다.

## 4. 동적 패킷과 정적 경로 수렴

- **VERIFIED (94 실측)** CE seq262가 `10:34:30.260`에 도착하고 입력이 없을 때,
  `+15.028s`에 C→S `CA` 22B가 발생했습니다.
- raw payload:
  `0100000000000000000000000000000000f78fdc7201`
- decode: `side=1`, current/destination `(0,0)`, `timing=0x72DC8FF7`,
  `timeoutFlag=1`입니다. `(0,0)`은 두 구역 밖이고 당시 CE 정답은 side0이므로
  정적 timeout-opposite 경로와 정확히 일치합니다.
- **VERIFIED (94 실측)** self loser CB 뒤 `+6.503s`에 C→S `C9` exact 1B `00`이
  발생했습니다.

## 5. C9, CB, D2/D4 lifecycle

- **VERIFIED** C8 handler는 `this+0x84=0`으로 초기화합니다.
- **VERIFIED** `FUN_006028E0`은 `FUN_005ABE50(this+0x84)`로 C9를 보낸 뒤 OX
  actor/state를 정리합니다.
- **VERIFIED** CB loser result state2 뒤 `FUN_005FF5B0`이 `0x1963`ms(6499ms)를
  기다리고 `FUN_00602830 → FUN_006028E0`으로 들어갑니다. 실측 6.503초와 일치합니다.
- **VERIFIED** S→C D2 handler도 `FUN_00602830`을 호출합니다. 이 경로는 teardown,
  mode0 설정, `GameManager_EnqueueRoomCode(0x6E)` 순서입니다.
- **VERIFIED** enqueue 함수 `0050A7F0`은 pending room code를 로컬 큐에 넣습니다.
  클라이언트 내부에서 C9 송신 뒤 특정 OX 응답을 기다리는 분기는 없습니다.
- **VERIFIED** D4 handler `FUN_006076F0`은 다음 tick의 종료 경로를 켜는 flag를
  설정합니다.
- **VERIFIED** `FUN_00607530`은 CD 수신 시 result state3과 6499ms timer를 설정하고,
  `FUN_005FF5B0`은 state2(CB loser)와 state3(CD final) 모두
  `FUN_00602830`으로 보냅니다.
- **VERIFIED** D4의 `+0x9D` flag는 매 tick의 `FUN_00603620`에서
  `FUN_00602830`을 호출합니다. 따라서 `CD`, `D2`, `D4`는 상호배타적인 종료
  원인이며 pair가 아닙니다.
- **VERIFIED by 97 live** C9 직후 C→S `0016[01]`가 발생하고, S→C `000D[00]`
  한 프레임이 `0004[01]` 5회→0064 왕복→Plaza healthy를 완주합니다.

## 6. 서버 반영

`azrok_server.py`에 다음을 반영했습니다.

- exact C2S C9/CA decoder 및 packet semantics
- CA side 기반 generation/deadline fail-closed 판정
- 0066/0067은 위치 telemetry와 D0 relay만 수행
- 기본 side geometry를 `0={14,15}`, `1={20,21}`로 정정하되 판정에는 사용하지 않음
- 자연 timeout CA를 받도록 기본 question window를 16000ms로 조정
- C9 수신 시 OX membership 즉시 제거 및 peer S→C CA actor-remove
- sender metadata를 `Plaza transition pending`으로 바꾸고 Hansol kind01 calibration arm
- sender에게 S→C `000D[00]` exact 1회 전송
- `ox_finish`: 기본 `cd`; CD actor-id payload만 전송. forced `d2`/`d4`는 각각
  standalone exact0B만 전송하며 어떤 pair도 만들지 않음
- malformed C9와 잘못된 CA side/flag는 fail-closed; 중복 C9는 idempotent

자동 테스트는 raw 실측 CA decode, malformed 거부, CA side 권위 판정, deadline 경계,
generation mismatch, C9 즉시 cleanup, 000D prelude, kind01 calibration 재개,
CD/D2/D4 상호배타 전송을 포함합니다.
2026-07-18 현재 OX 표적 **16 tests OK**, 전체 `tools/test*.py` **86 tests OK**입니다.
