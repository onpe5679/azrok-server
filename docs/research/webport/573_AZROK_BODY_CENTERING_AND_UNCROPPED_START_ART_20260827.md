# 573 — 상단바 제외 본체 중앙 정렬과 게임시작/우측 배경 비크롭 보정

날짜: 2026-08-27 KST  
범위: 원본 HTML 파생 홈페이지의 배치 보정

## 결론

- **VERIFIED — 중앙 정렬 범위:** 사용자 피드백에서 “가운데 정렬”은 메인 배너 로고가 아니라 퍼니또 상단바 아래 사이트 본체 전체를 뜻했다. 최상위 두 번째 행의 본체 table만 1019px로 고정하고 좌우 `auto` margin을 적용했다. 상단바는 계속 전체 폭이다.
- **VERIFIED — 메인 로고:** 915x305 배너 내부의 로고 중앙 정렬을 취소했다. 약 25% 축소한 216x170 크기는 유지하고 원래 좌측 여백 42px 위치로 복귀했다.
- **VERIFIED — 게임시작:** 링크 슬롯을 233x106에서 233x154로 늘리고 191x152 GIF의 `translateY(-25px)`를 제거했다. 실제 브라우저에서 GIF 상하 전체가 슬롯 안에 표시됐다.
- **VERIFIED — 우측 배경:** `azrok_bg03.jpg`의 좌측 페이드에 더해 상단 56px 하늘색 페이드를 겹쳐, 상단바 아래에서 이미지가 직선으로 잘린 것처럼 보이던 경계를 제거했다. 서버 선택 및 실행 외곽에도 같은 원칙을 적용했다.

## 브라우저 실측

- 1101px viewport에서 본체 바깥 경계는 x=37.8부터 x=1063.1까지로 좌우 중앙 정렬됐다.
- 메인 hero는 x=37.8, 로고는 x=79.8로 본체 기준 약 42px 왼쪽 위치다.
- 게임시작 링크는 233x154, 내부 GIF는 191x152이며 변환값은 없다.
- 로드 실패 이미지는 0개다.

## 검증

- `python tools/build_azrok_archive_home.py`
- `node --check tools/boxedwine_local/azrok_legacy_restore.js`
- `python -m unittest discover -s tools -p 'test_*.py'`
- in-app browser 데스크톱 시각 검증

