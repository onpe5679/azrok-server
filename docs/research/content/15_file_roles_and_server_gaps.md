# Azrok 서버 프로토콜 복원: 파일 역할, 현재 서버의 틀린 점, 남은 미해결

Date: 2026-03-31
Evidence: Ghidra string search, decompilation, local data files, `azrok_server.py`

## 1. 로컬 파일 역할 정리

| 파일 | 바이너리 직접 문자열 참조 | 현재 해석 |
| --- | --- | --- |
| `lgc.tmp` | 있음 | visible stat schema 이름/min/max 템플릿 |
| `sys.tmp` | 있음 | 행동별 stat delta 테이블의 live source |
| `Azrok.dat` | 있음 | 방/가구/인벤토리 계열 metadata 가능성이 높음 |
| `init.csv` | 없음 | current-value seed. 초기값 참고용으로는 유용하지만 raw wire-order 정답은 아님 |
| `test.csv` | 없음 | `sys.tmp`의 alternate tuning variant |
| `JSData.tmp` | 없음 | `Guest` + `0xCC` padding + zero block. network template로 보이지 않음 |

## 2. `lgc.tmp`, `init.csv`, `sys.tmp`, `test.csv`의 실제 의미

### `lgc.tmp`

- 57행
- visible stat schema와 강하게 맞는다.
- 각 행은 이름, default, min, max 구조다.
- `StatSchema_LoadFallbackAndMapNames`가 만드는 local visible schema와 가장 잘 맞는다.

### `init.csv`

- 55행
- `IQ`와 일부 hidden row가 빠져 있다.
- 현재값 seed로는 유용하다.
  - 예: 레벨 25, 경험치 33000, 허기 10, 위생 80
- 하지만 raw wire stat bag의 정확한 순서를 설명하지는 못한다.

### `sys.tmp`

- 실제 바이너리 문자열 참조가 있다.
- section을 합치면 `20 + 9 + 2 + 1 = 32`개의 핵심 action row가 나온다.
- 이 32행 구조는 `0x000A group3`의 `1001..1032` family와 잘 맞는다.

관련 section count:

- 식사: 20
- 재마운: 9
- 유아기: 2
- 책: 1

### `test.csv`

- 직접 참조는 없고 `sys.tmp` 대체 튜닝본으로 보인다.
- 실제 차이는 5행뿐이다.
  - `수면1`
  - `용변1`
  - `목욕1`
  - `목욕교육`
  - `용변교육`

### `JSData.tmp`

- 길이 `329B`
- 내용은 `Guest` 문자열 2개, `0xCC` padding, trailing zero block
- 관측된 `C->S 0x0000(106B)`, `S->C 0x0007(472B)`, `S->C 0x000A(150B)`, `S->C 0x000B(62B)`와 길이/형태가 맞지 않는다.

## 3. `azrok_server.py`가 현재 틀린 지점

## 3.1 가장 치명적인 것

1. `S->C 0x0000`을 4바이트 zero payload로 보낸다.
   - 클라이언트는 최소 약 `0x183` 바이트를 읽는다.
2. stat/curve packet 번호를 `0x0010`, `0x0011`로 보낸다.
   - 바이너리 evidence는 `0x000A`, `0x000B`를 가리킨다.
3. `0x0007` stat bag을 `init.csv` row order 가정으로 채운다.
   - raw wire order와 다르다.
4. `0x000A group0`을 flat 22 values로 채운다.
   - 실제는 11개 stat의 `current/max` pair다.

## 3.2 state-1 쪽

5. 첫 authoritative `0x0064`를 `entry_mode=0x0A`로 보내 Plaza를 강제한다.
   - PatHouse `room.wmb -> 100` first-room 가설과 충돌한다.
6. `0x0066(self_id)`와 `0x0068(self_id)`를 같이 보내지만 self actor 기준으로 거의 inert다.
7. `C->S 0x0017`를 `<kind, stat_id, value>`로 파싱해도 실제 분기에는 반영하지 않는다.
8. `0x006E`는 late experimental branch인데도 현재 코드상 feature flag로만 매달려 있다.

