# 541 BoxedWine 한글 조합 완료 텍스트 경로 정적 확정과 최소 X11 훅 (2026-07-30)

날짜: 2026-07-30  
선행: #539  
범위: 브라우저/CDP 실행 없이 BoxedWine·SDL·Wine root 이미지·Azrok 디컴파일의 정적 소스 분석, 그리고 소스 훅 적용.

원본 `Azrok.exe`, `acknex.dll`, 게임 자산은 변경하지 않았습니다.

## 결론

**VERIFIED:** 기존 빌드는 조합 완료 텍스트가 Wine까지 갈 수 있는 경로가 없습니다. Emscripten SDL은 `keypress`에서 UTF-8 `SDL_TEXTINPUT`을 만들 수 있으나 기본적으로 비활성이고, BoxedWine은 이를 소비하지 않습니다. 실제 키는 가상 X11의 고정 US/ASCII 키맵만 통과합니다.

**VERIFIED:** Azrok 채팅창은 ASCII-only 게임 위젯이 아니라 ANSI 표준 `Edit` 컨트롤입니다. 서브클래스는 Enter만 가로채고 나머지 메시지를 원래 Edit 프로시저에 위임합니다. `GetWindowTextA`로 바이트 문자열을 읽고, 렌더도 high-bit 문자를 2바이트 DBCS로 다룹니다.

**선택 및 적용:** 후보 **(b)**, BoxedWine C++ 텍스트 훅 + WASM 재빌드를 선택했습니다. 조합 완료 Unicode scalar를 `SDL_TEXTINPUT`으로 넣고, 가상 X11의 synthetic `KeyPress`와 연결해 `XLookupString`이 UTF-8 payload를 반환하도록 했습니다. 이 방식은 게임 바이너리와 자산을 건드리지 않고 Wine의 기존 키→문자 메시지 경로를 보존합니다.

**NOT VERIFIED:** 포함된 Wine 11은 소스가 아닌 binary-only이므로, 이 UTF-8 `XLookupString` 결과를 Wine이 어떤 `WM_CHAR`/`WM_IME_CHAR` 시퀀스로 만들고 ANSI Edit에 어떻게 변환하는지는 이 워크스페이스의 정적 자료만으로 증명할 수 없습니다. 또한 현재 선택 root의 ACP는 **1252**이지 949가 아닙니다. 따라서 패치가 컴파일된 뒤의 브라우저 실측 전에는 “게임 입력창에 한글이 실제로 들어간다”를 VERIFIED라고 쓸 수 없습니다.

## 1. 기존 입력 경로

| 단계 | 직접 근거 | 판정 |
|---|---|---|
| DOM 키 이벤트 등록 | `lib/sdl2/src/video/emscripten/SDL_emscriptenevents.c:638-670`은 `keydown`/`keyup`/`keypress`만 등록합니다. `compositionstart`/`update`/`end` 등록은 없습니다. | VERIFIED |
| DOM → SDL key | 같은 파일 `:477-525`가 keydown/up을 `SDL_SendKeyboardKey()`로 보냅니다. | VERIFIED |
| DOM keypress → UTF-8 | 같은 파일 `:529-536`이 `charCode`를 UTF-8로 만들고 `SDL_SendKeyboardText()`를 부릅니다. | VERIFIED |
| SDL text queue 조건 | `lib/sdl2/src/events/SDL_keyboard.c:789-809`은 TEXTINPUT event state가 enabled일 때만 큐잉합니다. 기본 state는 `SDL_events.c:447`에서 disabled입니다. BoxedWine source에는 기존 `SDL_StartTextInput()` 호출이 없었습니다. | VERIFIED |
| SDL poll | `source/sdl/emscripten/mainloop.cpp:54-84,130-160` → `KNativeInputSDL::processEvents()`, 실제 poll/dispatch는 `platform/sdl/knativeinputSDL.cpp:302-318`입니다. | VERIFIED |
| 기존 텍스트 폐기 | 패치 전 `handlSdlEvent()`는 mouse, `SDL_KEYDOWN`, `SDL_KEYUP`, window event만 처리했습니다(`knativeinputSDL.cpp:555-622`). `SDL_TEXTINPUT` case가 없었습니다. | VERIFIED |
| 보통 키 → X11 | `knativeinputSDL.cpp:270-280,597-610` → `XKeyboard::sdl2x11()` → `XServer::key()`입니다. | VERIFIED |
| 가상 X11 event | `source/x11/xserver.cpp:1008-1020`이 focus window로 보내고, `source/x11/xwindow.cpp:1345-1383`이 `KeyPress`/`KeyRelease`를 Wine X11 client event queue에 넣습니다. | VERIFIED |
| X11 문자 얻기 | `source/x11/x11common.cpp:761-800`의 `XLookupString()`은 `XKeyboard::translate()`만 사용했습니다. 키맵은 `source/x11/xkeyboard.cpp:37-142`의 `usKeyBoard`; 문자 필드는 ASCII뿐이고 `:408-446`은 그 바이트만 복사합니다. | VERIFIED |
| `/dev/input` | XServer 부재일 때만 `onKeyDown/Up()` fallback을 씁니다(`knativeinputSDL.cpp:601-608`). 이는 `source/kernel/devs/devinput.cpp:832-857`의 key/sync event일 뿐 text channel이 아닙니다. | VERIFIED |

