# 595 — BoxedWine 모바일 터치 이중 스케일 제거

날짜: 2026-08-27

## 결론

- **VERIFIED:** #593의 브라우저 좌표 환산은 CSS canvas 위치를 현재 BoxedWine 논리 화면 `screenWidth()/screenHeight()`로 바꾸는 데까지는 맞았다.
- **VERIFIED:** 그러나 `boxedwine_touch_pointer`가 그 논리 좌표를 기존 `KNativeInputSDL::mouseMove/mouseButton`에 넘겼고, 두 함수는 입력을 SDL window 좌표로 간주해 `xFromScreen/yFromScreen`을 다시 적용했다. 따라서 모바일의 확대/축소 비율이 좌표에 두 번 반영되며, 좌상단은 맞고 우하단으로 갈수록 오차가 누적되고 오른쪽/아래쪽이 도달 불가능해졌다.
- **VERIFIED:** 새 `touch2` 런타임은 브라우저가 환산한 논리 좌표를 `mouseMoveLogical/mouseButtonLogical`로 전달한다. 이 공통 함수들은 XServer에 좌표를 그대로 보내면서 기존 recorder, audio unlock, button mapping을 유지한다.
- **VERIFIED:** 기존 `touch1` JS/Wasm은 덮어쓰지 않았다. 새 Wasm은 pointer exports와 currentabi1 relocation map base `12968408`, capacity `262144`를 유지한다.
- **NOT VERIFIED:** 물리 모바일에서 새 페이지를 다시 열고 네 모서리 및 우하단 버튼을 누르는 최종 사용자 수용 시험은 남아 있다.

## 직접 근거

### 이중 변환

브라우저는 다음 식으로 CSS 좌표를 논리 화면 좌표로 만든다.

```text
x = floor((clientX - rect.left) * screenWidth / rect.width)
y = floor((clientY - rect.top)  * screenHeight / rect.height)
```

#593 구현은 이 값을 `KNativeInputSDL::mouseMove/mouseButton`에 넘겼다. 두 함수 본문은 다시 다음 변환을 수행한다.

```text
xFromScreen(x) = (x - scaleXOffset) * 100 / scaleX
yFromScreen(y) = (y - scaleYOffset) * 100 / scaleY
```

따라서 이미 논리 좌표인 값이 다시 축소된다. 이는 사용자가 보고한 “좌상단은 정확하지만 우하단으로 갈수록 빗나가고 오른쪽/아래쪽은 클릭 불가” 패턴과 일치한다.

### 교체 경로

- `boxedwine_touch_pointer`
  - 현재 논리 폭/높이로 clamp.
  - `KNativeInputSDL::mouseMoveLogical(x, y, false)` 호출.
  - down/up은 `mouseButtonLogical(action == 1, 0, x, y)` 호출.
- 기존 desktop/SDL 입력
  - `mouseMove/mouseButton`이 종전처럼 `xFromScreen/yFromScreen`을 한 번 수행한 뒤 같은 logical 공통 함수로 진입.
- 결과
  - 브라우저 touch는 변환 1회.
  - desktop/SDL mouse는 변환 1회.
  - 오디오 unlock과 X11 버튼 번호 변환은 양쪽 모두 동일.

## 변경

- `tools/boxedwine_local/bwujit_threaded_abi/platform/sdl/knativeinputSDL.h`
- `tools/boxedwine_local/bwujit_threaded_abi/platform/sdl/knativeinputSDL.cpp`
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/makefile`
- `tools/boxedwine_local/index_d3d9web_pathouse.html`
- `tools/boxedwine_local/azrok_launch.js`
- `tools/test_d3d9web_page_contract.py`
- `tools/test_boxedwine_xim_contract.py`
- `tools/test_azrok_home_contract.py`

## 불변 산출물

- runtime stem: `boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2`
- JS: 329,600 bytes
- JS SHA-256: `3396bf98e087d8190c120e204bf2e33a96ca68ccc5dd1eb39d14db49712c5ca6`
- Wasm: 3,056,422 bytes
- Wasm SHA-256: `d717235bce2663585291246ddc4528b5c2a609c704b3135f3244e60741efea96`
- raw exports: `_boxedwine_pointer_stat`, `_boxedwine_touch_pointer`
- currentabi1 relocation map: base `12968408`, capacity `262144`

## 검증

- Emscripten 격리 `touch2` build — **PASS**.
- 이전 `touch1` JS/Wasm SHA-256 불변 — **PASS**.
- 새 JS/Wasm SHA-256 및 raw export — **PASS**.
- currentabi1 relocation map base/capacity — **PASS**.
- 페이지/런타임/홈페이지 집중 계약 61 tests — **PASS**.
- 전체 도구 회귀 계약 — **289/289 PASS**.
- 8765 HTTP 실제 전달 — JS 329,600 bytes, Wasm 3,056,422 bytes이며 위 로컬 SHA-256과 각각 일치 — **PASS**.
- 8765의 `azrok_launch.js`와 실행 페이지 기본 runtime stem이 모두 `touch2`를 가리킴 — **PASS**.
- 실제 in-app browser의 새 `autorun=0` 실행 페이지 script 목록에서 `assets_d3d9web/boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2.js` 요청 확인 — **PASS**.
- 물리 모바일 네 모서리/우하단 — **NOT VERIFIED**.
