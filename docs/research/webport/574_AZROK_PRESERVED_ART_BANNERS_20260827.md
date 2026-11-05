# 574 — 보존 원본 아트 기반 메인/가이드/출석 배너

날짜: 2026-08-27 KST  
범위: 원본 HTML 파생 홈페이지의 미회수 Flash/GIF 대체 표현

## 결론

- **VERIFIED — 메인 배너:** 1024x768 `_Converted_WIS/Data/Common/MainLoading.png`(SHA-256 `4767FCE248EEF18BBEBE8921143DD95609AE1431C0E344E582FC9C8A9EC4FD6D`)를 915x305 `main_menu.swf` 대체 영역에 적용했다. `cover`와 중앙 45% 위치로 상·하단 문구/로고를 제외하고 중앙 캐릭터 장면을 사용한다. 별도 216x170 로고는 기존 좌측 42px 위치를 유지한다.
- **VERIFIED — 게임시작 여백:** 191x152 GIF를 233x154 슬롯 안에서 `translateY(-15px)`로 보정했다. 실제 브라우저에서 불투명 그림 기준 위 약 16px, 아래 약 22px로 균형을 맞췄다.
- **VERIFIED — 초보자 가이드:** 800x622 `docs/research/_salvage/screenshots/azrok_dc_2.jpg`(SHA-256 `39307DC383FDDCF619DAA18CF823E4583F30A375E3BBE327DB0D0F35E00E0DDB`)를 343x95 가이드 배경으로 사용했다. 숲 장면 위에 녹색 음영과 `AZROK GAME GUIDE`/`아즈로크 초보자 가이드` 제목을 겹쳤다.
- **VERIFIED — 출석도장:** 95x95 `Mouse2_0.png`(SHA-256 `BE911DD4E3F1BB3A6343DAA921DEBB35AB9FC39E75B516D874CDCABDBBB4CB03`)와 250x234 `NPC_02.png`(SHA-256 `01998B16981FCCE31A963C96EAB5141770F293AF8C4EA2AC58177B068508427B`)를 289x95 배너에 함께 적용했다. 고양이 NPC를 오른쪽 중심 캐릭터, 지팡이를 뒤쪽 장식으로 두고 크림·주황색 문구 영역을 확보했다.
- **VERIFIED — 보존 빌드:** 빌더가 네 자산을 `azrok_home_assets`에 결정적으로 복사한다. 원본 HTML table 구조, 서버 선택 링크, D3D9Web/runtime/launcher는 변경하지 않았다.

## 브라우저 검증

- 새 배너 3종의 CSS 배경 URL이 모두 로드됐다.
- 홈페이지 이미지 로드 실패는 0개였다.
- 가이드 343x95, 출석도장 289x95, 게임시작 233x154를 실측했다.

## 검증

- `python tools/build_azrok_archive_home.py`
- `node --check tools/boxedwine_local/azrok_legacy_restore.js`
- `python -m unittest discover -s tools -p 'test_*.py'`
- in-app browser 데스크톱 시각 검증

