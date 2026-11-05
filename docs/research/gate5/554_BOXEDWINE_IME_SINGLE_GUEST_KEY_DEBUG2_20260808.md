# 554. BoxedWine IME single guest-key debug2 (2026-08-08)

## Scope

Plaza에서 브라우저 자동화 Enter 한 번이 Wine X11 `XmbLookupString` 호출을 4회 늘려 Edit 활성화 여부를 판정하지 못했다. 페이지나 production runtime을 바꾸지 않고 SDL event layer에 정확히 한 번의 press/release를 보내는 debug-only export를 추가해 동적 수락 테스트를 분리한다.

## VERIFIED — 최소 구현

- `platform/sdl/knativeinputSDL.cpp`의 `BOXEDWINE_IME_RUNTIME_DEBUG` 구간에 `boxedwine_ime_debug_key(unsigned int scancode)`를 추가했다.
- 0 또는 `SDL_NUM_SCANCODES` 이상은 거부한다.
- 유효 scancode에 `SDL_SendKeyboardKey(SDL_PRESSED, ...)`와 `SDL_SendKeyboardKey(SDL_RELEASED, ...)`를 각각 정확히 한 번 호출한다.
- 반환 bit 0은 press가 SDL queue에 게시됨, bit 1은 release가 게시됨을 뜻한다. 따라서 `SDL_SCANCODE_RETURN=40`의 정상 반환은 `3`이다.
- production korean5와 기존 immutable debug1은 덮어쓰지 않았다.
- `index_d3d9web_pathouse.html`, 원본 게임 바이너리, server protocol은 수정하지 않았다.

## VERIFIED — immutable debug2 identity

- runtime stem: `boxedwine.upstreamjit64fn6inlineabi2korean5imedebug2`
- JS: 329,161 bytes, SHA-256 `7F8BA53B8A6D422D24AE3AF49B168D2D9CCC7BA04010EC25E3C074764C9AF38D`
- WASM: 3,055,349 bytes, SHA-256 `3A1A903245430B029C0FC19CC46C27F53DB238A923CF422C8B69A7E3E3515467`
- Node가 JS glue의 실제 raw WASM export를 따라 직접 확인한 값은 `relocMapBase=12968408`, `relocMapCapacity=262144`, debug ABI `1`, snapshot words `38`, key export type `function`이다.
- LAN `<lan-ip>:8765`와 Tailscale `<tailscale-ip>:8765`가 위 JS/WASM과 동일한 해시를 제공한다.
- `python -m unittest tools.test_boxedwine_xim_contract -v`: 12/12 pass.

## Runtime probe contract

```js
Module.ccall('boxedwine_ime_debug_key', 'number', ['number'], [40])
```

기대값은 `3`이다. 이 한 번의 호출 뒤 Edit가 열렸는지 확인하고, browser composition commit을 주입하여 #553의 C.UTF-8 app A/B를 판정한다.

## NOT VERIFIED

- debug2 호출이 실제 live guest에서 Edit를 여는지.
- Edit가 열린 상태에서 fake-XIM의 UTF-8 `한글`이 Azrok Edit에 표시되는지.
- 전송 뒤 C2S `0x006A` 또는 상대 세션 말풍선에 동일한 한글이 나타나는지.

위 세 항목은 실제 Plaza 동적 확인 전에는 성공으로 승격하지 않는다.
