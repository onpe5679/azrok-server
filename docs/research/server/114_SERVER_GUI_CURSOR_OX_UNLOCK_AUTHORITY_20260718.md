# 서버·GUI 대개편 후속: cursor/OX/entity projection/액세서리 해금 권위 (2026-07-18)

표기: **VERIFIED test**=실행 코드 회귀·mock/runtime probe로 확인, **VERIFIED static**=디컴파일·확정 문서 계약으로 확인, **NOT VERIFIED live**=원본 클라이언트 추가 실측 필요.

## 결론

105/110의 대개편 청사진에서 실제 운영을 막던 네 가지를 구현했습니다.

1. 다중 클라이언트 appearance를 active entity별로 투영하고 `S2C 0x0065/0x0067` lifecycle을 반영했습니다.
2. OX phase/deadline/participant/answer와 prepare/open/tick/finish를 다루는 전용 운영 패널을 추가했습니다.
3. packet/event cursor API와 overview를 추가하고 GUI를 500ms 증분 polling으로 전환했습니다.
4. 액세서리 set의 stat/evolution 해금 검증을 서버 권위로 적용해 forged locked selector를 fail-closed 처리했습니다.

전체 `python -m unittest discover -s tools -p 'test_*.py' -q`는 **131 tests PASS**입니다.

## 1. entity별 appearance projection

- **VERIFIED test/runtime ring** active client의 `entity_id`를 projection target으로 전달해 다른 연결의 actor id 1 self ACK/baseline이 섞이지 않습니다.
- **VERIFIED test** `S2C 0x0065`는 remote appearance 전체를 reset합니다.
- **VERIFIED test** `S2C 0x0067`은 해당 remote actor만 제거합니다.
- baseline source/seq, runtime delta source/seq, canonical은 계속 분리 표시합니다.

112의 실제 두 클라이언트 ring에서 active entity 3 projection은 entity 2의 self packet을 섞지 않았습니다.

## 2. OX 운영 패널

표시:

- room, phase, generation, monotonic deadline
- question index/text, correct side
- participants/survivors/answers
- 참가자별 survivor/eliminated와 answer side/generation/timeout

제어:

- prepare
- open question: question index optional, duration `1..300000ms`
- tick
- finish: 상호배타 `CD/D2/D4`

**VERIFIED browser/test** phase에 맞지 않는 버튼은 비활성화하고 모든 state transition 직전에 확인창을 띄웁니다. room/input 검증, double-submit 방지, HTTP/409/API 오류 유지, 응답 snapshot 즉시 반영을 확인했습니다. read-only browser mock에서 question phase 2명/answer 1명의 렌더와 tick confirm을 확인했고 POST는 취소했습니다.

## 3. packet/event cursor API와 증분 GUI

API:

- `GET /api/packets?after_seq=<n>&limit=<1..200>`
- `GET /api/events?after_seq=<n>&limit=<1..200>`
- `GET /api/overview`

cursor 응답은 `oldest_seq`, `latest_seq`, `next_seq`, `dropped_before_seq`, `gap`, `overflow`, `has_more`, `sequence_monotonic`을 제공합니다. malformed/negative cursor는 HTTP 400이며 기존 `/api/state`는 호환을 위해 유지합니다.

GUI:

- 최초와 매 20회(10초)는 full `/api/state` snapshot을 읽습니다.
- 나머지 500ms poll은 `/api/overview`와 packet/event cursor를 병렬 사용합니다.
- seq dedupe/정렬, packet 400/event 200 bounded merge, 최대 4페이지 drain을 적용합니다.
- gap이면 local ring을 버리고 oldest부터 재기준화하며 `CURSOR GAP` badge·경고·toast를 latch합니다.
- cursor endpoint/JSON 실패는 즉시 `/api/state` fallback하고 fallback 상태를 표시합니다.

**VERIFIED runtime probe** 임시 TCP9210/control9302 서버에서 overview port 9210, empty packet cursor `gap=false/overflow=false/monotonic=true`, event seq1 `gap=false/overflow=false/monotonic=true`를 직접 조회한 뒤 프로세스를 종료했습니다.

## 4. 액세서리 stat-derived unlock 권위

109의 exact gate를 서버 mutation 앞단에 적용했습니다.

- canonical `snapshot_hex` exact196B에서 evolution `+0x05`와 70 u16 stats `+0x0A`를 읽습니다.
- stat1은 level입니다.
- group1=`31..33`, group2=`34..36`, group3=`37..39`, group4=`30`, group5=`40..66`의 합계입니다.
- 109의 9행 threshold와 slot1/value4의 evolution>=3 gate를 적용합니다.
- level/direct-stat/all-stat gate도 `FUN_005B2CB0` 계약대로 적용합니다.
- recovered gate가 없는 tier1 selector는 클라이언트 기본 항목으로 허용합니다.

**VERIFIED test** locked set은 canonical 저장, live metadata 변경, self ACK, peer relay가 모두 0건입니다. boundary allowed, group1..5 exact, evolution 2 reject/3 accept를 회귀로 고정했습니다. clear의 current-value stale 검증은 기존 그대로 유지합니다.

## 운영 상태

- 주 server PID106840/client PID104264는 재시작하거나 변경하지 않았습니다.
- 실행 중인 주 9300과 격리 9301은 이전 import의 PAGE를 보유하므로 새 OX/cursor GUI는 다음 정상 서버 재시작부터 노출됩니다.
- 주 `profile_playable_v2` SHA 3개는 112 종료 뒤에도 `875390...817E`, `821D08...2940`, `D19045...31F`로 불변입니다.
- Ghidra MCP 두 bridge는 재조회 당시 running instance 0개였으므로, 이번 정적 근거는 기존 decompile 산출물과 독립 바이너리 정적 에이전트 검증을 사용했습니다.

## 남은 대개편 항목

- **VERIFIED partial by 116** 공통 canonical mutation transaction id/revision/exact-file SHA receipt와 GUI. durable journal·delete archive·CAS는 남음.
- **NOT VERIFIED** 단일 protocol registry source에서 API·GUI·inspector 생성
- **NOT VERIFIED** 캐릭터별 70 stats/evolution/disease/runtime-row의 완전 semantic projection
- **NOT VERIFIED** CAS 기반 canonical admin preview/commit 및 normal/diagnostic mode 경계

Related: 84, 105, 109, 110, 111, 112, 113, INDEX.
