# 569 — 3D 아즈로크 홈페이지와 BoxedWine 실행 전환 복원

날짜: 2026-08-27 KST  
범위: `tools/boxedwine_local` 첫 화면, 역사적 서버 선택 단계, 기존 사설 BoxedWine 입장 계약  
원칙: 원본 게임/운영 WASM·root·app·IME·D3D9Web 실행 페이지는 수정하지 않음

## 결론

- **VERIFIED (원본 웹 계약):** 2011 IE 캐시의 로그인 상태 본문은 좌측 `233x79` `start_goTester.swf`와 `goTester()`를 보존한다. 로그인/동의 후 메인 창은 `/azrok/server.list.screen`으로 이동한다. 과거의 즉시 ActiveX 직접 실행안은 주석 처리돼 있다.
- **VERIFIED (원본 실행 계약):** 회수 JS/OCX/installer 분석은 `GAMEIP`, `GAMEID`, `GAMESESSION`을 최종 `Azrok.exe -NX 100 -NWND -PL <ID> -DIR <SESSION> -IP <IP>`로 전달한다.
- **VERIFIED (현재 등가 경계):** 현재 사설 웹 입장은 `/api/private-session`이 browser-bound v2 ticket, launcher, account를 발급하고 `index_d3d9web_pathouse.html`이 같은 named CLI 계열로 원본 실행파일을 기동한다.
- **VERIFIED (구현):** bare `/`는 이제 `azrok_home.html`을 보여 준다. `게임시작`은 `azrok_server_list.html`로 이동하고, `아즈로크 보존 광장` 접속은 기존 사설 admission을 호출한 뒤 `dynamicaccounts2_startersplash1` app과 `autorun=1`을 사용해 기존 실행 페이지로 전환한다. 이 후보는 #568에서 11개 launcher의 `-NWND`만 제거해 원본 starter 창을 보존한 패키지다.
- **SUPERSEDED (초기 구현):** 첫 구현은 HTML의 치수만 참고해 현대식 DOM/CSS를 새로 작성했으므로 “원본 HTML 복원” 요구를 충족하지 못했다. 사용자 지적 후 폐기하고 아래 원본 파생 빌드로 교체했다.
- **VERIFIED (원본 HTML 파생 구현):** `docs/research/_salvage/html/azrok_main.utf8`(2012-01-29 캡처의 CP949→UTF-8 동일문자본)을 빌드 정본으로 삼는다. Wayback loader/toolbar와 원격 tracker만 제거하고 원본 table 53개, tr 184개, td 360개, form 6개, iframe 2개, 로그인 폼, pollId 2072 설문, 공지 5개, 랭킹 10개, hidden `start_azrok` iframe을 유지한다.
- **VERIFIED (브라우저):** 실제 in-app 브라우저에서 원본 906px 퍼니또 상단 GNB, 915x305 Flash 자리, 233px 좌측 로그인/233x79 게임시작/설문, 682px 본문, 104px 우측 레일을 확인했다. 게임시작은 서버 선택 화면으로 이동한다.
- **VERIFIED (신규 전체 실행):** 같은 브라우저 탭에서 `원본 HTML 파생 홈페이지 → 서버 선택 → private-session → D3D9Web`을 실행했다. `startersplash1` ZIP을 실제 요청했고 한솔교육 splash와 첫 게임 화면 완료를 확인했다. 사용자는 그 앞의 Acknex starter가 순간이 아니라 알아볼 수 있게 표시되는 것을 직접 확인했다.

## Wayback `re_azrok` 자산 재검증

> **SUPERSEDED by 570 for the final all-range asset verdict.** 이 절의 초기 단일 패스 판정은 #570의 전 기간·raw 재검증 결과로 교체한다.

`docs/research/_salvage/re_azrok_recovery_20260827_verified/manifest.json`이 권위 결과다.

- 고유 3D 아즈로크 표적 64개
- CDX 캡처 61개: 모두 참조된 GIF/JPEG/SWF가 아니라 `text/html` 도메인 파킹 응답
- CDX 미캡처 3개: `fd_tester_banner.gif`, `main_banner.gif`, `main_banner.swf`
- 실제 회수된 홈페이지 바이너리/원본 HTML 자산: **0개**
- `azroktcg`/`images/gameplay/azroktcg` 혼입: **0개**

따라서 “61개 목록이 있으므로 그대로 다운로드 가능” 가정은 기각한다. 그러나 이것은 공통 퍼니또 자산까지 모두 없다는 뜻은 아니다. `funitto_common_recovery_20260827/manifest.json`을 새로 만들고 원본 HTML이 참조하는 비-`re_azrok` GIF 135개를 재검증했다.

