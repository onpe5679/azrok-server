# 570 — 아즈로크 홈페이지 자산 Wayback 전 기간 재검증

날짜: 2026-08-27 KST  
범위: 2012 원본 HTML의 미회수 공통 자산, `images/re_azrok/` 3D 전용 자산, 관련 CSS/JS/SWF와 서버 선택 경로  
원칙: 확장자·로컬 CDX만으로 단정하지 않고 live CDX/Availability/TimeMap/TimeGate와 raw `id_` 응답 바이트를 교차 검증

## 결론

- **VERIFIED — 공통 누락 자산:** 비-`re_azrok` 후보 65개를 2005-2020 연도별 기준일과 2012 원본 시각으로 세 차례 조회하고, 공통 실패만 재시도한 뒤 마지막 10건을 개별 확인했다. Availability 3,492건과 exact CDX 221건의 최종 합성 결과는 정상 바이너리 **1개**, 유효 캡처 없음 **64개**, 미확정 **0개**다.
- **VERIFIED — 만화 썸네일:** `azrok_thumb_10_2[114114].gif`는 로컬 CDX에 없었지만 live Timegate가 `20150502105330` 캡처를 반환했다. GIF89a, 12,359바이트, 276x66, SHA-256 `D8E203AAB23DFEC791DED55C53ECC91403C603990C969C629DFD50A99E0F7D80`이다.
- **VERIFIED — 3D `re_azrok`:** 비-TCG 표적 64개 중 61개 URL에서 전 기간 고유 캡처 154건을 열거했다. 범위는 `2014-12-20`부터 `2024-08-12`로 모두 후대 캡처다. raw 재생을 세 차례 수행하고 마지막 6개 고유 digest를 개별 요청한 결과, 정상 이미지/SWF **0개**, 파킹 HTML **154개**, 미확정 **0개**다. 132건은 raw 바이트로 직접 확인했고 22건은 직접 확인된 파킹 본문과 Wayback CDX digest가 동일하다.
- **VERIFIED — 관련 원본 코드:** `common.css`와 공용 JS 5개(`common.js`, `menuLink.js`, `objectWrite.js`, `parent_menu.js`, `selectbox.js`)를 2013 캡처에서 정상 CSS/JavaScript로 회수해 SHA-256으로 고정했다. `menuLink.js`는 `/azrok/preop.screen` 및 같은 창의 `/azrok/server.list.screen` 분기를, `objectWrite.js`는 JSStarter/PlazaStarter CAB 실행 세대를 보존한다.
- **VERIFIED — SWF 음성 결과:** `main_menu.swf`, `main_bn_preop.swf`, `main_banner.swf`, `right_banner_movie.swf`, `start_goTester.swf`에서 유효 `FWS/CWS/ZWS` 본문은 회수되지 않았다. 현재 발견된 후대 응답은 파킹 HTML이다.
- **NOT VERIFIED — 서버 목록 화면 본문:** 원본 HTML과 회수 JS로 별도 `server.list.screen` 라우트 및 same-window 이동은 확정됐지만, 서버 목록 페이지 자체의 정상 HTML 캡처는 local CDX 0행이고 live route probe가 Wayback 장애로 완료되지 않아 원본 시각 DOM은 미회수다.

## 홈페이지 반영

- 기존 검증 GIF 68개와 새 만화 썸네일 1개, 총 69개를 원본 URL 경로로 패키징했다.
- 회수한 원본 `common.css`를 보완 CSS보다 먼저 실제 적용한다.
- 공용 JS 5개는 원본 코드 보존본으로 패키징하되, 종료된 로그인·ActiveX 호출이 현재 페이지를 방해하지 않도록 직접 실행하지 않는다.
- 실제 브라우저에서 이미지 요소 118/118 로드, 만화 썸네일 276x66, 원본 CSS와 보완 CSS 두 스타일시트 로드를 확인했다.
- 3D 전용 SWF/이미지는 회수되지 않았으므로 해당 원본 치수 영역은 복원 라벨 또는 실제 3D 인게임 스크린샷 기반 명시적 대체 영역으로 유지한다.
- `azroktcg` 이미지와 `sub_02game02*`는 패키지에 포함하지 않았다.

## 증거 산출물

- `docs/research/_salvage/funitto_common_fullscan_final_20260827/`
- `docs/research/_salvage/re_azrok_fullscan_final_20260827/`
- `docs/research/_salvage/azrok_related_discovery_20260827/`
- `docs/research/_salvage/funitto_common_fullscan_{20260827,slowretry2_20260827,slowretry3_20260827,merged_20260827}/`
- `docs/research/_salvage/re_azrok_{fullscan_20260827,raw_replay_20260827,raw_replay_retry2_20260827,raw_replay_retry3_20260827}/`
- 재실행 스크립트: `fullscan_funitto_common_wayback.py`, `merge_retry_funitto_fullscan.py`, `fullscan_re_azrok_wayback.ps1`, `retry_reazrok_raw_replays.py`

## 검증

- `python -m py_compile` — 신규 Python 스캐너 3개 PASS
- `python tools/build_azrok_archive_home.py` — 결정적 재빌드 PASS
- `python -m unittest discover -s tools -p 'test_*.py'` — 269개 PASS
- in-app browser — 원본 `common.css`, 보완 CSS, 118개 이미지, 276x66 만화 썸네일, 게임시작 버튼 PASS
