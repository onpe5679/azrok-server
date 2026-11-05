# azrok_server.py 소스 손실 정확 복구 (2026-07-18)

표기: **VERIFIED artifact**=보존 파일 해시/헤더/코드 객체 직접 비교, **VERIFIED test**=실행 회귀, **VERIFIED runtime**=기존 서버 상태 비침습 조회.

## 결론

에이전트의 실패한 대형 패치 도중 `azrok_server.py`가 0바이트가 됐습니다. 실행 중인 서버는 이미 import한 코드를 유지했으므로 종료하지 않았고, 최신 CPython 3.11 bytecode와 로컬 source history 및 성공한 Codex `apply_patch` 기록으로 별도 후보를 재구성한 뒤 원본을 복원했습니다.

복원된 `azrok_server.py`는 **416,839 bytes**, SHA256 `3009D9E4611720FE8DFC67D692CF545E9EE64EED456CCCA5096D579DC26E4327`입니다.

## 1. 보존 증거

- **VERIFIED artifact** 손실 전 `__pycache__/azrok_server.cpython-311.pyc`를 `artifacts/dynamic-analysis/azrok_server_pre_loss_131tests.cpython-311.pyc`로 먼저 복사했습니다.
- 크기 `482,210 bytes`, SHA256 `E57377F7D9A8FB609B77BE64B484F5F07AFCF1E171FD148929625FA859FA6013`입니다.
- pyc header는 timestamp-based CPython 3.11이고 embedded source size는 정확히 `416,839`입니다.
- Claude source-history v33은 `395,531 bytes`, SHA256 `18CEFA692FAF82BFCE5F6C8D05AC4093A2FA9B5089533F453D21D1D93093739D`로 더 오래된 기준본입니다.

## 2. 복구 방법

1. v33을 `azrok_server.recovery.py`로 복사했습니다.
2. 2026-07-18 Codex rollout JSONL에서 성공한 `azrok_server.py` Update 패치만 시간 순서로 추출했습니다.
3. snapshot에 이미 포함된 첫 패치는 중복 적용하지 않았습니다.
4. 한글 주석 인코딩 문맥이 다른 두 패치는 코드 문맥만 남긴 최소 Update로 동일 변경을 적용했습니다.
5. pyc source mtime의 초 경계 뒤 `0.100s`에 기록돼 처음 누락된 `S2C 0x0007 +0x1AC..+0x1D3 = FF×40` 패치를 호출 ID `call_UJrJZR977xtho397g2FZI9OG`로 정확히 추가했습니다.
6. 검증된 후보를 원본 위치에 복사했습니다.

복구 보조 스크립트는 Windows Store Codex의 `apply_patch` 실행 권한 때문에 자동 재생에 직접 사용하지 않았습니다. 또한 Add/Delete 허용, 초 단위 시간 경계, 병렬 완료 순서 등 감사에서 확인된 위험 때문에 최종 복구는 호출별 Update-only 재생과 코드 객체 검증으로 제한했습니다.

## 3. 정확성 검증

- **VERIFIED artifact** 후보 크기 `416,839 == pyc embedded source size`.
- `compile(candidate_bytes, 'azrok_server.py', 'exec', dont_inherit=True, optimize=0)` 결과와 보존 pyc payload를 `co_consts` index path로 재귀 비교했습니다.
- 모듈과 중첩 함수/람다/comprehension을 포함한 코드 객체 **315개**에서 다음 필드를 비교했습니다: bytecode, 일반 상수, names/varnames/freevars/cellvars, flags/stack/args, first line, line table, exception table.
- mismatch **0건**입니다.
- **VERIFIED test** `python -m py_compile azrok_server.py` 성공.
- C: 여유 공간 0으로 첫 회귀 실행은 임시 파일 생성에서만 실패했습니다. `TEMP/TMP=B:\Azrok_TestTemp`로 옮긴 같은 명령 `python -m unittest discover -s tools -p 'test_*.py' -q`는 **131 tests PASS**입니다.

## 4. 런타임 보존

- **VERIFIED runtime** 복구 중 TCP9207/control9300, TCP9208/control9301, TCP9209/control9303 서버를 종료하지 않았습니다.
- 감사 시점에 9207은 client 1, 9208은 client 2, 9209는 대기 0으로 모두 control API HTTP 200과 heartbeat를 유지했습니다.
- 실행 서버는 손실 전 import된 코드를 계속 사용하므로, 소스 복구가 라이브 세션을 변형하지 않았습니다.

## 후속 안전 규칙

> **2026-07-18 follow-up (116):** 사용자가 C: 여유 공간을 확보했고 27.79GB free에서 기본 TEMP 전체 133 tests가 통과했습니다. 아래 B: TEMP 규칙은 복구 당시의 임시 우회 기록입니다.

- 대형 패치는 한 파일에 한 번에 적용하지 않고 작은 Update와 즉시 compile/test로 나눕니다.
- 복구 후보나 generated artifact는 원본 경로와 분리합니다.
- 전체 회귀는 C: 공간이 복구될 때까지 `B:\Azrok_TestTemp`를 사용합니다.
- 실행 중인 9207/9208 세션은 에너지/액세서리 후속 실측을 위해 계속 보존합니다.

Related: 84, 105, 108, 109, 112, 113, 114, INDEX.
