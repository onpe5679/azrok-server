# OX automatic progression after natural client C8 (2026-07-18)

> **LIVE VERIFIED by 122.** 자연 Plaza 목문 클릭의 C→S006B부터 request-driven 006E, 자연 C8, 자동 CC/CE/CA/CB/C9/000D, 최종 Plaza healthy까지 clean 원본 클라이언트로 완주했습니다.

## 결론

- **VERIFIED (code/test):** 서버는 클라이언트가 자연스럽게 C→S `00C8`을 보낸 뒤에만 OX 참가자로 admit하고, `CC → CE → CB → (다음 CE 또는 CD)`를 scheduler로 진행합니다.
- **VERIFIED (safety):** 자동화는 S→C `006E`를 먼저 보내지 않습니다. `admission_mode=client_c8_only`, `unsolicited_006e=false`입니다.
- **VERIFIED (network fail-closed):** 실제 소켓의 Plaza C8은 같은 연결에서 30초 이내 자연 C→S006B→S→C006E handshake가 있어야 합니다. 내부 controller/test의 격리 room 구성만 명시적 direct admission을 유지합니다.
- **VERIFIED (lifecycle):** 탈락자의 자연 C→S `00C9`는 기존 S→C `000D` 복귀 calibration 경로로 연결됩니다.
- **INFERRED:** admission grace, ready delay, question duration, result hold, exit stall의 시간값은 원본 장시간 실측 전까지 configurable inferred policy입니다.
- **VERIFIED (clean live, 122):** Plaza 실제 OX 목문 클릭 → 자연 C2S006B → request-driven S2C006E → 자연 C8 → 자동 1회전 → C9/000D → Plaza healthy 전체 왕복을 실측했습니다.

## 구현 계약

기본 정책은 `enabled=true`, C8 admission grace 2,000ms, ready delay 750ms, question 16,000ms, result hold 7,000ms, exit stall 12,000ms, scheduler poll 50ms입니다. `max_rounds=0`은 survivor가 남는 동안 question bank를 순환합니다. 이 숫자는 원본 권위값으로 단정하지 않습니다.

상태기는 각 room에 generation, round index, participants, survivors, spectators, answers, `next_action`, `next_due_at`을 보존합니다. question 중간 입장자는 현재 CE를 받지 않는 spectator이며 다음 fresh match에서 승격됩니다.

## 발견 후 수정한 경쟁 상태

**VERIFIED (reproduction/test):** 모든 기존 참가자가 loser가 된 뒤 scheduler가 `await_c9` due token을 소비하고, 마지막 loser C9 이탈 뒤 spectator만 남으면 다음 match가 영구 정지할 수 있었습니다. `_ox_remove_participant`가 이 정확한 상태에서 fresh due token을 다시 설정하도록 수정했습니다. spectator에게 강제 `D2`, `D4`, `006E`를 보내지 않습니다.

## 관제면

- `POST /api/ox/automation`: typed timing policy만 갱신하며 room/payload 임의 필드는 무시합니다.
- GUI는 AUTO, phase, round, generation, next action/due, deadline, participant/survivor/spectator, inferred timing을 표시합니다.
- 자동화 on/off는 확인 대화상자를 거치며, 기존 prepare/open/tick/finish 수동 controller도 유지됩니다.

## 검증

- OX 표적 24 tests PASS.
- 전체 `py_compile` PASS.
- x32dbg non-D path guard까지 포함한 전체 **177 tests PASS**.

관련 권위: 94, 96, 97, 114, 122. exact live sequence와 문 identity는 122를 권위로 사용합니다.
