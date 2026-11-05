# 571 — 아즈로크 로딩 로고와 게임시작 이미지 대체

날짜: 2026-08-27 KST  
범위: 원본 HTML 파생 홈페이지의 미회수 `main_menu.swf` 영역, `start_goTester.swf` 영역, 보존 서버 선택 화면 헤더

## 결론

- **VERIFIED — 로고 원본:** `_Converted_TGA/Data/Game/Loading1.png`는 312x246 PNG이며 SHA-256은 `1001DA7542F6984058CCCDC3E19E2B3B47D62D6797D2096B98093FDE487E6F4F`이다.
- **VERIFIED — 게임시작 원본:** `docs/research/_salvage/web_images/azrok_main_gamestart04.gif`는 261x208, 16-frame GIF이며 SHA-256은 `57A19B7FD324B8D653EF2E182EBFB44B8553B394A5F4275C456B5E0B8E96A3E0`이다.
- **VERIFIED — 메인 배너:** 미회수 `main_menu.swf`의 915x305 영역은 기존 실제 인게임 스크린샷 배경을 유지하고, 텍스트로 합성했던 `AZROK/아즈로크` 대신 `Loading1.png`를 287x226 비율 유지 이미지로 표시한다.
- **VERIFIED — 게임시작:** 미회수 `start_goTester.swf`의 원본 233x79 슬롯과 `azrok_server_list.html` 링크를 유지하면서 16-frame `azrok_main_gamestart04.gif`를 표시한다. 원본 캔버스의 세로 여백은 슬롯 내부 overflow로 잘라 왜곡을 피했다.
- **VERIFIED — 서버 선택:** 텍스트 `AZROK` 로고를 같은 `Loading1.png` 이미지로 교체하고 142x112로 표시한다. 서버 선택·접속 버튼과 BoxedWine 전환 계약은 변경하지 않았다.
- **VERIFIED — 브라우저:** 메인 로고 312x246 natural / 287x226 rendered, 게임시작 261x208 natural / 125x100 rendered, 서버 로고 312x246 natural / 142x112 rendered를 실제 in-app browser에서 확인했다. 모든 페이지 이미지가 로드됐다.

## 구현 경계

- `tools/build_azrok_archive_home.py`가 두 원본 파일을 `tools/boxedwine_local/azrok_home_assets/`로 결정적으로 복사한다.
- 홈페이지는 `azrok_legacy_restore.js?v=archive3`, `azrok_legacy.css?v=archive3`을 사용한다.
- 서버 선택 페이지는 `azrok_home.css?v=restore2`를 사용한다.
- `index_d3d9web_pathouse.html`, D3D9Web runtime, app ZIP, launcher, private admission 로직은 수정하지 않았다.

## 검증

- `python tools/build_azrok_archive_home.py` — PASS
- `node --check tools/boxedwine_local/azrok_legacy_restore.js` — PASS
- `python -m unittest tools.test_azrok_home_contract` — PASS
- 실제 홈페이지 및 서버 선택 화면 브라우저 시각 검증 — PASS
