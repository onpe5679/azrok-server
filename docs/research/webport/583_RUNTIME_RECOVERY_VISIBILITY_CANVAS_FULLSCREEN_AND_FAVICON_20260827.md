# 583 — 실행 화면 복구 코드 가시성, 화면 맞춤/전체 화면, 패비콘

## 판정

- **VERIFIED — 복구 코드 표시/숨김:** 실행 전·실행 중 버튼명을 `복구 코드 표시 및 복사`로 통일하고 `복구 코드 숨기기`를 추가했다. 라이브 8765 실행 화면에서 코드 문자열 자체를 기록하지 않은 채 표시 후 출력/숨김 버튼이 나타나고, 숨김 후 출력 길이 0·출력 hidden·숨김 버튼 hidden으로 돌아가는 것을 확인했다. 명시적인 `복구 코드 재생성`은 누르지 않았다.
- **VERIFIED — 캔버스 맞춤 원인과 수정:** 기존 `#resize` 체크박스에는 이벤트 핸들러와 참조 코드가 없어 완전한 no-op였다. 현재는 실제 backing 크기와 남은 viewport를 기준으로 4:3 화면을 축소하고, source canvas와 D3D9Web overlay에 같은 CSS 크기를 적용한다. 1024×768 준비 화면은 510×382로 맞춰졌고, 첫 실제 게임 렌더 뒤 640×480 source/overlay를 맞춤했을 때 두 사각형의 `(x,y,w,h)` 차이는 `(0,0,0,0)`이었다. 해제하면 원래 크기로 복귀했다.
- **VERIFIED — 전체 화면 예외 원인과 수정:** 기존 버튼은 정의되지 않은 `toggleCanvasFullscreen()`을 호출해 `Exception thrown, see JavaScript console`을 만들었다. 표준 `requestFullscreen()`/`exitFullscreen()`을 쓰는 예외 처리 함수로 교체했다. 실제 버튼 클릭에서 `#dropzone`이 3840×2160 전체 화면 영역으로 들어갔고, 기존 예외 문구는 나타나지 않았다.
- **VERIFIED — 패비콘:** 프로젝트 루트의 `azrok.ico`(2,238 bytes)를 웹 루트에 동일 바이트로 복사하고 보존 홈페이지, 서버 선택, 실행 화면, 레거시 게이트에 `image/x-icon`으로 연결했다. 8765의 `/azrok.ico`는 HTTP 200과 `image/x-icon`을 반환했다.
- **VERIFIED — 회귀 검사:** `python -m unittest discover -s tools -p 'test_*.py'` 전체 **273 tests**가 통과했다.

## 변경 파일

- `tools/boxedwine_local/index_d3d9web_pathouse.html`
- `tools/boxedwine_local/azrok_server_list.html`
- `tools/boxedwine_local/azrok_home.html`
- `tools/boxedwine_local/index.html`
- `tools/boxedwine_local/azrok.ico`
- `tools/build_azrok_archive_home.py`
- `tools/test_d3d9web_page_contract.py`
- `tools/test_azrok_home_contract.py`

## 보존 경계

- 복구 코드 재생성 API와 계정별 불변 정책은 변경하지 않았다.
- BoxedWine 앱 ZIP, Wine root, D3D9Web runtime JS, 게임 바이너리는 변경하지 않았다.
