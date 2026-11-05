> **SUPERSEDED by 561.** 물리 입력 첫 조합 update에서 Wine 콜백이 같은 합성 키를 재진입해 WASM worker `Maximum call stack size exceeded`가 발생했습니다. 콜백 구현은 무가드 상태로 배포하면 안 됩니다.

# 560. Wine XIM preedit callback bridge (2026-08-08)

## Scope

#559의 확정문자+Backspace 미리보기를 폐기하고, 게임 바이너리 수정 없이 브라우저
IME의 active composition을 Wine 11이 원래 구현한 XIM preedit callback 경로로 보낸다.

## VERIFIED - #559 regression

- 사용자 물리 입력에서 `안녕`이 `ㅇ안`으로 표시됐다.
- 라이브 FIFO는 `queued=184`, `served=184`, `depth=0`이었다. 첫
  `compositionupdate(ㅇ)`부터 모든 revision을 `XLookupChars` 확정 문자열로 보냈다.
- 원본 Edit는 synthetic Backspace를 동일한 확정 문자열 편집으로 받아들이지 않았다.
  첫 자음이 남은 것은 브라우저 IME 문제가 아니라 #559 설계 자체의 결과다.
- korean7 committed-preedit 경로는 기본값에서 제거하고
  `liveCommittedPreedit=1` 진단 opt-in으로만 보존했다.

## VERIFIED - callback implementation

- host는 `XIMPreeditCallbacks | XIMStatusCallbacks`를 광고한다.
- guest libX11의 `XVaCreateNestedList`가 Wine이 등록한 start/draw/done callback과
  client data를 보존한다.
- browser action은 `1=start+update`, `2=update`, `3=done+commit`, `4=cancel`이다.
- host `XmbLookupString`은 이를 private status `0x7101..0x7104`로 guest libX11에
  전달한다. guest는 update를 `XIMPreeditDrawCallbackStruct`로 호출하고
  `XLookupNone`을 Wine에 반환한다. action 3에서만 `XLookupChars`를 반환한다.
- 따라서 `ㄱ`, `가`, `간` 중간값은 Wine IME composition buffer에만 존재하고
  원본 Edit 확정 문자열에는 `compositionend`의 최종값만 들어간다.

## VERIFIED - artifacts and boot

- runtime: `boxedwine.upstreamjit64fn6inlineabi2korean8preeditcallbacks1`
- runtime JS SHA-256:
  `0AC2068FF1F39C9D048F61D06933520345709A2CB0264D6D0D30E2B690A6141F`
- runtime WASM SHA-256:
  `3216647E067E771A0C503737CE4B0819895EA1FDEB49AFF14170FE0BE072F658`
- libX11 SHA-256:
  `BDDC8AC393E26A8ECD552F090A1D8B2D69DA2DA870F32E79535A8592D30A47F7`
- root: `...acp949-xim30preeditcallbacks1.zip`, SHA-256:
  `57E5EA5D27066E8AEF7340D0C6D222C0610E4B2247BA6D0E809C6755C926DAB6`
- guest libX11 32-bit `-Wall -Werror` compile/link 통과.
- WASM direct instantiate에서 currentabi1 `12968408/262144`, preedit export function을
  확인했다.
- LAN HTTPS에서 JS/WASM/root 모두 200이며 새 runtime/build id로 원본 캐릭터 생성
  화면까지 정상 부팅했다.
- focused 42 tests, full 249 tests, page/runtime JS syntax 검사가 통과했다.

## NOT VERIFIED

- 새 callback bridge에서 사용자 물리 한글 입력 `안녕`의 원본 Edit 표시 결과.
- callback start/draw/done의 라이브 횟수는 기존 38-word debug ABI에 아직 별도 word가
  없어 화면 결과와 물리 입력 후 private status를 함께 수락해야 한다.
