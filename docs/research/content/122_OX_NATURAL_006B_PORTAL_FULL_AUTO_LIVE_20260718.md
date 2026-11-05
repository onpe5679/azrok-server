# OX 자연 문 진입과 자동 1회전 실전 검증 (2026-07-18)

## 결론

- **VERIFIED (clean live):** Plaza의 실제 OX 입구는 보라색 `FULL PLAY` 표지판이 아니라 두 보라색 표지 사이의 갈색 목문입니다. 자연 클릭으로 C→S `006B`가 발생했고, 서버의 request-driven S→C `006E[00 00]` 뒤 원본 클라이언트가 자연 C→S `00C8`을 보냈습니다.
- **VERIFIED:** 문 클릭부터 `00C8 → 00CC → 00CE → 00CA → 00CB → 00C9 → 000D`까지 자동 scheduler 한 회전을 입력 보조 없이 완주했고, 최종 Plaza `scene=110 / phase=4 / dispatch_mode=1 / self=1 / room=27`로 건강하게 복귀했습니다.
- **VERIFIED:** 자동화는 unsolicited `006E`를 보내지 않았습니다. `006E`는 같은 세션의 자연 C→S `006B` 요청에 대한 응답이었습니다.
- **VERIFIED (code/test):** 후속 네트워크 C8은 같은 connection의 최근 006B marker를 30초 TTL로 검사합니다. marker 없음·만료는 Plaza에서 fail-closed하고, 유효한 006B 뒤 C8만 admission합니다.
- **INFERRED:** 질문/결과 대기 시간의 숫자는 여전히 configurable 보존 정책이며 원본 서버의 절대 시간값으로 단정하지 않습니다.

## 캡처 증거

Run `20260718T191339_95676_052fd24d`:

| seq | 방향/opcode | payload / 의미 |
|---:|---|---|
| 212 | C→S `006B` | empty, 실제 갈색 목문 자연 클릭 |
| 213 | S→C `006E` | `0000`, origin `ox`, 요청 기반 입장 허용 |
| 214 | C→S `00C8` | empty, 원본 클라이언트 자연 admission |
| 215 | S→C `00C8` | 14B, 참가 상태 |
| 216 | S→C `00CC` | ready |
| 219 | S→C `00CE` | 131B, 질문 `1 + 1 = 2`, correct side 0 |
| 222 | C→S `00CA` | 22B, side 1, 자연 timeout 오답 제출 |
| 223 | S→C `00CB` | actor 1 loser |
| 226 | C→S `00C9` | `00`, 자연 퇴장 |
| 227 | S→C `000D` | `00`, 자동 Plaza calibration 재개 |

후속 seq228..244 0016/0004 calibration, seq245 C→S0064, seq246 S→C0064 뒤 seq247..274 heartbeat가 지속됐습니다. 서버와 클라이언트 모두 Plaza healthy였고 OX room은 idle, participants empty, `last_auto_error=null`, history generation 1이었습니다.

## 화면/이동 교정

- 보라색 표지판 클릭은 일반 `0066/0067` 이동만 만들었고 OX portal이 아니었습니다.
- 실제 목문 클릭 직전 서버 위치는 대략 `(4326,399)`였고 당시 화면 상대좌표 약 `(0.43,0.16)`이었습니다. 이는 재현용 관찰값이지 고정 월드→화면 투영 계약은 아닙니다.
- 방 탐색 자동화는 장거리 이동을 목표로 하지 않습니다. 서버가 검증된 문 근처로 재배치하고 마지막 문 클릭·portal commit·방 로드·콘텐츠 action은 원본 경로로 실측하는 기존 전략을 유지합니다.

## 판정

문서 119의 `clean automated full round live NOT VERIFIED`는 본 문서가 **VERIFIED**로 종결합니다. 119의 C8-only admission, spectator/deadlock 수정, no-unsolicited-006E 계약은 유지됩니다.

관련 권위: 94, 96, 97, 119, INDEX.
