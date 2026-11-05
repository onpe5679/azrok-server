# Gate 6 — 브라우저 절대 포인터 좌표 이중 확대 제거 (2026-07-22)

## 결론

- **VERIFIED (DOM/runtime):** SDL 원본 캔버스는 backing `640x480`, CSS `1024x768`이고 D3D9Web overlay는 backing/CSS 모두 `1024x768`이다.
- **VERIFIED (source):** Emscripten SDL2의 mouse event 경로가 CSS target 좌표를 SDL logical window 좌표로 이미 변환한다. BoxedWine의 `BOXEDWINE_D3D9WEB_FIXED_INPUT_1024X768` 보정은 같은 좌표를 다시 `640x480 -> 1024x768`로 확대한 이중 보정이었다.
- **VERIFIED (browser trace):** 수정 전 canvas-local `(800,600)` 이동은 `raw=800,600 mapped=1280,960`이었고, 수정 후 같은 입력은 `raw=800,600 mapped=800,600`이었다.
- **VERIFIED (visible input):** 수정본에서 게임 커서 hotspot이 실제 포인터 위치와 일치했고, 화면 좌하단의 실제 `접속` 버튼을 눌러 정상 PatHouse로 진입했다. 우하단으로 갈수록 오차가 커지던 현상은 재현되지 않았다.

## 수정

`C:\bwujit\platform\sdl\knativeinputSDL.cpp`에서 D3D9Web 전용 수동 절대좌표 확대와 설정 함수를 제거했다. Azrok JIT/JIT-audio/no-JIT 빌드의 `BOXEDWINE_D3D9WEB_FIXED_INPUT_1024X768` 정의도 제거했다. 상대 포인터 잠금 경로는 문서 251의 별도 게이트이며 이번 절대좌표 수정과 섞지 않았다.

검증 자산:

- `boxedwine.upstreamjit7inputfix.js`: `D3409D83FED1CB7879F932EE9CA34C7C34FEAEB41030DDE93F1A85F72F16138E`
- `boxedwine.upstreamjit7inputfix.wasm`: `3718374A08576FA30CFA09AC7705BCC8330FAEA51D81984B07C22B2BED5DAF07`

## 범위

- **VERIFIED:** 잠금 해제 상태 절대 포인터, `1024x768` CSS 표시, 캐릭터 선택 `접속` 클릭, PatHouse 진입.
- **NOT VERIFIED:** 표준 브라우저 root document에서 Pointer Lock 카메라 회전/ESC detach/재attach. 이는 251을 계속 따른다.

