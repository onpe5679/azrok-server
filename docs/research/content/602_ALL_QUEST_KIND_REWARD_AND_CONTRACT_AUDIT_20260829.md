# 602 — 전체 퀘스트 kind 보상·계약 감사 (2026-08-29)

## 결론

- #601의 kind5 튜토리얼 순서 외에 **정상 클라이언트에서 추가로 재현된 보상
  금액/ACK 오류는 없다.** 서버의 정적 FunCorn 표는 원본 switch/table과 전
  항목 일치한다.
- 합성 정상 순서에서 보상형 kind0/1/2 총 58개는 58/58, kind5 다섯 aux는
  5/5가 balance ACK와 durable commit을 통과했다. 전체 suite는 299 tests PASS다.
- 그러나 kind1/2와 일부 후반 퀘스트는 실제 UI 자연 완료 표본이 없고, 조작되거나
  비정상 순서인 0011/0012를 fail-closed 처리하지 못하는 계약 공백이 남아 있다.
  이를 정상 플레이 결함과 구분한다.

## VERIFIED — 원본/서버 보상 행렬

| kind | 의미 | 로컬 효과 | FunCorn | 원본 순서 |
|---:|---|---|---:|---|
| 0 | 음식 wish | stat7 -10~-30 | 38/40/43/45/48 | 0012 → 0011 |
| 1 | 스킬/미니게임 | 해당 skill +15~19 | 19/21/22/24 | 0012 → 0011 |
| 2 | 급식/운동/음식 | stat7 -10~-20 | 0 또는 24/29/35 | 보상형 0012→0011, 무보상형 0011 |
| 3 | 성장/진화 | stage 0→1→2→3 | 0 | 0010→0011→0007→0010→0011 |
| 5 | stage0 튜토리얼 | EXP +40/+50/+60/+70/+80 | 각 100 | 0011 retire→0012→0011 next |

- `quest_funcorn_reward_for_runtime_row`의 kind0 19개, kind1 24개, kind2
  보상형 15개, kind5 5개가 원본 `FUN_005A6CE0/7240/7910`과
  `DAT_006E0D80`에 exact 일치한다.
- kind2 action `CF/DC-E2/102`는 원본부터 FunCorn callback이 없는 정상
  무보상 완료다. 콘이 안 오르는 것을 버그로 분류하면 안 된다.
- kind3은 FunCorn이 아니라 진화가 보상이며 서버 threshold mirror와
  0010/0011/0007 계약을 사용한다.

## VERIFIED — 자연 캡처 범위

- kind0: food1001 세 표본. 모두 `0014→0008→0012/40→0011→0007`.
- kind3: aux0 성장 완료 6표본. 모두 completion/removal/stage edge/next proposal
  계열과 일치했다.
- kind5: 운영 aux212/202/203 세 표본. 모두 #601의 선행-retire 순서였다.
- 운영 mutation journal의 quest_reward reject 3건은 전부 #601 이전의 같은
  kind5 문제이며 그 뒤 새 reject는 없다.

## NOT VERIFIED — 실제 UI 전수 수용

- kind0: 19개 중 food1001 외 18개.
- kind1: 24개 전부.
- kind2: 15개 보상형과 무보상 action 계열 전부.
- kind3: aux1~6의 stage1→2 및 stage2→3.
- kind5: aux227/201과 최종 kind3/aux0 handoff.

따라서 정적·합성 통과를 실제 UI 전수 성공으로 과장하지 않는다.

## VERIFIED — 남은 fail-closed 계약 공백

정상 캡처에서는 재현되지 않았지만 격리 서버에서 다음을 재현했다.

1. 임의의 유효 kind1 행을 빈 canonical에 0011로 삽입한 뒤 0012→0011만으로
   FunCorn을 만들 수 있다. unknown kind/aux/value도 저장된다.
2. kind5 reverse-order replacement를 반복하면 원본 체인 검증 없이 반복 지급할
   수 있다. `212→202→203→227→201→kind3/0` durable cursor가 없다.
3. quest pair 사이 다른 packet을 끼워 correlation을 실패시킨 뒤 0011을 보내면
   active row만 무보상 삭제될 수 있다.
4. 보상 대상 한 행과 무관한 다른 active 행을 같은 0011에서 함께 제거해도
   reward ACK 후 전체 projection이 저장된다. 동시 expiry인지 오염인지 구분하지 않는다.
5. kind3 completion 0010이 canonical active aux/generation에 즉시 결합되지 않아
   잘못된 aux pending을 남길 수 있다.

이들은 보존 서버의 무결성/비정상 순서 문제다. packet adjacency를 무작정
완화하면 서로 다른 quest를 오결합할 수 있으므로, 수정 전 kind1/2 자연 캡처와
expiry semantics가 필요하다. 이번 감사에서는 정상 운영 경로를 바꾸지 않았다.

## 유지보수 보강

- 원본 보상표 전 항목 exact 테스트와 kind0/1/2 대표 reward→retire ACK matrix를
  추가했다.
- `RUNTIME_ROW_SERVER_POLICIES`의 wire 부재라는 오래된 주석을 현재
  0011/0012 correlation 사실로 정정했다. 런타임 동작은 변경하지 않았다.