## 3.3 문서/코드 불일치

9. `_build_response()` docstring가 실제 처리 opcode를 다 반영하지 못한다.
10. `_build_stat_table_0010_draft()` 주석은 binary baked defaults를 써야 한다고 적지만, 기본 동작은 guessed defaults다.
11. `proto_state`에는 이미 버린 전략의 dead field가 남아 있다.
   - `full_0064_pending`
   - `full_0064_sent`
   - `post_0017_heartbeat_count`

## 4. 지금 시점의 가장 강한 서버 구현 원칙

1. `0x0007`은 CSV 파일을 그대로 덤프해서 만들지 말 것
2. `0x000A group0`은 반드시 `current/max` pair 구조로 만들 것
3. `0x0007 +0x125..+0x12F`가 비면 `0xFF` sentinel을 넣을 것
4. `0x0007 +0x1D4..+0x1D7`에서 empty는 `0xFF`이고 `0`은 유효값으로 취급할 것
5. `C->S 0x0064`는 echo하지 말 것
6. 첫 authoritative `0x0064`에서 Plaza entry byte를 강제하지 말 것
7. self actor에 대해 `0x0066`, `0x0068`을 정답 packet처럼 믿지 말 것

## 5. 아직 끝까지 못 박지 못한 미해결

### A. `S->C 0x0000` full layout

확정:

- 큰 구조체라는 점
- count field와 id/value array가 있다는 점

미해결:

- 정확한 record semantics
- 실서버가 채우는 id/value 목록

### B. `S->C 0x0003` 첫 바이트

확정:

- manager `gm+0x31C63`에 저장된다.

미해결:

- flag 의미
- 첫 방 진입에서 어떤 값이 원래 정답인지

### C. `0x0007 +0x97..+0x11D`, `+0x131`

확정:

- 모두 `FUN_0059BC00` 타입의 list/set block이다.

미해결:

- block별 정확한 gameplay 이름
- 실서버가 어떤 id 집합을 넣는지

### D. `0x000A group1/2/6`

확정:

- key 공간은 복원됐다.

미해결:

- 각 key의 완전한 gameplay 의미
- 실제 초기값 source file

### E. `0x006E byte0`와 natural ready-latch 경로

확정:

- `byte1 == 0`이 중요하다.
- `gm+0x129B`와 two manager fields가 갱신된다.

미해결:

- `byte0`의 정확한 semantic label
- `gm+0x31946` latch가 원래 어떤 packet/scene path로 자연스럽게 세워지는지

### F. `SendC2S_0064_LocalBootstrapStatus`가 읽는 이름 버퍼의 원래 upstream source

확정:

- stage-0 bootstrap은 `gm+200`에서 이름을 읽는다.

미해결:

- 이 이름이 원래 어떤 inbound packet에서 authoritative하게 채워지는지

## 6. 다음 단계 우선순위

1. 새 서버 구현에서는 `0x000A`, `0x000B` 번호부터 바로잡기
2. `0x0007` builder를 CSV row-order 가정에서 분리하기
3. first authoritative `0x0064`를 `0x00` 또는 `0x14` branch로 시험하기
4. self follow-up에서는 `0x0066`, `0x0068`을 빼고 `0x0069`만 남긴 실험 가지를 만들기
5. `S->C 0x0000` full struct를 별도 복원 대상으로 올리기

## 최종 한 줄 요약

`init.csv`는 "좋은 초기값 참고서"이고, `lgc.tmp`는 "visible schema", `sys.tmp`는 "행동 로직"이다. 하지만 raw wire protocol 정답은 이 파일들을 그대로 보내는 데 있지 않고, `Azrok.exe`가 실제로 읽는 packet layout과 숨은 인덱스/registry 구조를 맞추는 데 있다.
