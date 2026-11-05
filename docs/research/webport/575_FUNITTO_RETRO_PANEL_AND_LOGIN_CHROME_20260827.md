# 575 — 퍼니또식 복고 패널 제목띠와 로그인 UI

날짜: 2026-08-27 KST  
범위: 원본 HTML 파생 홈페이지의 제목/로그인/설문 외곽 표현

## 근거

- **VERIFIED — 보존 페이지:** `docs/research/_salvage/html/fj_intro.html`은 2011-10-02 웨이백 캡처, `evlist.html`·`noticelist.html`·`cust.html`은 2012-06-10 웨이백 캡처다.
- **VERIFIED — 반복 특징:** 해당 HTML과 사용자가 제공한 퍼니또 화면은 고정폭 table, 11~12px Dotum, 주황색 탭/버튼, 하늘색 로그인·좌측 상자, 연두색 보조 상자, 흰색/연크림 내용판, 1px 분리선을 반복한다.
- **NOT VERIFIED — 개별 아즈로크 제목 GIF:** 원본 `body_main_*_tit.gif` 파일은 여전히 미회수이므로 이번 색 배치는 퍼니또 공통 디자인 문법을 적용한 복원 해석이며, 해당 네 GIF의 픽셀 단위 복제라고 주장하지 않는다.

## 구현

- **VERIFIED — 제목띠:** 공지사항은 주황, 만화 아즈로크는 하늘, 랭킹은 황주황, 베스트 스크린샷은 연두의 45px 이미지형 제목띠로 표현했다. 1px 외곽선, 위쪽 하이라이트, 아래쪽 음영, 작은 둥근 모서리를 사용했다.
- **VERIFIED — 로그인:** 원본 `left_login_bg.gif` 셀에 `회원 로그인 / FuniTTo MEMBER` 하늘색 제목띠를 동적으로 추가했다. 입력칸은 흰색+하늘색 테두리, 로그인 버튼은 주황 그라데이션으로 복원했다.
- **VERIFIED — 설문/내용판:** 퍼니한표 제목은 하늘색 상자로, 중앙 내용판은 흰색/연크림과 얇은 베이지 테두리로 정리했다.
- **VERIFIED — 구조 경계:** 정적 `azrok_main.utf8` 기반의 53-table DOM, 공지/랭킹 데이터, 만화/스크린샷 이미지, 게임시작·서버 선택·D3D9Web 경로는 변경하지 않았다.

## 브라우저 실측

- 네 제목띠는 각각 원본 폭 338/289px와 높이 45px를 유지했다.
- 로그인 상자는 233px 폭, 추가 제목띠는 약 231x27px로 표시됐다.
- 홈페이지 이미지 로드 실패는 0개였다.

## 검증

- `python tools/build_azrok_archive_home.py`
- `node --check tools/boxedwine_local/azrok_legacy_restore.js`
- `python -m unittest discover -s tools -p 'test_*.py'`
- in-app browser 데스크톱 시각 검증

