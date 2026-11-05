# 568 — Acknex starter window 보존과 drawn-Present 전환

## 요청 경계

대상은 BoxedWine 파란 화면 뒤, 한솔교육 로고가 나오는 메인 게임창보다 앞서 표시되는 **별도 Acknex 엔진 starter 창**이다. `logo.bmp`의 CrazyDiamond 화면과 한솔교육 이후 메인 D3D 화면은 대상이 아니다.

## 확정 사실

- **VERIFIED (static/decompile):** `acknex.dll`의 `engine_open`은 `acknex_mainwin` 클래스로 별도 Win32 창을 만들고, private message `0x150E`에서 starter model을 붙인다. `WM_PAINT`는 GDI `FillRect`/`SetDIBitsToDevice` 경로로 그린다. 따라서 이 창은 D3D9Web canvas가 아니라 BoxedWine SDL/Wine source canvas에 먼저 나타난다.
- **VERIFIED (static):** Acknex CLI의 `-NWND`는 windowed-mode 옵션이 아니라 초기 starter 창을 숨기는 옵션이다(`#263`). 기존 production ZIP의 11개 `run_azrok*.bat` 모두 이 옵션을 포함했다.
- **VERIFIED (original-media inventory):** 2011 원본 설치 디렉터리에도 `acknex.wdf`는 없었다. 따라서 WDF 부재를 웹 패키징 회귀로 볼 수 없고, 원본도 엔진 내장 starter model을 사용한 경로가 성립한다.
- **VERIFIED (dynamic/browser):** 기존 renderer는 실제 draw가 없는 초기 `Clear -> Present`에서 overlay를 표시했다. 수정 전 격리 실행은 빈 첫 Present에서 `d3d9webFirstPresent=1`과 검정 output을 보였다.
- **VERIFIED (dynamic/browser):** renderer를 draw 포함 Present로 제한한 뒤 동일 실행은 초기 빈 Present 세 번 동안 overlay가 숨겨졌고, 첫 geometry 포함 Present가 `4`일 때 output overlay가 표시됐다. 이후 메인 게임 출력은 정상 진행했다.
- **VERIFIED (user visual observation):** `-NWND`만 제거한 immutable 후보 ZIP 실행에서 목표 Acknex starter 화면이 순간적으로 보였다. 이는 launcher 억제 해제가 올바른 축임을 확인한다.

## 수정

1. `d3d9web-runtime.js`
   - `frameHasDraw`와 `overlayHasPresentedDraw` latch를 추가했다.
   - clear-only Present는 WebGL overlay를 계속 숨긴다.
   - `DRAW_PRIMITIVE_UP` 또는 `DRAW_INDEXED`가 포함된 첫 Present에서만 overlay를 표시하고 first-present 신호를 발행한다.
2. `index_d3d9web_pathouse.html`
   - 부팅 상태 카드를 중앙에서 우하단으로 옮겨 starter 내용을 가리지 않게 했다.
   - source canvas의 밝고 색상 변화가 있는 네이티브 starter 프레임을 RAF에서 포착해 `#acknex-starter-hold`에 보존한다.
   - hold canvas는 source 위(z=1), D3D output 아래(z=2)에 두고 첫 drawn Present에서 해제한다.
3. `build_acknex_starter_app.py`
   - 원본 바이너리와 자산은 바꾸지 않고 11개 Azrok launcher의 `-NWND` 토큰만 제거한 immutable 패키지를 만든다.
   - 후보 stem: `Azrok_D3D9Web_pathouse_guestprofiles6_rsdefaults1_utf8ime2_dynamicaccounts2_startersplash1`

## 검증

- **VERIFIED:** `node --check tools/boxedwine_local/web_backend/host/d3d9web-runtime.js`
- **VERIFIED:** focused contract test 6/6 통과.
- **VERIFIED:** candidate ZIP에서 11개 launcher가 변경됐으며 `Azrok.exe`, `acknex.dll`, `Title.bmp`, `BL.tga` 등 다른 member payload는 builder 계약상 그대로 보존된다.
- **VERIFIED:** candidate ZIP SHA-256 `171CAD7371967E7FA35462957CD4A3AC4D1D471CF07E66333A1C1F0873205F61`.
- **VERIFIED (user visual, 2026-08-27):** 홈페이지의 실제 게임시작→서버선택 경로에서 `startersplash1` app이 요청됐고, 사용자가 Acknex 로딩 화면이 알아볼 수 있게 표시된 뒤 한솔 화면으로 정상 전환되는 것을 확인했다.
- **VERIFIED (route/browser):** `azrok_launch.js`와 legacy `index.html` fallback 모두 새 candidate stem을 사용한다. 브라우저 요청 로그도 `...dynamicaccounts2_startersplash1.zip` 200을 기록했다.

## 롤백 경계

- 원본 production ZIP `9357FA9499D3981CFDA00FD4A2F0EDBB7D012E1F38C6706AC74FBE453774CB9B`는 수정하지 않았다.
- candidate ZIP은 별도 파일이므로 app stem을 원래 값으로 되돌리면 launcher 변경을 즉시 롤백할 수 있다.
- 메인 D3D 렌더링은 첫 geometry Present 이후 기존 경로를 그대로 사용한다.
