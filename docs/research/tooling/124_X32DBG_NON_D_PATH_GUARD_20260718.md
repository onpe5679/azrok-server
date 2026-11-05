# x32dbg D 드라이브 접근 차단과 경로 가드 (2026-07-18)

## 결론

- **VERIFIED (code/test):** `tools/x32dbg_000d_trace.py`, `x32dbg_plaza_interaction_trace.py`, `x32dbg_hang_snapshot.py`, `stop_azrok_elevated.ps1`에 남아 있던 `D:\x64dbg\x32\x32dbg.exe` 하드코딩을 제거했습니다.
- **VERIFIED:** resolver는 `AZROK_X32DBG_PATH`와 B:/workspace/C: 후보만 검사하며 D:로 해석되는 설정은 파일 존재 검사 전에 건너뜁니다.
- **VERIFIED:** 비-D configured path 선택 및 D path 미탐색 회귀 2개를 추가해 전체 **177 tests OK**, `py_compile` PASS입니다.
- **NOT VERIFIED / BLOCKED EXTERNAL:** 현재 B:/workspace/C: 후보에는 x32dbg.exe가 발견되지 않았습니다. 사용자가 x32dbg를 비-D 경로로 옮기거나 `AZROK_X32DBG_PATH`를 설정하기 전에는 x32dbg 동적 트랙이 명확한 오류로 fail-closed합니다.

Ghidra는 기존 지시대로 B: 인스턴스를 사용하며 D:는 조사·검색·존재 검사 대상에서도 제외합니다. x32dbg가 다시 배치될 때까지 동적 분석은 구조화 packet capture와 원본 클라이언트 실플레이를 병행하고, 정적 분석은 B: Ghidra를 사용합니다.

관련 권위: INDEX, 121, 123.
