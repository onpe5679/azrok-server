# durable mutation journal·delete receipt (2026-07-18)

표기: **VERIFIED test**=자동 회귀/장애 주입으로 확인, **VERIFIED code**=현재 구현을 직접 확인, **NOT VERIFIED**=실제 전원 차단 또는 원본 클라이언트 live가 더 필요함.

## 결론

116의 RAM-only transaction receipt를 append-only JSONL audit journal로 확장했습니다.

- **VERIFIED code/test** 모든 mutation receipt는 `mutation_transactions_v1.jsonl`에 UTF-8 JSON 한 줄로 기록되고 매 행 `fsync`됩니다.
- **VERIFIED test** 재시작 시 최대 sequence와 최근 500행을 복구해 다음 transaction id가 연속됩니다.
- **VERIFIED test** 마지막 행이 절단돼도 이전 정상 행을 복구하고 corrupt count를 표시하며, 다음 정상 행을 별도 줄로 추가합니다.
- **VERIFIED test** 저널 append/fsync 실패는 별도 `audit_journal_failure`로 보고하되 이미 atomic replace된 canonical 상태를 롤백하지 않습니다.
- **VERIFIED test** character delete 성공·dense-tail 거부·부분 archive rollback 모두 `character_delete` 영수증과 archive 결과를 남깁니다.
- **VERIFIED test** `/api/transactions` cursor와 `/api/overview.cursor.transactions`가 독립 sequence를 제공합니다.
- **VERIFIED code/test** GUI 영속성 카드가 journal durable/degraded, latest seq, failure/corrupt/gap 수를 표시합니다.

## 1. 디스크 계약

경로는 현재 profile namespace의 `state_store_dir/mutation_transactions_v1.jsonl`입니다. 각 행 schema는 `azrok.mutation.transaction.v1`이며 다음을 포함합니다.

- 독립 `seq`, `transaction_id`, UTC timestamp
- kind/result, request opcode/packet seq
- opaque `chr_*` character id와 selected-key validity
- revision/SHA before/after
- changed fields, bounded metadata, sanitized reason

**VERIFIED test** raw account/character storage key와 binary payload/snapshot은 journal에 기록하지 않습니다. key/password/account raw 계열은 redaction하고 문자열·목록·중첩 깊이를 제한합니다.

## 2. 저장 순서와 실패 의미

canonical mutation은 다음 순서를 유지합니다.

```text
validate → deterministic tmp write/fsync → os.replace
→ in-memory revision/cache update → audit journal append/fsync
```

따라서 journal 실패는 `journal_status=failed`인 감사 손실이지 게임 상태 rollback 사유가 아닙니다. 반대로 canonical replace 실패는 rejected receipt이고 revision/file bytes는 불변입니다.

이 결정은 재접속 가능한 게임 상태를 우선 보존하면서 감사 계층 저하를 GUI/API에서 숨기지 않는 정책입니다.

## 3. restart recovery

**VERIFIED test** 로더는 파일을 streaming으로 읽고 다음을 복구합니다.

- 정상 행 중 최대 seq
- 최근 500 receipt RAM window
- corrupt line 수
- non-increasing/gap sequence 수

파일 마지막이 newline이 아니면 append 전에 newline을 하나 보강해 절단 행과 다음 정상 JSON을 섞지 않습니다. corrupt 행은 삭제하거나 고쳐 쓰지 않아 보존 증거를 유지합니다.

## 4. 캐릭터 삭제 영수증 경계

**VERIFIED test** current delete는 다음을 기록합니다.

- success: archived status와 moved file 수
- dense tail precondition failure: archive 전에 rejected
- 두 번째 move 장애: rollback attempted/failed 상태와 rejected

그러나 현재 archive는 여러 파일을 `os.replace`한 뒤 실패 시 역순 rollback하는 구조입니다.

- **NOT VERIFIED crash durability** 프로세스/전원 중단이 이동 사이에 발생했을 때 재시작 reconciliation이 없습니다.
- **NOT VERIFIED two-phase delete** `pending/committed` staging directory 또는 manifest 기반 commit이 아직 없습니다.
- 따라서 본 문서는 “삭제 영수증이 durable”함을 확인하지만 “삭제 다중 파일 transaction 자체가 전원 차단에 원자적”이라고 주장하지 않습니다.

## 5. API·GUI

- `/api/transactions?after_seq=N&limit=M`: RAM/restart-recovered 최근 500행 cursor
- `/api/overview.cursor.transactions`: oldest/latest/gap without items
- operator `mutation_journal`: file basename, latest seq, loaded rows, failures, corrupt lines, sequence gaps, durable flag
- GUI Persistence: `JOURNAL`, `JOURNAL SEQ`, `JOURNAL HEALTH`

**NOT VERIFIED disk history query** API는 전체 JSONL을 검색하지 않습니다. 500행 이전 기록은 파일에 남지만 현재 cursor API로 조회할 수 없습니다.

## 6. 회귀

- `py_compile azrok_server.py azrok_control.py` PASS.
- 전체 `python -m unittest discover -s tools -p 'test_*.py' -q`: **153 tests PASS**.
- 재시작 sequence/tail, truncated tail, journal append failure, delete success/reject/rollback, transaction cursor, GUI JavaScript syntax을 포함합니다.

**VERIFIED runtime** 격리 `minimal/qa_journal_118` 서버(9212/9305)에서 `/api/state`와 `/api/transactions`를 직접 조회했습니다. journal은 latest0/failure0/corrupt0/gap0/durable true였고 HTML에 `JOURNAL HEALTH`/`DEGRADED` 렌더 분기가 포함됐습니다. 검증 뒤 프로세스를 종료해 두 포트가 해제된 것도 확인했습니다.

**NOT VERIFIED browser (이번 재부팅 후)** 실제 인앱 브라우저 연결은 브라우저 플러그인 런타임이 `AppData` realpath에서 EPERM으로 시작하지 못해 화면/console 재검증을 수행하지 못했습니다. 116/117의 이전 실제 브라우저 성공 증거는 유효하지만, 118의 새 세 지표는 API·HTML·JS syntax까지만 확인됐습니다.

## 남은 작업

1. character delete를 pending manifest → committed archive로 바꾸고 시작 시 reconciliation합니다.
2. 전체 journal의 bounded disk query/export와 capture run manifest는 별도 계층으로 구현합니다.
3. 원본 클라이언트의 실제 구매/energy/삭제를 새 journal과 canonical revision/SHA까지 연결해 live 검증합니다.

Related: 102, 105, 114, 116, 117, INDEX.
