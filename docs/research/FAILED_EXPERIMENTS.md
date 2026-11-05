# 실패 실험 재도입 방지 대장

이 문서는 과거 실험 파일을 삭제하지 않고 보존하면서, 실패한 구현이 근거 없이 운영 기본값으로 다시 들어오는 일을 막기 위한 금지 목록입니다.

## FE-IME-001 — committed `compositionupdate` replacement

- **상태:** FAILED / PRODUCTION 재도입 금지
- **아티팩트:** `boxedwine.upstreamjit64fn6inlineabi2korean7preedit1`
- **관련 문서:** archive #559, rollback #563
- **직접 실패:** 실제 키보드로 `안녕`을 입력했을 때 원본 Edit에 `ㅇ안`이 남았습니다.
- **원인:** 조합 중간값 `ㅇ`, `아`, `안`을 각각 확정 문자열로 넣고 synthetic Backspace로 이전 값을 지우려 했으나, 원본 Edit가 삭제와 삽입을 동일 순서로 처리하지 않았습니다.
- **금지:** `compositionupdate`를 guest committed text로 보내지 않습니다. `boxedwine_replace_preedit_utf8`를 기본 페이지 경로에 연결하지 않습니다.

## FE-IME-002 — Wine XIM active-preedit callbacks

- **상태:** FAILED / PRODUCTION 재도입 금지
- **아티팩트:** `boxedwine.upstreamjit64fn6inlineabi2korean8preeditcallbacks1`, roots `xim30preeditcallbacks1`, `xim31preeditreentry1`
- **관련 문서:** archive #560, archive #561, rollback #562/#563
- **직접 실패:** 첫 물리 한글 조합 순간 worker가 `RangeError: Maximum call stack size exceeded`로 종료됐습니다.
- **재시도 실패:** depth guard 뒤에도 동일 예외가 재현됐고 FIFO `depth=29`, lookup=9, served=2가 측정됐습니다.
- **원인 경계:** callback 처리 중 새 composition action이 계속 생성되는 producer 순환입니다. 단순 nested lookup guard로 해결되지 않았습니다.
- **금지:** `boxedwine_ime_preedit_utf8` 또는 XIM start/draw/done callback을 일반 URL 기본 경로에 연결하지 않습니다.

## 현재 승인된 운영 경로

- runtime: `boxedwine.upstreamjit64fn6inlineabi2korean6chat1`
- root: `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1-acp949-xim25koreanlocale2`
- app: `Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2`
- 입력 정책: 브라우저 조합 중에는 guest로 보내지 않고 `compositionend`에서만 기존 `send(e.data, true)`를 호출합니다.
- 직접 수락 근거: #558에서 원본 이름 Edit의 `한글별` 표시와 확인 후 다음 화면 진입을 VERIFIED했습니다.

## 재검토 조건

아래 조건을 모두 충족하지 않으면 FE-IME-001/002를 운영 경로로 되살리지 않습니다.

1. 기존 runtime/root를 덮어쓰지 않는 새 immutable 진단 아티팩트일 것.
2. 일반 URL 기본값이 아니라 명시적 진단 URL에서만 먼저 실행할 것.
3. 실제 물리 키보드로 캐릭터 이름과 Plaza Edit 양쪽에서 `ㄱ → 가 → 간`, `안녕`, Space, Backspace, 취소를 확인할 것.
4. 중복 글자, 마지막 글자 유실, worker 예외, FIFO 누적이 모두 없어야 할 것.
5. 최소 30초 입력 반복과 새 계정 재부팅 후 재입력을 통과할 것.
6. 성공 증거 문서가 이 파일의 해당 항목을 명시적으로 SUPERSEDE하고 INDEX를 동시에 갱신할 것.

## 자동 방지

`tools/test_d3d9web_page_contract.py::test_post_1635_preedit_experiments_are_not_in_the_page`가 운영 페이지에 다음 구현이 다시 나타나면 실패합니다.

- `compositionupdate` handler
- committed-preedit 진단 변수
- XIM active-preedit 진단 변수
- `boxedwine_replace_preedit_utf8` page binding
- `boxedwine_ime_preedit_utf8` page binding
