> **SUPERSEDED by 545.** X11 `XLookupString` 주입은 Wine이 반환 문자열을 무시하므로 폐기했고, Wine의 기존 Clipboard/`Ctrl+V` 경로로 대체했습니다.

# 542 한글 입력 — 브라우저 구간 해결, 게스트 구간은 유실성 (2026-07-30)

날짜: 2026-07-30
선행: #541(정적 경로·소스 훅), #539
근거: 라이브 브라우저 세션 계측(이벤트 로그·스크린샷). 원본 실행파일·게임 자산 무수정.

---

## 0. 결론

| 구간 | 상태 |
|---|---|
| 브라우저 IME 조합 → `compositionend` | **해결 (VERIFIED)** |
| `compositionend` → WASM `boxedwine_inject_text_utf8` | **해결 (VERIFIED)** |
| WASM → Wine → ANSI Edit | **부분 동작, 유실 있음 (VERIFIED)** |

게임 채팅 로그에 한글 음절이 실제로 찍혔다. 경로는 뚫렸다. 다만 대부분의 글자가 유실된다.

## 1. 빌드 — Codex 계획의 결함 하나 (VERIFIED)

#541 이 적용한 훅은 `Module.ccall` 로 WASM 을 부른다. 그런데 이 빌드 타깃
(`azrokMultiThreadedJitAudioO3AsyncRingFn6InlineAbi`)은 `EXPORTED_RUNTIME_METHODS` 가
`addFunction,removeFunction,wasmTable,HEAPU8` 로 **고정**이라 `ccall` 이 없다.
그대로 빌드했다면 `typeof Module.ccall !== 'function'` 에서 조용히 return 하는,
**아무 일도 일어나지 않는** 훅이 됐을 것이다.

`makefile` 에 `ccall` 과 `_boxedwine_inject_text_utf8` 을 추가하고 재빌드·재링크했다.

```text
Build/.../boxedwine.js  grep ccall                      1
Build/.../boxedwine.js  grep boxedwine_inject_text_utf8 1
런타임 확인: Module.ccall = function, Module._boxedwine_inject_text_utf8 = function
```

배포는 되돌릴 수 있게 새 stem 으로 했다: `boxedwine.upstreamjit64fn6inlineabi2korean1`.
기존 stem 은 그대로 둔다. `boxedwine-shell.js` 는 공용이라 `.pre-korean1.bak` 로 백업했다.

## 2. ACP — 실사용 root 에서 직접 확인 (VERIFIED)

#541 은 `fullWine1.7.55-v8.zip` 을 읽었는데 **실제 실행에 쓰이는 root 는 그게 아니다**
(`TinyCore15Wine11.0-wsaeventfix5-korean4-...`). 실사용 root 를 직접 열어 확인한 결과
결론은 같았다.

```text
[System\ControlSet001\Control\Nls\Codepage]
"ACP"="1252"  "OEMCP"="437"  "MACCP"="10000"
c_949.nls  : home/username/.wine/drive_c/windows/system32/, opt/wine/share/wine/nls/  (둘 다 존재)
gulim.ttc  : 존재
```

CP949 NLS 와 한글 폰트는 이미 있는데 ACP 만 1252 였다.
ACP/OEMCP 만 949 로 바꾼 root 를 새로 만들었다(원본 보존, 접미사 `-acp949`).
8,660 엔트리를 권한 비트까지 보존해 재패킹. 부팅·한글 UI·접속 모두 정상.

> 이 root 는 저장 키가 달라 **프로필이 새것**이다. 캐릭터 선택 화면이 한 번 더 나온다.

## 3. 브라우저 구간 — 두 개의 실제 결함 (VERIFIED)

### 3.1 IME 가 아예 붙지 않았다

브라우저 IME 는 **편집 가능한 요소에 포커스가 있어야** 작동한다. 캔버스는 그런 요소가
아니므로 한영키를 눌러도 `compositionstart` 조차 발생하지 않았다.
영어만 되던 것이 정확히 이 증상이다 — ASCII 는 조합 없이 keydown 만으로 가기 때문이다.

