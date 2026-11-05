# OX mode-2 실제 클라이언트 C→S CA 및 D2 종료 실측 (2026-07-18)

> **PARTIALLY SUPERSEDED by 97.** 이 문서의 CD→D2는 당시 서버가 잘못 보낸 pair의 실측입니다. 현행 계약은 CD/D2/D4 상호배타이며 C9 뒤 000D calibration으로 Plaza에 복귀합니다.

관련 권위 문서: 84, 92, 93, 95. 이 문서는 `azrok_server.py`의 mode-2 구현을 실제 클라이언트 한 개로 검증한 동적 분석 기록입니다. 원본 서비스나 외부 서버에는 접속하지 않았고, 로컬 보존 서버 TCP 9207/control 9300만 사용했습니다. x32dbg와 Frida는 이 실측에 사용하지 않았습니다.

표기: **VERIFIED**=실제 클라이언트 패킷·메모리·화면을 직접 관찰, **INFERRED**=직접 증거에서 도출한 구현 후보, **NOT VERIFIED**=추가 동적 확인 필요.

> **SUPERSEDED:** 92/93의 “OX 답안은 C→S 0066/0067 이동만으로 제출된다”는 가설은 본 문서의 C→S `00CA` 실측으로 폐기해야 합니다. 0066/0067은 여전히 일반 이동 wire로 유효하지만, OX 판정의 유일한 입력으로 취급하면 안 됩니다.

## 1. 실행 기준선

- **VERIFIED** clean runtime PID `77412`, entity `2`, capture `captures/packets_20260718_102145.txt`였습니다.
- **VERIFIED** Plaza에서 targeted S→C `006E[0000]` 한 프레임(seq 248) 뒤 C→S `00C8` exact 0B(seq 249)가 자연 발생했고, 서버의 S→C `00C8` exact 14B(seq 250) 뒤 `scene=111`, `dispatch_mode=2`, heartbeat 정상, engine error 없음으로 OX 방에 입장했습니다.
- **VERIFIED** 화면에서 O 표시는 왼쪽, X 표시는 오른쪽에 보였습니다. 이는 화면 라벨의 직접 확인일 뿐 world-X 부호와의 대응을 다시 추정하지 않습니다.

## 2. 질문 개시와 새 C→S 00CA

| seq | 시각 | 방향/opcode | 길이 | payload / 의미 |
|---:|---|---|---:|---|
| 261 | 10:34:29.681 | S→C `00CC` | 0 | 준비/카운트다운 |
| 262 | 10:34:30.260 | S→C `00CE` | 131 | `1 + 1 = 2`, side 0, stars 1 |
| 267 | 10:34:45.288 | C→S `00CA` | **22** | `0100000000000000000000000000000000f78fdc7201` |

- **VERIFIED** CE 뒤 15.028초에 C→S `00CA` 22B가 발생했습니다.
- **VERIFIED** CE와 CA 사이에는 사용자의 클릭·키 입력이나 서버 측 수동 이동 주입이 없었습니다.
- **VERIFIED** 현재 서버는 이 프레임을 unknown C2S로 기록했고 OX `answers`는 빈 상태로 남았습니다.
- **INFERRED** 발생 시점과 mode-2 전용 opcode 충돌을 함께 보면 `00CA`는 OX의 주기적 위치/답안 제출 후보입니다. 다만 22B 내부 필드와 첫 바이트 의미는 아직 확정하지 않습니다.
- **NOT VERIFIED** 실제 O/X 발판으로 이동한 뒤 CA의 어느 필드가 바뀌는지, CA가 한 질문에서 반복되는지, CA만으로 판정 가능한지는 서버 decoder를 추가한 clean runtime에서 A/B 표본을 받아야 합니다.

## 3. 마감, 탈락, C→S 00C9

- **VERIFIED** deadline 뒤 `/api/ox/tick`은 entity 2를 loser로 결정했고, S→C `00CB` seq 292 payload `01000000`를 보냈습니다. 서버 entity 2가 클라이언트 self actor id 1로 변환된 결과와 일치합니다.
- **VERIFIED** 화면은 즉시 “게임에서 탈락하여 돌아가는 중...” 연출로 전환됐습니다.
- **VERIFIED** CB 6.503초 뒤 C→S `00C9` exact 1B payload `00`가 seq 293으로 자연 발생했습니다.
- **INFERRED** `00C9[00]`는 탈락 연출 완료/복귀 준비 acknowledgement 후보입니다. 단일 표본이므로 의미를 확정하지 않습니다.