따라서 질문의 “브라우저 key/composition → SDL → guest Linux → Wine → WM_CHAR/WM_IME_CHAR”는 **현재** 다음에서 끊깁니다.

```text
compositionend: DOM listener 자체가 없음
keypress: UTF-8 SDL_TEXTINPUT 가능 (단, 기본 disabled)
      -> KNativeInputSDL: SDL_TEXTINPUT case 없음, payload 폐기
      -> Wine/WM_CHAR: 도달하지 않음
```

Wine의 실제 `WM_CHAR` 또는 `WM_IME_CHAR` 생성 파일:라인은 제공할 수 없습니다. active root ZIP의 `opt/wine/`에는 `.c/.cc/.cpp/.in` 구현 소스가 0개이고 Wine implementation `.so/.dll.so`만 있습니다. 이는 **NOT VERIFIED가 아니라, 현재 자료로는 검증 불가능함이 VERIFIED**인 한계입니다.

## 2. SDL_TEXTINPUT과 코드페이지

`SDL_TEXTINPUT` UTF-8은 “게스트까지 전달된다”고 말할 수 없습니다. 활성화되지 않았고, 활성화되더라도 BoxedWine이 소비하지 않습니다. 그러므로 기존 경로에서 Wine의 UTF-8→ANSI `WM_CHAR` 변환 코드페이지를 묻는 전제 자체가 성립하지 않습니다.

- `source/x11/x11common.cpp:802-804`: `XmbLookupString`은 panic입니다.
- `:2378-2457`: `XOpenIM`은 0, `SetICFocus`/`UnsetICFocus`/`CreateIC` 등은 panic입니다.
- `:2365-2366`: 가상 X server가 `WM_LOCALE_NAME=en_US.UTF-8`을 광고합니다.

따라서 (c) Wine IME 설정만으로는 앞선 SDL payload 폐기를 해결할 수 없습니다. **VERIFIED.**

선택된 root `tools/boxedwine_local/fs/fullWine1.7.55-v8.zip`의 `home/username/.wine/system.reg`를 직접 읽은 결과는 다음과 같습니다.

```text
virtual line 31099  [System\\CurrentControlSet\\Control\\Nls\\Codepage]
virtual line 31102  "ACP"="1252"
```

CP949 NLS가 root 안에 있더라도 ACP=949라는 뜻은 아닙니다. 현재 ACP 1252이므로 Wine의 ANSI conversion에 949가 쓰인다고 주장할 수 없습니다. **VERIFIED.**

## 3. Azrok Edit와 DBCS

- `plaza_dump.txt:174280-174303`, `:236000-236052`: `FUN_005209e0`이 `CreateWindowExA(..., "edit", ...)`로 ANSI standard Edit를 만들고 HWND를 보관한 뒤 subclass를 설치합니다. RTTI `CDxEdit2`도 `plaza_vtables.txt:425-428`에 있습니다. **VERIFIED.**
- `plaza_dump.txt:236358-236381`: `FUN_005214f0`은 `WM_KEYDOWN`/`WM_KEYUP` 중 Enter만 다루고 나머지는 `CallWindowProcA`로 원래 Edit proc에 넘깁니다. 즉 `WM_CHAR`/`WM_IME_CHAR`를 게임이 명시적으로 ASCII filter하는 코드가 없습니다. **VERIFIED.**
- `plaza_dump.txt:236071-236138`: `FUN_00520cc0`은 매 tick `GetWindowTextA(hwnd, object+0x3a, 0x200)`를 호출합니다. `plaza_dump.txt:223852-224041`은 Enter 때 이 buffer를 `_strlen` 후 C2S 생성기로 넘깁니다. **VERIFIED.**
- `plaza_dump.txt:235299-235319`: `FUN_0051eec0`은 high-bit clear면 +1, set이면 +2 전진합니다. 따라서 채팅 문자열 모델은 DBCS 2-byte 단위입니다. **VERIFIED.**

`안`(CP949 `BE C8`)과 `녕`(`B3 E7`)의 lead/trail을 *각각 별도의 `WM_CHAR`*로 전달하는 것이 Wine ANSI Edit에서 허용되는지는 Wine user32/Edit source가 없어 **NOT VERIFIED**입니다. 그러나 그렇게 만들어진 NUL 없는 4바이트 문자열을 Azrok가 읽고 다룰 수 있다는 것은 위 `GetWindowTextA` 및 DBCS stride로 직접 확인됐습니다. **VERIFIED.**

## 4. 적용한 최소 훅

변경 파일은 BoxedWine source 네 개뿐이며 game binary/assets는 무수정입니다.

