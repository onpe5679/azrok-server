> **SUPERSEDED by 595.** 브라우저 환산 좌표를 `KNativeInputSDL::mouseMove/mouseButton`에 넘기면 내부 `xFromScreen/yFromScreen`이 다시 적용되어 물리 모바일 오차가 남는다. 원인과 교체 구현은 #595를 따른다.

# 593 — BoxedWine 논리 화면 기준 모바일 터치 좌표

날짜: 2026-08-27

## 결론

- **VERIFIED:** #591의 네이티브 SDL touch 경로만으로는 물리 모바일 문제가 해결되지 않았다. 사용자가 다시 확인한 증상은 좌상단은 정확하지만 우하단으로 갈수록 오차가 커지고 오른쪽/아래쪽이 도달 불가능한 형태다.
- **INFERRED:** 증상 비율은 초기 SDL window `800x600`을 실제 Azrok 논리 화면 `1024x768`에 사용했을 때의 `800/1024 = 600/768 = 0.78125`와 정확히 같은 모양이다. 즉 우측/하단 21.875%가 도달 불가능해진다. 물리 기기의 실제 내부 수치는 아직 직접 읽지 못했다.
- **VERIFIED:** 새 런타임은 브라우저 터치를 SDL의 보존된 window 크기에 다시 곱하지 않는다. BoxedWine의 `KNativeSystem::getCurrentInput()`에서 현재 `screenWidth()/screenHeight()`를 읽고, CSS canvas 좌표를 그 논리 화면에 직접 환산해 `mouseMove`와 `mouseButton`으로 보낸다.
- **VERIFIED:** 전용 빌드 타깃과 불변 JS/Wasm 자산은 기존 korean6chat1을 덮어쓰지 않고 새 `korean6chat1touch1` stem으로 배포한다. JIT relocation map은 기존 currentabi1의 base `12968408`, capacity `262144`를 유지한다.
- **VERIFIED:** #591의 모바일 가로 전체화면 4:3 contain/letterbox 규칙은 유지했다.
- **NOT VERIFIED:** 물리 모바일에서 우하단 끝과 네 모서리를 직접 눌러 보는 최종 사용자 수용 시험은 필요하다.

## 변경

- `tools/boxedwine_local/bwujit_threaded_abi/platform/sdl/knativeinputSDL.cpp`
  - `boxedwine_pointer_stat`: ABI 1과 현재 BoxedWine 논리 폭/높이 반환.
  - `boxedwine_touch_pointer`: 논리 좌표 clamp, move, primary down/up 직접 전달.
- `tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/makefile`
  - `azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbiImeDebugKeyTouch` 격리 타깃 추가.
- `tools/boxedwine_local/index_d3d9web_pathouse.html`
  - 기본 runtime stem을 `boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch1`으로 전환.
  - 전용 export가 준비된 경우 capture 단계에서 primary touch를 논리 화면 좌표로 직접 전달하고, 수락된 이벤트만 SDL의 중복 합성 전에 차단.
  - export가 없거나 아직 준비되지 않은 경우 기존 SDL 경로를 막지 않는다.
- `tools/test_d3d9web_page_contract.py`, `tools/test_boxedwine_xim_contract.py`
  - 좌표 환산 소유권, native input routing, 격리 타깃, 해시, exports, currentabi1 map 계약 추가.

## 불변 산출물

- JS SHA-256: `3396bf98e087d8190c120e204bf2e33a96ca68ccc5dd1eb39d14db49712c5ca6`
- Wasm SHA-256: `7d1c6333da233fa52cb46589f0a3293a5c952b7562336eee057e85073143b8f7`
- Wasm exports: `_boxedwine_pointer_stat`, `_boxedwine_touch_pointer`.
- relocation map: base `12968408`, capacity `262144`.

## 검증

- Emscripten 새 타깃 clean build — **PASS**.
- 새 JS/Wasm 해시 고정 및 raw Wasm export 검사 — **PASS**.
- 페이지/런타임 집중 계약 — **26/26 PASS**.
- 전체 도구 회귀 계약 — **288/288 PASS**.
- 8765 HTTP에서 새 JS 329600 bytes와 Wasm 3056293 bytes를 내려받아 로컬 불변 해시와 동일함을 확인 — **PASS**.
- 실제 서버 선택 페이지에서 보존 광장 `접속가능`, 코어 9200/9300 `running=true` 확인 — **PASS**.
- 물리 모바일 우하단 터치 — **NOT VERIFIED**.