## 4. D2 종료는 현재 구현에서 Plaza 복귀를 완주하지 못함

- **VERIFIED** `/api/ox/finish {exit_mode:"d2"}`는 S→C `00CD` exact 0B(seq 312)와 S→C `00D2` exact 0B(seq 313)를 같은 시각에 보냈습니다.
- **VERIFIED** D2 뒤 디스패치 mode는 0, scene 표시는 110이 됐지만 phase는 5에 남았습니다. 60초 이상 C→S `0064`/`0065`가 없었고 서버 `room_kind=-2`, `ox_room_id=default`도 남았습니다.
- **VERIFIED** heartbeat는 계속 왕복했고 engine error는 없었지만 화면은 탈락 복귀 연출에 고정됐습니다. 따라서 “process alive”가 “Plaza 복귀 완료”를 뜻하지 않습니다.
- **INFERRED** 현재 `CD→D2` 순서 또는 D2 이전/이후 C→S `00C9` handshake 처리가 부족합니다. 서버는 `00C9`와 `00CA`를 unknown으로 버리지 말고 먼저 exact decoder와 상태 전이를 구현해야 합니다.
- **NOT VERIFIED** D4 경로는 정적 보강 전에는 시도하지 않았습니다.

## 5. clean restart 결과와 운영 경계

- **VERIFIED** stuck 증거를 고정한 뒤 clean restart했습니다. 새 PID는 `107696`, capture는 `captures/packets_20260718_103929.txt`입니다.
- **VERIFIED** 새 세션은 `saved_state_key=a706c61796572_s0_c417a726f6b31`와 persisted evolution 1을 읽었지만 lobby roster는 비어 `account_has_characters=false`였고 캐릭터 생성 화면을 표시했습니다.
- **VERIFIED** 이후 S→C 0003/0007/0005/000A/000B와 C→S 0008은 오갔지만 마지막 관찰은 `scene=100`, `phase=2`, `mode=0`, heartbeat 정상, engine error 없음으로 Plaza baseline이 복구되지 않았습니다.
- **NOT VERIFIED** 이 restart 이상이 OX lifecycle 정리, roster lease, 또는 별도 lobby snapshot 문제 중 무엇인지는 본 실측에서 단정하지 않습니다.

## 6. 서버 구현에 즉시 반영할 계약 변경

1. C→S `00CA` exact 22B decoder를 mode-2에 추가하되 필드 의미가 확정되기 전에는 raw/timestamp/generation을 보존합니다.
2. C→S `00C9` exact 1B decoder를 추가하고 CB 이후 상태에서만 수용합니다.
3. 기존 0066/0067 기반 `answers` 갱신은 잠정 정책으로 격하합니다. CA A/B 표본과 일치하기 전에는 원본 동작으로 표시하지 않습니다.
4. D2 성공 조건은 `mode=0`만이 아니라 C→S 자연 복귀 보고, OX metadata 제거, Plaza scene 110/phase 4, heartbeat 정상까지 묶습니다.
5. 현재 runtime에서는 active click 표본을 더 받지 않습니다. CA decoder/상태 전이를 구현하고 clean restart에서 Plaza baseline을 먼저 복구한 뒤 O/X 양쪽 A/B를 재개합니다.

## 7. 증거 파일

- `artifacts/dynamic-analysis/ox_primary_e2e_evidence_20260718.json`
- `artifacts/dynamic-analysis/ox_primary_mode2_admitted_20260718.bmp`
- `artifacts/dynamic-analysis/ox_primary_after_cb_loser_20260718.bmp`
- `artifacts/dynamic-analysis/ox_primary_after_d2_20260718.bmp`
- `artifacts/dynamic-analysis/ox_post_restart_lobby_20260718.bmp`
- 패킷 원문: `captures/packets_20260718_102145.txt`, `captures/packets_20260718_103929.txt`