1. `platform/sdl/knativeinputSDL.cpp:48-58`
   - `SDL_StartTextInput()`으로 text event를 활성화했습니다.
   - `EMSCRIPTEN_KEEPALIVE` exported C ABI `boxedwine_inject_text_utf8()`를 추가했습니다. 이 함수는 UTF-8 scalar를 `SDL_TEXTINPUT` queue에 넣습니다.
2. `platform/sdl/knativeinputSDL.cpp:615-632`
   - ASCII는 기존 KEYDOWN 경로와 중복되지 않도록 무시합니다.
   - non-ASCII UTF-8 text만 X11 text FIFO에 넣고, scalar마다 unused synthetic keycode `0x7e`의 press/release를 focus window에 넣습니다.
3. `source/x11/xkeyboard.h:329-331`, `xkeyboard.cpp:411-448`
   - UTF-8 scalar FIFO와 `queueTextInput()`/`consumeTextInput()`을 추가했습니다.
4. `source/x11/x11common.cpp:777-788`
   - synthetic keycode의 `XLookupString()`은 static US map 대신 FIFO UTF-8 payload를 반환합니다. keysym은 `NoSymbol`(0)입니다.
5. `project/emscripten/boxedwine-shell.js:1038-1048`
   - SDL upstream이 놓친 `compositionend`를 listen합니다.
   - non-ASCII commit만 Unicode scalar 단위로 exported queue API에 넣습니다. ASCII keypress는 기존 경로를 유지합니다.

새 경로는 다음과 같습니다.

```text
DOM compositionend (완료 text)
  -> boxedwine_inject_text_utf8() -> SDL_TEXTINPUT
  -> KNativeInputSDL (non-ASCII)
  -> XKeyboard UTF-8 FIFO + synthetic KeyPress(0x7e)
  -> XLookupString returns UTF-8 payload
  -> Wine binary keyboard handling -> WM_CHAR/ANSI Edit -> GetWindowTextA
```

마지막 Wine binary arrow와 ACP 949 conversion은 **NOT VERIFIED**입니다. 이 패치는 그 지점까지의 source-controlled 전달 경로만 복원합니다.

## 5. 후보 판정

| 후보 | 판정 | 근거 |
|---|---|---|
| (a) JS만으로 guest key queue byte 주입 | 불충분 | 현 JS에 text payload consumer/export가 없고 C++는 static keycode만 소비합니다. payload를 건너뛰면 Korean scalar/DBCS를 표현할 수 없습니다. VERIFIED. |
| (b) C++ text hook + WASM rebuild | 선택 | 최초 차단점(SDL text disabled/ignored)과 X11 ASCII table을 바로 고칩니다. game binary 무수정이며 Wine의 기존 message path를 유지합니다. source-controlled 부분 VERIFIED, Wine 변환 결과 NOT VERIFIED. |
| (c) Wine IME/codepage만 설정 | 불가 | XIM 구현이 없고, 이전 단계에서 text가 폐기됩니다. ACP=1252도 별도 문제입니다. VERIFIED. |
| (d) 불가능 | 부정 | BoxedWine source 쪽에는 명확한 injection boundary가 있고 훅을 적용했습니다. Wine binary의 결과만 정적 증명 불가입니다. |

## 6. 검증과 재빌드

정적 검증:

```text
node --check project/emscripten/boxedwine-shell.js      PASS
source hook static-contract check                         PASS
```

Emscripten object/full build는 이 작업 환경에서 실행하지 못했습니다.

```text
make: command not found
em++ direct object compile: clang++.exe permission denied
```

이는 source syntax failure가 아니라 현 sandbox toolchain executable 제약입니다. 브라우저/CDP는 실행하지 않았습니다.

재빌드해야 배포 asset에 반영됩니다. active runtime과 동일한 make target을 사용해야 하며 JS/WASM/shell을 같은 build output에서 함께 교체해야 합니다.

```bash
source <home>/emsdk/emsdk_env.sh
cd <home>/Documents/<project-dir>/Azrok_Plaza/tools/boxedwine_local/bwujit_threaded_abi/project/emscripten
make -f makefile -j2 <active-azrok-target>
# Build/<active-azrok-target>/boxedwine.js
# Build/<active-azrok-target>/boxedwine.wasm
# Build/<active-azrok-target>/boxedwine-shell.js
```

소요 시간은 이 sandbox에서는 측정할 수 없습니다. 이전 build log의 wall time을 신뢰할 직접 근거도 없으므로 추정치를 기록하지 않습니다. 재빌드 후에는 사람이 브라우저에서 한글 1자와 `안녕`을 입력하여 (1) Edit 표시, (2) `GetWindowTextA` 기반 C2S byte, (3) 화면 렌더를 함께 확인해야 합니다. ACP 949 전환은 root overlay를 만들기 전에 실제 active root ZIP를 하나로 확정하고 Wine binary behavior를 실측한 뒤 별도 최소 변경으로 진행해야 합니다.