- 원본 GIF로 회수·magic/Content-Type/SHA-256 검증: **69개** (초기 로컬 CDX 선별 68 + live Wayback Timegate 교정 1)
- 초기 격리 67개 중 만화 썸네일 1개를 직접 회수해 유효 격리는 **66개** (`azroktcg_menu_asset` 2 포함)
- 패키지에 포함된 TCG GIF: **0개**

회수된 69개는 원본 URL 경로를 유지한 채 로컬 페이지에 연결했다. 이 중 `azrok_thumb_10_2[114114].gif`는 로컬 CDX에는 없었지만 HTML의 정확한 Wayback URL을 직접 요청하자 `20150502105330` 캡처로 이동해 276x66 GIF를 반환했다(SHA-256 `D8E203AAB23DFEC791DED55C53ECC91403C603990C969C629DFD50A99E0F7D80`). 3D 전용 그림/SWF가 없는 자리만 원래 width/height 안에서 명시적인 placeholder로 남긴다. 915x305 `main_menu.swf` 자리는 회수된 실제 3D 스크린샷을 쓰되 “원본 SWF 미회수”를 화면에 표시한다. 스크린샷 SHA-256은 `AA5A118DFBF06A2DD93B03E2948BC045AFDEED58065973F09C7D12CC3D786476`이다.

## 변경 파일

- `tools/boxedwine_local/azrok_home.html`
- `tools/build_azrok_archive_home.py` — 보존 HTML에서 로컬 페이지를 결정적으로 생성
- `tools/boxedwine_local/azrok_legacy.css`
- `tools/boxedwine_local/azrok_legacy_restore.js`
- `tools/boxedwine_local/azrok_legacy_screenshot.html`
- `tools/boxedwine_local/azrok_legacy_assets/recovered/*` — 검증된 공통/만화 GIF 69개
- `tools/boxedwine_local/azrok_legacy_assets/original-code/*` — 회수한 원본 `common.css`와 공용 JS 5개
- `tools/boxedwine_local/azrok_server_list.html`
- `tools/boxedwine_local/azrok_launch.js`
- `tools/boxedwine_local/azrok_home_assets/azrok_dc_1.jpg`
- `tools/boxedwine_local/server.py` — bare `/`만 복원 홈페이지로 rewrite
- `tools/test_azrok_home_contract.py`
- `docs/research/_salvage/re_azrok_recovery_20260827_verified/*`
- `docs/research/_salvage/funitto_common_recovery_20260827/*`
- `docs/research/_salvage/scripts/recover_re_azrok_assets.ps1`
- `docs/research/_salvage/scripts/recover_funitto_common_assets.ps1`

## 보존한 운영 경계

- `index.html` 사설 admission landing은 구조를 보존하고 inline fallback app 값만 `startersplash1`로 맞췄다.
- `index_d3d9web_pathouse.html`은 수정하지 않았다.
- `boxedwine.upstreamjit64fn6inlineabi2korean6chat1` JS/WASM, `xim25koreanlocale2` root, currentabi1 JIT, compositionend-only IME 경로를 수정하거나 덮어쓰지 않았다. 홈페이지 실행 선택값만 #568의 `dynamicaccounts2_startersplash1` 후보로 연결했다.
- 과거 3D와 별개인 아즈로크 TCG GIF는 사용하지 않았다. 단, 2012년 3D 홈페이지 원본 설문과 퍼니또 게임 목록에 실제로 들어 있던 `아즈로크TCG` 텍스트/DOM은 역사적 캡처 내용이므로 삭제하지 않았다.
- 과거 ActiveX를 재도입하지 않고 확인된 3개 입력의 의미를 현재 account-bound admission과 named CLI로 치환했다.

## 검증

- `python tools/build_azrok_archive_home.py` 결정성 계약 — PASS
- `node --check tools/boxedwine_local/azrok_legacy_restore.js` — PASS
- `node --check tools/boxedwine_local/azrok_launch.js` — PASS
- `tools.test_azrok_home_contract + tools.test_private_browser_admission` — 22개 PASS
- 기존 private/page 계약 테스트는 프로젝트 `tools/bridge_pydeps`를 `PYTHONPATH`에 둔 전체 검증에서 다시 실행한다.

2026-08-27 #570 반영 후 `python -m unittest discover -s tools -p 'test_*.py'` **269개 전체 PASS**. 임시 HTTP 오류 객체 정리 `ResourceWarning` 두 건은 테스트가 의도적으로 만든 404/400 응답의 cleanup 경고이며 실패는 0개다.
