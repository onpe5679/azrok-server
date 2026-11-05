# 0x000D 동적 코어 성공과 요청 구동형 calibration 교정

작성일: 2026-07-17  
상태: 동적 재현 및 요청 구동형 보정 경로 검증 완료

## 1. 핵심 결과

무패치 Nexus=40 기준선의 새 세션(PID 117840)에서 서버가 `S->C 0x0003`
(`Data\\Space\\Plaza`)와 `S->C 0x000D 00`을 보낸 뒤, 클라이언트의
`Plaza_TransitionFromRoom` 코어 경로가 x32dbg에서 끝까지 통과했다.

기록된 순서는 다음과 같다.

1. `0x00568770` transition entry
2. `0x0050A802` scene write (`ECX=0x6E`)
3. status/azron/calendar/state list cleanup 4회 call/return
4. `gm+0x31C72` flag write
5. `0x0059DE50` calibration reset entry
6. 첫 `C->S 0x0016[01]`
7. reset return 및 transition return
8. `core_success`

전환 직후에도 프로세스는 살아 있고 API 상태는 `scene=110`,
`responding=true`, `child all_zero=78/78`이었다. 따라서 이전의 즉시 크래시는
이번 실행에서 재현되지 않았고, 78개 panel preflight는 전환을 차단하는 근거가
아니다.

증거 파일(첫 코어 재현):

- `artifacts/dynamic-analysis/X32DBG_000D_TRACE_20260717_075050.jsonl`
- `captures/packets_20260717_075050.txt`

교정 후 clean-session 증거:

- `artifacts/dynamic-analysis/x32dbg_000d_trace_20260717_075744.jsonl`
- `captures/packets_20260717_075744.txt`

교정 후 세션(PID 113980)에서는 `0x000D` 직후 `hansol_calibration_active=true`
및 count=0으로 arm 되었고, 다섯 번의 `C->S 0x0016[01]`에 각각
`S->C 0x0004[01]`이 대응했다. 이어 `C->S 0x0064`가 도착했고 서버의
`S->C 0x0064`/`0x006E` 응답 후 `scene=111`, `self_actor_id=1`,
`phase=5`, `responding=true`를 유지했다. `legacy_0019_memory_shortcut=false`
이며 바이너리 패치는 사용하지 않았다.

## 2. 첫 실행에서 발견한 실제 정지 원인

코어 성공 뒤 `C->S 0x0016[01]`은 발생했지만 서버의 `calib_0004_count`가
bootstrap 단계에서 이미 5로 남아 있었다. `0x000D`는 control API의 직접
inject이므로 기존 `_build_response(0x0016)` 경로의 카운터 reset을 거치지
않았고, 결과적으로 서버는 `S->C 0x0004`를 하나도 보내지 않았다.

이것은 엔진 정지나 vtable 실패가 아니라 서버 상태 reset 누락이다.

## 3. 교정 내용

`azrok_server.py`에 다음을 반영했다.

- `S->C 0x000D 00` inject 시 Hansol calibration을 arm하고
  `calib_0004_count`, `client_0064_*`를 reset한다.
- Hansol arm 상태에서는 클라이언트가 보낸 `C->S 0x0016[01]`에만
  `S->C 0x0004[01]`을 최대 5회 응답한다.
- 일반 bootstrap `C->S 0x0016[00]`은 기존처럼 `S->C 0x0004[00]` 경로를
  사용한다.
- 클라이언트 `C->S 0x0064`가 도착하면 Hansol arm을 해제한다.
- `hansol` GUI macro는 `0x000D`만 전송하며 0x0004를 선제 주입하지 않는다.

## 4. 검증 기준과 결과

새 clean session에서 다음을 확인했다.

1. `0x000D` 직후 `hansol_calibration_active=true`, count=0 — 통과
2. 다섯 번의 `C->S 0x0016[01]` 각각에 대응하는 `S->C 0x0004[01]` — 통과
3. 다섯 번째 후 자연 발생하는 `C->S 0x0064` — 통과
4. 서버의 authoritative `S->C 0x0064`/`0x006E` 응답 — 통과
5. 게임 프로세스 응답성, 최종 scene, 패킷 캡처 및 x32dbg trace — 통과

이번 문서에서는 `0x0064`를 공간 선택자로 해석하지 않는다. 공간은
`0x0003` path와 그 상위 room-load 경로가 결정하며, `0x0064`는 이미 로드된
레벨에 self entity를 배치하는 후속 handshake다.

## 5. Plaza 목표는 아직 열려 있음

이번 증명은 Hansol/transition 계약이 살아 있다는 뜻이지, 최종 공간이
Plaza라는 뜻은 아니다. 실제 최종 상태는 `scene=111`인 OX 퀴즈 공간이었다.
따라서 다음 동적 패스에서는 `0x0050A7F0`(scene request), `0x0050A880`
(post-load bridge), `0x0050A0F0`(room-code dispatch), `0x0050B400`(room
initializer), `0x00614370`(Hansol stage entry), `0x006143EC`/`0x005AB738`
(stage-0의 0x0064 sender)를 함께 관찰해 OX 분기가 발생하는 정확한 지점을
기록한다. 이 체크포인트들은 `tools/x32dbg_000d_trace.py`에 등록되어 있다.

## 6. 0x006E A/B 결과 — Plaza 확인

정적 분석이 지목한 OX 강제 경로를 분리하기 위해 새 clean session(PID
83304)에서 `AZROK_PLAZA_REPLY_MODE=0064`로 동일한 전환을 실행했다.
`C->S 0x0064[01]` 뒤 authoritative `S->C 0x0064`만 보내고 `S->C 0x006E`는
보내지 않은 결과는 `scene=110`, `phase=4`, `self_actor_id=1`로 유지되었고,
게임은 응답 상태를 계속 유지했다. 실제 캡처에서 3D 야외 Plaza(중앙
캐릭터, 광장 표지판/미니맵/HUD)가 확인되었다.

따라서 문제의 원인은 `0x000D`나 `0x0064 entry_kind`가 아니라 성공 직후
서버가 추가하던 `S->C 0x006E[00,00]`이다. 이 패킷은 클라이언트의 ready
commit을 통해 `0x0C -> global room 0x6F -> OXQuiz.wmb`를 실행한다.
지원 런처 기본값을 `AZROK_PLAZA_REPLY_MODE=0064`로 변경했고, `both`는
OX 재현용 명시적 진단 모드로 남겼다.

A/B 증거: `captures/packets_20260717_080648.txt`.

수정된 지원 기본값을 one-shot override 없이 재시작한 최종 세션도
`plaza_reply_mode="0064"`, `scene=110`, `phase=4`, `self_actor_id=1`,
`hansol_calibration_samples_sent=5`를 재현했다. 최종 캡처는
`captures/packets_20260717_081659.txt`이다.
