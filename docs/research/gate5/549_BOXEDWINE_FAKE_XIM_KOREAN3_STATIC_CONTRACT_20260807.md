# 549. BoxedWine fake-XIM korean3 static contract (2026-08-07)

> **PARTIALLY SUPERSEDED by 550.** fake-XIM 계약은 유효하지만 korean3 URL은 라이브에서 모순된 map ABI를 보고해 기본 배포에서 제외했다. 기본 immutable runtime은 korean4다.

## Scope

브라우저 `compositionend`가 만든 UTF-8을 BoxedWine FIFO에 넣고, Wine 11이 실제로 소비하는 `XmbLookupString`의 `XLookupChars` 결과로 돌려주는 최소 fake-XIM 계약을 구현했다. 기존 clipboard/강제 Ctrl+V는 rollback fallback으로 보존했다. 원본 게임 바이너리, 서버 프로토콜, 공인 IP listener는 변경하지 않았다. 사용자 요청에 따라 실제 게임 실행과 Plaza 입력 테스트는 하지 않았다.

## VERIFIED — `vvvv`의 구조적 원인

- 기존 `korean1` WASM에는 Ctrl down → V down/up → Ctrl up 합성 코드가 실제로 들어 있었다. 따라서 `vvvv`는 단순히 소스 수정이 빠진 현상으로 단정할 수 없다.
- Wine 11 `X11DRV_KeyEvent`는 X 이벤트의 `state` 비트만 보고 Windows Ctrl 상태를 만들지 않고, 각 KeyPress/KeyRelease를 `NtUserSendHardwareInput`으로 보낸다. `g_boxedwineForceControlModifier`는 이 경로의 근본 계약이 아니었다.
- 당시 BoxedWine의 `XOpenIM`은 0, `XmbLookupString`은 panic이었고 `XCreateIC`/focus 관련 엔트리도 동작 계약이 없었다. Wine은 XIC가 없으면 `XLookupString`/물리 keycode 경로에 남으므로, 조합 완료 문자열을 `xim_set_result_string()`으로 넘길 수 없었다.
- 서버 로그의 실제 채팅 payload에도 `vvvv`, `vvvvv`, `vdkssuivvvv`가 남아 clipboard/Ctrl 경로의 Plaza 수락 성공 주장을 반증했다.

## VERIFIED — 최소 fake-XIM ABI

- 게스트 `tools/x11/X11.c`의 `XGetIMValues()`가 varargs를 읽고 `XNQueryInputStyle`의 output pointer를 `X11_GET_IM_VALUES` 2-인자 ABI로 전달한다.
- 호스트 `x11common.cpp`는 `XOpenIM`, `XCloseIM`, `XDisplayOfIM`, `XLocaleOfIM`, `XGetIMValues`, `XVaCreateNestedList`, `XCreateIC`, `XDestroyIC`, focus/set/reset 엔트리에 Wine이 요구하는 최소 opaque-handle 계약을 제공한다.
- query style은 `XIMPreeditNothing | XIMStatusNothing` 한 개다. 32-bit guest `XIMStyles`는 12-byte 단일 allocation으로 만들어 Wine의 단일 `XFree`와 맞춘다.
- `XmbLookupString`은 합성 KeyPress와 UTF-8 FIFO scalar를 결합해 buffer에 committed bytes를 쓰고 status `XLookupChars(2)`를 반환한다. Wine 11은 이 status에서 `xim_set_result_string()`을 호출하고 물리 keycode 처리를 종료한다.
- FIFO payload가 없는 borrowed keycode의 release/repeat는 `XLookupNone`으로 삼켜 라틴 문자 누출을 막는다.

## VERIFIED — build and immutable deployment identity

- guest libX11 32-bit compile/link: `-Wall -Werror -Wno-return-type -m32 -march=i586`, pass. WSL build prerequisite로 `libglu1-mesa-dev:i386`를 설치했다.
- `libX11.so.6.4.0`: 32,316 bytes, SHA-256 `F67436E6649B9DD9205AE6D7527311185B1A294348007145266FFBC137F3A4ED`.
- korean3 JS: SHA-256 `857BADA4C966F5691989557559A4BC5144F7E337C802CE8765983E39135482DE`.
- korean3 WASM: SHA-256 `A3E0160AF4AD1AF7A32CF5045CF0497A8AC501C3406DA4A8A6330AD316CE4520`. 바이너리에 `ko_KR.UTF-8` 표식이 존재한다.
- 기존 자산은 덮어쓰지 않았다. 새 runtime stem은 `boxedwine.upstreamjit64fn6inlineabi2korean3`, 새 root stem은 `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-noprefixupd1-acp949-xim1`이다.
- 새 ZIP의 `usr/local/lib/libX11.so.6.4.0` 해시는 위 빌드 산출물과 동일하다. ZIP SHA-256은 `4641D1BD5F8A24C49F45EE444F6E1898C0F4D141F23A5B44A601B2B8422F6DC6`이다.
- 기본 페이지는 korean3/xim1을 선택하며 `boxedwine_inject_text_utf8`을 먼저 호출한다. export가 없는 구 runtime에 대해서만 `boxedwine_paste_text_utf8`을 fallback으로 호출한다.

## Verification

- `python -m unittest tools.test_boxedwine_xim_contract tools.test_d3d9web_page_contract`: **18 passed**.
- `python -m unittest discover -s tools -p "test_*.py"`: **221 passed** after
  the XIM, OX launcher-contract, audio, page, and server-state changes were
  combined.
- generated korean3 JS `node --check`: pass.
- guest libX11 compile/link: pass.
- Emscripten `azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbi`: pass.
- 새 root ZIP entry hash와 standalone guest lib hash: exact match.
- Live LAN HTTPS (`<lan-ip>:8765`) returned korean3 JS **200 / 328459
  bytes**, korean3 WASM **200 / 3053605 bytes**, and xim1 root ZIP **200 /
  167614916 bytes**.  The served page selects korean3/xim1 and orders inject
  before clipboard fallback.  This proves delivery identity, not in-game text
  acceptance.

## NOT VERIFIED

- Wine이 실제 Azrok 창에서 fake XIM/XIC를 생성하는지.
- `XLookupChars`가 `xim_set_result_string()`을 거쳐 Azrok Edit의 CP949 text로 최종 수락되는지.
- 실제 Plaza에서 완성 한글이 보이고 `vvvv`/라틴 조합 원문이 누출되지 않는지.
- 게임 입력·렌더링·BGM·성능 회귀가 없는지.

위 네 항목은 사용자의 다음 플레이 테스트 전에는 성공으로 승격하지 않는다.
