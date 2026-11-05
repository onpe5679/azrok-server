# 572 — 원본 HTML 공백 보정과 퍼니또 계열 실행 화면 통일

> **PARTIALLY SUPERSEDED by 573.** 본체/로고 중앙 정렬 범위, 게임시작 슬롯 높이, `azrok_bg03.jpg` 상단 경계는 #573의 사용자 확인 보정이 최신이다.

날짜: 2026-08-27 KST  
범위: 원본 HTML 파생 홈페이지, 서버 선택 화면, D3D9Web 실행 페이지의 외곽 표현

## 결론

- **VERIFIED — 원본 구조 유지:** 홈페이지는 `azrok_main.utf8`의 53개 table DOM을 계속 정본으로 사용한다. 공지·만화 제목 사이의 비정상 공백은 미회수 `body_main_mwa_tit.gif` 대체 span이 원본 `height=100%` 제목 table을 289px로 늘린 결과였고, 해당 제목 table만 45px로 고정해 공지 목록과 만화 카드가 바로 이어지게 했다.
- **VERIFIED — 하단 배너:** 크기가 기록되지 않은 미회수 `main_banner.gif`가 1.8x1.8px 대체물로 축소되어 95px 행 대부분이 공백이었다. 원본 주석의 343x96 SWF 자리와 짝 패널 289x95를 근거로 대체물을 343x95로 보정했다.
- **VERIFIED — 요청 이미지:** 442x570 `azrok_bg03.jpg`(SHA-256 `42792066ADA86B78571100FF90FC5BEEC259EE58B4EE20AD902C2132F492261A`)를 빌더가 결정적으로 복사한다. 원본 전체를 우측 장식층에 두고 왼쪽 가장자리를 투명 페이드 처리했으며, 중앙·좌측은 같은 하늘색에서 하단 흰색으로 이어지는 CSS 그라데이션으로 확장했다. 좁은 원본 우측 셀에 이미지를 강제 크롭하는 방식은 사용하지 않았다.
- **SUPERSEDED by 573 — 요청 크기:** 216x170 축소 크기와 191x152 GIF 크기는 유지되지만, 로고 중앙 배치와 게임시작 슬롯 크롭은 #573에서 각각 원래 좌측 위치와 비크롭 233x154 슬롯으로 보정됐다.
- **VERIFIED — 퍼니또 디자인 근거:** 보존된 2011 `fj_intro.html`과 2012 `evlist.html`, `noticelist.html`, `cust.html`은 작은 Dotum 글꼴, 고정폭 table, 이미지형 제목/버튼, 흰색·연크림 내용판, 주황색 강조와 얇은 테두리를 반복한다. 실행 페이지 외곽을 이 특징에 맞춰 주황 상단띠, 크림 상태판, 녹색 강조, 흰/금색 게임 프레임으로 통일했다.
- **VERIFIED — 런타임 경계:** `index_d3d9web_pathouse.html`의 외곽 CSS와 정적 헤더 문구만 변경했다. canvas ID/크기 규칙, Acknex starter hold/release, Present 판정, D3D9Web runtime, IME, launcher, app ZIP, private admission은 변경하지 않았다.

## 브라우저 실측

- 공지 제목 338x45 / 만화 제목 289x45로 같은 행에서 일치했다.
- 초보자 가이드 343x95 / 출석도장 289x95로 같은 행에서 일치했다.
- 메인 로고 216x170, 게임시작 링크 233x106, 그 안 GIF 191x152로 표시되었다.
- 홈페이지 이미지 로드 실패는 0개였다.
- 실제 홈페이지 게임시작 → 서버 선택 → 접속 버튼 경로로 실행했으며 39초에 첫 게임 화면 표시 완료 상태와 한솔교육 프레임을 확인했다. 게임 canvas는 1024x768을 유지했고 새 주황/크림 외곽 프레임 안에 표시됐다.

## 검증

- `python tools/build_azrok_archive_home.py`
- `node --check tools/boxedwine_local/azrok_legacy_restore.js`
- `python -m unittest tools.test_azrok_home_contract tools.test_d3d9web_page_contract tools.test_boot_splash_visibility`
- in-app browser 데스크톱 시각 검증