수정: 캔버스 위에 투명 `<input>` 을 얹어 IME 대상으로만 쓴다.
`pointer-events:none` 이라 마우스는 전부 캔버스로 가고, keydown 은 document 로 버블링되어
SDL 의 ASCII 경로가 그대로 유지된다. 조합 중인 키만 capture 단계에서 SDL 에 닿지 않게 막는다
(`preventDefault` 를 쓰면 Chromium 이 조합을 중단시키므로 `stopImmediatePropagation` 을 쓴다).

### 3.2 내가 조합을 깨뜨리고 있었다

오버레이를 넣은 뒤에도 한글이 안 나왔다. 계측 결과:

```text
compositionstart 23 / compositionupdate 23 / compositionend 0
update 데이터: "ㅇ" "ㅓ" "ㅏ" "ㄴ" "ㅕ"  ← 자모는 정상 수신
```

매 키마다 start→update 후 **다시 start**. 커밋이 영영 안 된다.
원인은 입력 요소가 글자를 쌓지 않게 하려고 `input` 이벤트마다 `value` 를 비운 것.
**조합 도중 value 를 지우면 브라우저가 조합을 폐기한다.**

수정 후 계측:

```text
compositionstart 15 / compositionupdate 43 / compositionend 16
end 데이터: "신" "고" ...   ← 완성 음절 커밋됨
send() 반환 1 (스칼라 1개 전달)
```

**브라우저 구간은 여기서 끝났다.**

## 4. 게스트 구간 — 뚫렸으나 유실된다 (VERIFIED)

게임 채팅 로그에 한글 음절이 실제로 출력됐다.

```text
Guest : dкisksi 곤        ← 라틴 다수 + 한글 1자
```

즉 `XLookupString` → Wine → ANSI Edit 경로가 **동작은 한다**. #541 이 정적으로 증명 불가라고
남긴 마지막 구간이 실측으로 뚫린 것이다. 그러나 대부분의 스칼라가 유실된다.

CDP 로 `send('가')`, `send('나')`, `send('다')` 를 1.2초 간격으로 보낸 경우
입력줄에 **아무것도 들어가지 않았다**. 사용자가 직접 타이핑한 경우에만 간헐적으로 들어간다.

### 가설 (NOT VERIFIED)

`queueTextInput()` 이 UTF-8 을 FIFO 에 넣고 별도로 synthetic keycode `0x7e` 의
press/release 를 focus window 에 넣는데, 이 빌드는 `-sPROXY_TO_PTHREAD=1` 이라
키 이벤트 처리와 FIFO 접근이 다른 스레드에서 일어난다. 둘 사이에 순서 보장이 없으면
`XLookupString` 이 FIFO 를 비어 있는 상태로 읽거나 엉뚱한 키에 대해 소비한다.
브라우저 창이 OS 포커스를 갖지 않을 때 전량 실패하는 것도 X11 focus window 가
Edit 이 아니게 되는 것으로 설명된다.

### 다음 확인

1. `queueTextInput`/`consumeTextInput` 에 카운터를 export 해 **큐 투입 수 vs 소비 수**를 실측.
   유실이 FIFO 에서 나는지 그 이후인지 가른다.
2. 스칼라와 synthetic key 를 한 원자 단위로 묶거나, `XLookupString` 이 FIFO 를 소비할 때만
   키를 전달하도록 순서를 뒤집는다.
3. OS 포커스 유무에 따른 X11 focus window 를 비교.

## 5. 변경 파일

```text
tools/boxedwine_local/bwujit_threaded_abi/project/emscripten/makefile   ccall + inject fn export
tools/boxedwine_local/assets_d3d9web/boxedwine.upstreamjit64fn6inlineabi2korean1.{js,wasm}  신규 배포
tools/boxedwine_local/assets_d3d9web/boxedwine-shell.js                 갱신(.pre-korean1.bak 백업)
tools/boxedwine_local/fs/...-acp949.zip                                 신규 root
tools/boxedwine_local/index_d3d9web_pathouse.html                       IME 오버레이
scratchpad/gate5_session.ps1                                            -Root / -RuntimeStem 파라미터화
```

원본 실행파일·게임 자산·클라이언트 바이너리는 무수정. 기존 root/stem 은 전부 보존.
