# 562. XIM active-preedit callback production rollback (2026-08-08)

## VERIFIED

- xim31 물리 입력에서도 worker `Maximum call stack size exceeded`가 재현됐습니다.
- 실패 직후 계측은 FIFO `depth=29`, Xmb lookup=9, callback served=2였습니다. 단순 동일 lookup 재진입이 아니라 callback 처리 중 producer가 새 action을 계속 쌓는 순환입니다.
- korean8 callback 처리는 `liveXimPreeditCallbacks=1` 명시 진단에서만 활성화되도록 격리했습니다.
- 기본 runtime/root를 실제 원본 이름 Edit에서 `한글별` 표시와 다음 화면 진입까지 수락된 korean6+xim25로 복구했습니다.
- focused page/XIM 계약 42 tests가 통과했습니다.

## NOT VERIFIED

- 복구 기본값으로 새로 부팅한 사용자 세션에서 worker 예외가 사라졌는지 재수락.
- 마지막 활성 조합 글자를 게임 Edit 안에서 즉시 표시하는 자연스러운 preedit UX. 이 개선은 guest callback을 다시 기본 활성화하지 않고 브라우저 조합 UI 또는 안전한 composition 종료 정책으로 별도 구현해야 합니다.
