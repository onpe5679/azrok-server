> **SUPERSEDED by 593 for touch input.** 모바일 전체화면 4:3 contain 결론은 계속 유효합니다.

# 591 — 네이티브 SDL 터치 복구와 모바일 가로 전체화면 4:3

날짜: 2026-08-27

## 결론

- **VERIFIED:** #590의 브라우저 touch→MouseEvent 우회는 잘못된 소유권 변경이었다. SDL Emscripten backend가 이미 `targetX / client_w`, `targetY / client_h`로 CSS 좌표를 정규화하고, SDL core가 그 값을 `window->w/h`에 곱해 mouse motion/button을 합성한다.
- **VERIFIED:** #590 우회는 네이티브 SDL touch callback을 capture 단계에서 막고 `mousedown`을 직접 보냈다. SDL mouse button handler는 버튼 좌표를 갱신하지 않고 직전 mouse motion 위치를 사용하므로, tap 직전 motion이 없는 이 경로는 좌표가 뒤처지거나 이전 위치를 재사용할 수 있다.
- **VERIFIED:** 커스텀 `dispatchTouchMouse`/`touchBridge`를 제거했다. 모바일 touch는 다시 SDL의 정규화·mouse 합성 단일 경로가 소유하며, 기존 pointer fallback은 실제 mouse pointer에만 제한한다.
- **VERIFIED:** 모바일 일반 화면의 `width:100%; height:auto` 규칙이 가로 전체화면에서도 우선되어 4:3 canvas 높이가 viewport보다 커지는 충돌을 수정했다. `:fullscreen`과 `:-webkit-full-screen`에서 동적 viewport 기준 4:3 contain 크기를 더 높은 specificity로 강제한다.
- **VERIFIED:** 실제 Chromium의 `d3d9web-mobile` 전체화면 분기에서 3840×2160 viewport에 canvas 2880×2160, ratio 1.333333, overflow x/y 0을 측정했다. 즉 상하 crop 없이 좌우 letterbox가 생긴다.
- **NOT VERIFIED:** 수정 후 실제 물리 모바일에서 우하단 끝까지 정확히 터치되는 최종 사용자 수용 확인은 필요하다.

## 직접 근거

- `bwujit_threaded_abi/lib/sdl2/src/video/emscripten/SDL_emscriptenevents.c`
  - `x = targetX / client_w`, `y = targetY / client_h`.
  - touch callback은 canvas에 bubble 단계로 등록된다.
- `bwujit_threaded_abi/lib/sdl2/src/events/SDL_touch.c`
  - `SYNTHESIZE_TOUCH_TO_MOUSE 1`.
  - `pos_x = x * window->w`, `pos_y = y * window->h` 뒤 mouse motion/button 전송.
- `tools/boxedwine_local/assets_d3d9web/boxedwine.audiogate6.js`
  - 현재 배포 runtime에 touchstart/end/move/cancel callback 등록이 포함된다.

## 변경

- `tools/boxedwine_local/index_d3d9web_pathouse.html`
  - 커스텀 touch capture와 합성 MouseEvent 제거.
  - 모바일 전체화면에서 `100dvw/100dvh` 기반 4:3 contain 규칙 추가.
  - WebKit fullscreen selector도 동일 처리.
- `tools/test_d3d9web_page_contract.py`
  - 네이티브 SDL 정규화와 touch→mouse 합성 근거를 계약으로 고정.
  - 모바일 fullscreen 4:3 동적 viewport 계약 추가.

## 검증

- `python -m unittest tools.test_d3d9web_page_contract` — **24/24 PASS**
- `python -m unittest discover tools` — **283/283 PASS**
- 실제 Chromium `mobileCapture=1` 전체화면 — viewport 3840×2160, canvas 2880×2160, ratio 4:3, overflow 0.
