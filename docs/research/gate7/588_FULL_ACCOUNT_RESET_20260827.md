# 588 — 브라우저 보존 계정 완전 초기화

날짜: 2026-08-27

## 사용자 의미

홈페이지 하단의 `계정 완전 초기화`는 단순 로그아웃이나 복구코드 회전이 아니다. 캐릭터·인벤토리·퀘스트 진행도를 비운 새 동적 계정을 발급해 해당 브라우저를 최초 접속 상태로 되돌린다.

## 구현

- **VERIFIED:** 홈페이지 하단에 별도 `보존 계정 관리` 상자와 `계정 완전 초기화` 버튼을 추가했다.
- **VERIFIED:** 브라우저 확인창 뒤 사용자가 `초기화`를 직접 입력해야 POST가 전송된다.
- **VERIFIED:** 서버는 대상 계정이 접속 중이면 409로 거부한다.
- **VERIFIED:** 계정별 canonical/binary/legacy 저장본을 삭제하지 않고 `server_state/reset_accounts/<account>_<timestamp>/`로 원자적으로 이동한다. 중간 실패 시 이미 옮긴 파일을 복귀시킨다.
- **VERIFIED:** 기존 계정의 모든 브라우저 결합과 registry 레코드를 제거해 구 복구코드를 폐기하고, 요청 브라우저에는 새 계정 식별자를 결합한다.
- **VERIFIED:** 현재 실행 중인 구 코어를 즉시 재시작하지 않아도 웹 프런트엔드가 overview 기반 호환 보관 경로를 수행한다. 다음 자연스러운 코어 재시작 뒤에는 `AzrokServer.reset_preserved_account_state()`가 직접 수행한다.

## 실측

- **VERIFIED:** 폐기용 브라우저 식별자에서 초기 계정 `aqHpHqBNDAUFT`를 새 계정 `aufqrH2xBcFmL`로 교체했다.
- **VERIFIED:** 교체 뒤 동일 브라우저의 session API는 새 계정을 반환했다.
- **VERIFIED:** 다른 폐기용 브라우저가 구 복구코드를 사용한 복구 요청은 HTTP 403으로 거부됐다.
- **VERIFIED:** 실제 `http://127.0.0.1:8765/`을 새로 불러와 페이지 하단 상자와 버튼 노출을 시각 확인했다. 사용자 실제 계정에서는 파괴적 클릭을 수행하지 않았다.

## 회귀 검증

- `node --check tools/boxedwine_local/azrok_legacy_restore.js`
- `python -m unittest discover -s tools -p 'test_*.py'`
- **VERIFIED:** 282 tests, OK.

